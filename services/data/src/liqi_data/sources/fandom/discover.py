"""CLI discover: send probe to Fandom API"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://arenaofvalor.fandom.com/api.php"
DEFAULT_OUT_DIR = "artifacts/discovery"
PLACEHOLDER_UA = "LiqiDataBot/0.1 (+https://example.invalid/liqi; contact: unset)"
RETRY_STATUSES = {429, 500, 502, 503, 504}
# Chỉ giữ các header hữu ích cho việc chẩn đoán, tránh lưu cookie/token.
KEEP_HEADERS = {
    "content-type",
    "content-length",
    "content-encoding",
    "date",
    "server",
    "retry-after",
    "cache-control",
    "mediawiki-api-error",
    "x-served-by",
    "x-cache",
    "x-backend-response-time",
}


# --------------------------------------------------------------------------- #
#  Probe defination
# --------------------------------------------------------------------------- #
@dataclass
class Probe:
    name: str
    params: dict[str, Any] = field(default_factory=dict)
    url: str | None = None  # ghi đè base URL (ví dụ robots.txt)
    api: bool = True  # True -> tự thêm format=json
    note: str = ""


def default_probes() -> list[Probe]:
    """Default prbes"""
    return [
        Probe(
            "robots_txt",
            url="https://arenaofvalor.fandom.com/robots.txt",
            api=False,
            note="Kiểm tra quy tắc crawl của site.",
        ),
        Probe(
            "siteinfo",
            {
                "action": "query",
                "meta": "siteinfo",
                "siprop": "general|namespaces|namespacealiases",
            },
            note="Thông tin wiki, danh sách namespace.",
        ),
        Probe(
            "allcategories_first_page",
            {
                "action": "query",
                "list": "allcategories",
                "aclimit": 500,
                "acprop": "size",
            },
            note="Chỉ trang đầu; việc đi hết continuation thuộc bước 2.2.",
        ),
        Probe(
            "revisions_airi",
            {
                "action": "query",
                "prop": "revisions",
                "titles": "Airi",
                "rvprop": "ids|timestamp|content",
                "rvslots": "main",
            },
            note="Ứng viên trang tướng, cần xác minh ở bước 2.5.",
        ),
        Probe(
            "revisions_airi_formatversion2",
            {
                "action": "query",
                "prop": "revisions",
                "titles": "Airi",
                "rvprop": "ids|timestamp|content",
                "rvslots": "main",
                "formatversion": 2,
            },
            note="So sánh hình dạng phản hồi formatversion=2 với bản mặc định.",
        ),
        Probe(
            "revisions_sonic_boots",
            {
                "action": "query",
                "prop": "revisions",
                "titles": "Sonic_Boots",
                "rvprop": "ids|timestamp|content",
                "rvslots": "main",
            },
            note="Ứng viên trang trang bị, cần xác minh ở bước 2.5.",
        ),
        Probe(
            "parse_sections_airi",
            {"action": "parse", "page": "Airi", "prop": "sections"},
        ),
        Probe(
            "images_airi",
            {"action": "query", "prop": "images", "titles": "Airi", "imlimit": 50},
            note="Lấy tên file ảnh; imageinfo sẽ gọi sau khi biết tên file thật.",
        ),
        Probe(
            "missing_page",
            {
                "action": "query",
                "prop": "revisions",
                "titles": "Liqi_Probe_Page_That_Should_Not_Exist",
                "rvprop": "ids",
                "rvslots": "main",
            },
            note="Quan sát hình dạng phản hồi khi trang không tồn tại.",
        ),
    ]


# --------------------------------------------------------------------------- #
# Rate limit + fetch có retry
# --------------------------------------------------------------------------- #
class Fetcher:
    def __init__(
        self,
        user_agent: str,
        rate: float,
        timeout: float,
        max_retries: int,
        backoff: float,
    ):
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError("--rate phải > 0 (số request mỗi giây)")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("--timeout must be finite and > 0")
        if max_retries < 0:
            raise ValueError("--max-retries must be >= 0")
        if not math.isfinite(backoff) or backoff < 0:
            raise ValueError("--backoff must be finite and >= 0")
        self.min_interval = 1.0 / rate
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self._last = 0.0
        self.session = httpx.Client(follow_redirects=True)
        self.session.headers.update(
            {"User-Agent": user_agent, "Accept-Encoding": "gzip"}
        )

    def _throttle(self) -> None:
        wait = self._last + self.min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()

    def fetch(self, probe: Probe, base_url: str) -> dict[str, Any]:
        url = probe.url or base_url
        params = dict(probe.params)
        if probe.api:
            params["format"] = "json"

        record: dict[str, Any] = {
            "probe": probe.name,
            "note": probe.note,
            "source_url": url,
            "params": params,
            "request_url": None,
            "final_url": None,
            "redirects": [],
            "http_status": None,
            "fetched_at": None,
            "elapsed_ms": None,
            "attempts": 0,
            "response_headers": {},
            "body": None,
            "error": None,
        }

        for attempt in range(1, self.max_retries + 2):
            record.update(
                request_url=None,
                final_url=None,
                redirects=[],
                http_status=None,
                response_headers={},
                body=None,
                error=None,
            )
            record["attempts"] = attempt
            self._throttle()
            started = time.monotonic()
            record["fetched_at"] = datetime.now(UTC).isoformat(timespec="seconds")
            try:
                resp = self.session.get(
                    url, params=params or None, timeout=self.timeout
                )
            except httpx.RequestError as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
                record["http_status"] = None
                record["elapsed_ms"] = round((time.monotonic() - started) * 1000)
                if attempt <= self.max_retries:
                    time.sleep(self.backoff * 2 ** (attempt - 1))
                    continue
                return record

            record["error"] = None
            record["elapsed_ms"] = round((time.monotonic() - started) * 1000)
            record["http_status"] = resp.status_code
            record["request_url"] = str(
                resp.history[0].request.url if resp.history else resp.request.url
            )
            record["final_url"] = str(resp.url)
            record["redirects"] = [
                {"status": r.status_code, "url": str(r.url)} for r in resp.history
            ]
            record["response_headers"] = {
                k.lower(): v
                for k, v in resp.headers.items()
                if k.lower() in KEEP_HEADERS
            }
            record["body"] = resp.text  # nguyên bản, không parse lại

            if resp.status_code in RETRY_STATUSES and attempt <= self.max_retries:
                delay = retry_delay(
                    resp.headers.get("Retry-After", ""),
                    self.backoff * 2 ** (attempt - 1),
                )
                time.sleep(delay)
                continue
            return record
        return record  # không tới được, giữ cho type checker


# --------------------------------------------------------------------------- #
# Lưu kết quả
# --------------------------------------------------------------------------- #
def retry_delay(value: str, fallback: float) -> float:
    value = value.strip()
    if value.isascii() and value.isdigit():
        return float(value)
    try:
        deadline = parsedate_to_datetime(value)
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)
        return max(0.0, (deadline - datetime.now(UTC)).total_seconds())
    except (ValueError, TypeError, OverflowError):
        return fallback


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "probe"


def write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(tmp, path)


def classify(record: dict[str, Any]) -> str:
    """Nhãn ngắn để nhìn nhanh trong manifest."""
    if record["error"]:
        return "network_error"
    status = record["http_status"]
    if status is None:
        return "no_response"
    if status >= 400:
        return "http_error"
    body = record["body"] or ""
    if record["probe"] != "robots_txt":
        try:
            parsed = json.loads(body)
        except ValueError:
            return "ok_but_not_json"  # có thể là trang chặn bot/HTML
        if isinstance(parsed, dict) and "error" in parsed:
            return "api_error"
    return "ok"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="discover", description=(__doc__ or "").split("\n")[0]
    )
    p.add_argument(
        "--base-url", default=os.environ.get("FANDOM_API_URL", DEFAULT_BASE_URL)
    )
    p.add_argument("--out", default=DEFAULT_OUT_DIR, help="thư mục lưu probe")
    p.add_argument(
        "--user-agent", default=os.environ.get("FANDOM_USER_AGENT", PLACEHOLDER_UA)
    )
    p.add_argument("--rate", type=float, default=1.0, help="request/giây (mặc định 1)")
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--max-retries", type=int, default=3)
    p.add_argument(
        "--backoff", type=float, default=2.0, help="giây, nhân đôi mỗi lần retry"
    )
    p.add_argument(
        "--only", action="append", default=[], help="chỉ chạy probe có tên này"
    )
    p.add_argument("--list", action="store_true", help="liệt kê probe rồi thoát")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    probes = default_probes()

    if args.list:
        for pr in probes:
            print(f"{pr.name:35s} {pr.note}")
        return 0

    if args.only:
        unknown = set(args.only) - {p.name for p in probes}
        if unknown:
            print(f"Probe không tồn tại: {sorted(unknown)}", file=sys.stderr)
            return 2
        probes = [p for p in probes if p.name in args.only]

    if args.user_agent == PLACEHOLDER_UA:
        print(
            "CẢNH BÁO: đang dùng User-Agent mẫu. Hãy đặt --user-agent hoặc FANDOM_USER_AGENT "
            "với thông tin liên hệ thật.",
            file=sys.stderr,
        )

    try:
        fetcher = Fetcher(
            args.user_agent, args.rate, args.timeout, args.max_retries, args.backoff
        )
    except ValueError as exc:
        parser.error(str(exc))
    out_dir = Path(args.out)
    manifest: list[dict[str, Any]] = []

    with fetcher.session:
        for probe in probes:
            record = fetcher.fetch(probe, args.base_url)
            record["result"] = classify(record)
            write_json_atomic(out_dir / f"{safe_name(probe.name)}.json", record)
            manifest.append(
                {
                    "probe": probe.name,
                    "http_status": record["http_status"],
                    "result": record["result"],
                    "fetched_at": record["fetched_at"],
                    "attempts": record["attempts"],
                    "body_bytes": len((record["body"] or "").encode("utf-8")),
                    "error": record["error"],
                }
            )
            print(
                f"[{record['result']:>13}] {probe.name} "
                f"(HTTP {record['http_status']}, {record['attempts']} lần thử)"
            )

    write_json_atomic(
        out_dir / "_manifest.json",
        {
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "base_url": args.base_url,
            "user_agent": args.user_agent,
            "rate_per_second": args.rate,
            "probes": manifest,
        },
    )

    blocked = [m for m in manifest if m["result"] != "ok"]
    if blocked:
        print(
            f"\n{len(blocked)}/{len(manifest)} probe không thành công. "
            f"Xem {out_dir}/_manifest.json và ghi blocker vào runbook (bước 2.8).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
