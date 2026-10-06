# Frontend image. Target "dev" runs the Vite dev server for `make dev` (code is mounted).
# Target "web" is production: the built app served by Caddy, which also terminates HTTPS and
# proxies /api and /admin to Django. Its Caddyfile lives in infra/caddy and comes in as the
# named build context "caddy":
#   docker buildx build --target web --build-context caddy=infra/caddy frontend/
# Works on amd64 and arm64.

ARG NODE_VERSION=22

# ---------------------------------------------------------------- base
FROM node:${NODE_VERSION}-slim AS base
ENV PNPM_HOME=/pnpm \
    PATH="/pnpm:$PATH" \
    COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    CI=true
# pnpm version comes from "packageManager" in package.json.
RUN corepack enable
WORKDIR /app

# ---------------------------------------------------------------- dependencies
FROM base AS deps
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile

# ---------------------------------------------------------------- dev (make dev mounts the code)
FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["pnpm", "dev"]

# ---------------------------------------------------------------- build (production files)
FROM deps AS build
COPY . .
RUN pnpm build

# ---------------------------------------------------------------- web (production)
FROM caddy:2-alpine AS web
COPY --from=caddy Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv/app
RUN caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
EXPOSE 80 443 443/udp
