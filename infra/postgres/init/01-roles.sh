#!/bin/bash
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE ROLE liqi_owner  LOGIN PASSWORD '${LIQI_OWNER_PASSWORD}';
CREATE ROLE liqi_worker LOGIN PASSWORD '${LIQI_WORKER_PASSWORD}';
CREATE ROLE liqi_api    LOGIN PASSWORD '${LIQI_API_PASSWORD}';

REVOKE ALL ON DATABASE ${POSTGRES_DB} FROM PUBLIC;
GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO liqi_owner, liqi_worker, liqi_api;

-- Schema data: owner = liqi_owner
CREATE SCHEMA data AUTHORIZATION liqi_owner;
GRANT USAGE ON SCHEMA data TO liqi_worker, liqi_api;

-- Quyền cho bảng/sequence TƯƠNG LAI do liqi_owner tạo
ALTER DEFAULT PRIVILEGES FOR ROLE liqi_owner IN SCHEMA data
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO liqi_worker;
ALTER DEFAULT PRIVILEGES FOR ROLE liqi_owner IN SCHEMA data
  GRANT USAGE, SELECT ON SEQUENCES TO liqi_worker;
ALTER DEFAULT PRIVILEGES FOR ROLE liqi_owner IN SCHEMA data
  GRANT SELECT ON TABLES TO liqi_api;

-- Schema app: dành riêng cho NestJS
CREATE SCHEMA app AUTHORIZATION liqi_api;
SQL
