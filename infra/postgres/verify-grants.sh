#!/usr/bin/env bash
# Chạy từ repo root: bash infra/postgres/verify-grants.sh
set -euo pipefail

COMPOSE="docker compose -f infra/compose.yaml"

# Đọc SQL từ stdin, chạy bằng superuser trong container postgres
run() {
  $COMPOSE exec -T postgres sh -c \
    'psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
}

cleanup() {
  echo "DROP TABLE IF EXISTS data._grant_probe;" | run >/dev/null 2>&1 || true
}
trap cleanup EXIT

fail() { echo "FAIL: $1" >&2; exit 1; }

cleanup

echo "[1] owner tạo bảng thử trong schema data"
run <<'SQL'
SET ROLE liqi_owner;
CREATE TABLE data._grant_probe (id int);
RESET ROLE;
SQL

echo "[2] worker phải INSERT/UPDATE/DELETE được"
run <<'SQL' || fail "liqi_worker không ghi được vào data"
SET ROLE liqi_worker;
INSERT INTO data._grant_probe VALUES (1);
UPDATE data._grant_probe SET id = 2;
DELETE FROM data._grant_probe;
INSERT INTO data._grant_probe VALUES (1);
RESET ROLE;
SQL

echo "[3] api phải SELECT được"
run <<'SQL' || fail "liqi_api không đọc được data"
SET ROLE liqi_api;
SELECT * FROM data._grant_probe;
RESET ROLE;
SQL

echo "[4] api KHÔNG được INSERT/UPDATE/DELETE/CREATE trong data"
for stmt in \
  "INSERT INTO data._grant_probe VALUES (99);" \
  "UPDATE data._grant_probe SET id = 99;" \
  "DELETE FROM data._grant_probe;" \
  "CREATE TABLE data._api_should_fail (id int);"
do
  if printf 'SET ROLE liqi_api;\n%s\n' "$stmt" | run >/dev/null 2>&1; then
    fail "liqi_api thực hiện được: $stmt"
  fi
  echo "    bị từ chối (đúng): $stmt"
done

echo "[5] worker KHÔNG được DROP bảng (chỉ owner mới có quyền)"
if printf 'SET ROLE liqi_worker;\nDROP TABLE data._grant_probe;\n' | run >/dev/null 2>&1; then
  fail "liqi_worker drop được bảng"
fi

echo "[6] api phải sở hữu schema app"
run <<'SQL' || fail "liqi_api không tạo được bảng trong app"
SET ROLE liqi_api;
CREATE TABLE app._probe (id int);
DROP TABLE app._probe;
RESET ROLE;
SQL

echo "OK: phân quyền đúng"
