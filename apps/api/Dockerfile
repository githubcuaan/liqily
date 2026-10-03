FROM node:22-slim AS build
RUN corepack enable
WORKDIR /repo

# config copy
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY tsconfig.base.json ./
COPY apps/web/package.json apps/web/
COPY apps/api apps/api

# install dep
RUN pnpm install --frozen-lockfile --filter api...
RUN pnpm --filter api build

# package deploy + production dep
RUN pnpm --filter api deploy --prod /app/out

FROM node:22-slim
WORKDIR /app

COPY --from=build /app/out ./

ENV NODE_ENV=production
CMD ["node", "dist/main.js"]
