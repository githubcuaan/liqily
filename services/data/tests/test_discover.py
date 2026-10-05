import json
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest
from typer.testing import CliRunner

from liqi_data.cli import app
from liqi_data.sources.fandom import discover


def test_cli_capture(monkeypatch, tmp_path):
    def respond(request):
        assert request.url.params["format"] == "json"
        assert request.headers["User-Agent"] == "DiscoveryTest/1.0"
        return httpx.Response(200, json={"query": {"general": {}}})

    client = httpx.Client(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(discover.httpx, "Client", lambda **kwargs: client)
    monkeypatch.setenv("FANDOM_USER_AGENT", "DiscoveryTest/1.0")
    result = CliRunner().invoke(
        app, ["discover", "--only", "siteinfo", "--out", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    record = json.loads((tmp_path / "siteinfo.json").read_text())
    assert record["http_status"] == 200
    assert record["source_url"] == discover.DEFAULT_BASE_URL
    assert record["params"]["format"] == "json"
    assert record["fetched_at"]
    assert json.loads(record["body"]) == {"query": {"general": {}}}
    assert (tmp_path / "_manifest.json").exists()
    assert client.is_closed


def test_timeout_after_retry_clears_previous_response(monkeypatch):
    calls = 0

    def respond(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                503, text="unavailable", headers={"Retry-After": "120"}
            )
        raise httpx.ReadTimeout("timed out", request=request)

    sleeps = []
    monkeypatch.setattr(discover.time, "sleep", sleeps.append)
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(discover.httpx, "Client", lambda **kwargs: client)
        fetcher = discover.Fetcher("test", 1, 30, 1, 2)
        record = fetcher.fetch(discover.Probe("test"), discover.DEFAULT_BASE_URL)
    assert 120 in sleeps
    assert record["attempts"] == 2
    assert record["http_status"] is None
    assert record["body"] is None
    assert record["response_headers"] == {}
    assert record["final_url"] is None
    assert discover.classify(record) == "network_error"


def test_retry_after_date():
    deadline = datetime.now(UTC) + timedelta(seconds=120)
    assert 118 <= discover.retry_delay(format_datetime(deadline), 2) <= 120
    assert discover.retry_delay("invalid", 2) == 2
    assert discover.retry_delay("Wed, 01 Jan 2020 00:00:00 GMT", 2) == 0


@pytest.mark.parametrize(
    "option,value",
    [
        ("--rate", "0"),
        ("--rate", "nan"),
        ("--timeout", "0"),
        ("--timeout", "inf"),
        ("--max-retries", "-1"),
        ("--backoff", "-1"),
    ],
)
def test_invalid_options(option, value):
    result = CliRunner().invoke(app, ["discover", option, value])
    assert result.exit_code == 2
    assert option in result.output


def test_cli_help_and_list():
    runner = CliRunner()
    assert "--max-retries" in runner.invoke(app, ["discover", "--help"]).output
    result = runner.invoke(app, ["discover", "--list"])
    assert result.exit_code == 0
    assert "siteinfo" in result.output
