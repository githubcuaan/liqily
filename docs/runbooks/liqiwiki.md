## Startup order

1. postgres (healthy)
2. migration job: `docker compose -f infra/compose.yaml run --rm data-worker alembic upgrade head`
3. api, data-api, web

## Ports

web 3000 · api 3001 · data-api 8000 · postgres 5432

## Readiness / troubleshooting

- `curl localhost:3001/health` → 503 {"db":"down"}: kiểm tra API_DATABASE_URL, role liqi_api, postgres healthy.
- `curl localhost:8000/health` → 503: kiểm tra WORKER_DATABASE_URL.
- Đổi mật khẩu role sau lần init đầu: script init KHÔNG chạy lại; dùng ALTER ROLE hoặc `down -v` (mất dữ liệu dev).
- Logs: `docker compose -f infra/compose.yaml logs -f <service>`
