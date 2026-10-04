# Frontend image. Target "dev" runs the Vite dev server for `make dev` (code is mounted).
# The production web image (built files behind Caddy) is added with the deploy setup.
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
