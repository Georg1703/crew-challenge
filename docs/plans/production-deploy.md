# Plan: production on Lightsail (sohus.fun)

Status: draft for review. Branch: `feat/deploy` from `main` (after everything up to
`feat/team-tab-v2` is merged). Design: `docs/architecture/environments.md`.
Order of priorities: data safety, then a deploy that is boring and repeatable, then speed.

## Decisions (agreed)

| Topic | Decision |
|---|---|
| Host | One Lightsail instance `cc-prod`, Frankfurt, Ubuntu 24.04, 2 GB / 2 vCPU / 60 GB, static IP |
| Domain | `sohus.fun` (GoDaddy, DNS stays at GoDaddy). App on the bare domain, `www` redirects to it |
| Media | Full setup: private bucket, CloudFront on `media.sohus.fun` with signed cookies, MediaConvert -> HLS |
| Buckets | Global namespace: `cc-prod-media-gmirca`, `cc-prod-backups-gmirca` (eu-central-1) |
| Release | Everything up to `feat/team-tab-v2` merged into `main`; `main` is what runs |
| Deploys | GitHub Actions on `main` -> images to GHCR (tag = git sha) -> SSH -> `deploy.sh <sha>` |

## Backups (important: do not drop or weaken)

- Every night at 03:30 Europe/Chisinau, `infra/scripts/backup-db.sh` runs `pg_dump` in the
  Postgres container, gzips it and uploads `db/YYYY-MM-DD.sql.gz` to `cc-prod-backups-gmirca`.
  One file per day; a day's file is never overwritten.
- S3 deletes each file 14 days after upload (lifecycle rule on the whole bucket, already set,
  plus abort incomplete multipart uploads after 7 days). We always have the last 14 nights.
- The server's IAM user may only PUT into `cc-prod-backups-gmirca/db/*`: no list, no get, no
  delete. A broken or compromised server can add backups but cannot erase them.
- `infra/scripts/restore-db.sh <day>` restores one night (downloaded by the owner with their own
  credentials and copied to the server). Restore is tested once before the family starts using
  the app, and after any Postgres major upgrade.
- A failed backup is visible: the script exits non-zero and cron mails nothing, so it writes
  `/opt/cc/backups.log` and `deploy.sh` prints the last backup's date on every deploy.
- Not covered by the database backup: photos and videos (they live in `cc-prod-media-gmirca`).
  Optional later: versioning on the media bucket with old versions expiring after 30 days.

## Code (feat/deploy, one commit each)

1. `build(frontend): add the production web image served by caddy`
   - `frontend/Dockerfile` target `web`: `pnpm build`, then Caddy with the built files.
   - `infra/caddy/Caddyfile`: `sohus.fun` with automatic HTTPS, `www` -> bare domain,
     `/api/*` and `/admin/*` -> `backend:8000`, Django static files, SPA fallback to
     `index.html`, long cache for hashed assets, no cache for `index.html`, `sw.js` and the
     manifest, security headers.
2. `build(infra): add the production compose file`
   - `compose.prod.yaml`: caddy (web image), backend (gunicorn), worker, beat, redis, postgres
     17 with a named volume, health checks, restart policies, logs capped, env from
     `/opt/cc/.env`, CloudFront private key mounted read-only.
   - Images from `ghcr.io/<owner>/crew-challenges-{backend,web}:<sha>`.
3. `build(infra): add host bootstrap, deploy, backup and restore scripts`
   - `bootstrap-host.sh`: Docker, `deploy` user, `/opt/cc`, key-only SSH, fail2ban,
     unattended upgrades, swap file (2 GB RAM), the 03:30 backup cron.
   - `deploy.sh <sha>`: pull, migrate in a one-off container, `up -d`, wait for
     `/api/health`, roll back to the previous sha on failure, record `/opt/cc/current_sha`.
   - `backup-db.sh`, `restore-db.sh` as above. `shellcheck` clean, `set -euo pipefail`.
4. `ci: build images and deploy main to lightsail`
   - After CI passes on `main`: build backend + web for linux/amd64, push to GHCR, SSH as
     `deploy` with a dedicated key, run `deploy.sh <sha>`.
   - GitHub secrets: `DEPLOY_HOST`, `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS`.
5. `docs(infra): add the production runbook and backups policy`
   - `infra/aws/prod/app-user-policy.json` gains the backups statement (PUT only).
   - `docs/architecture/environments.md` and `infra/aws/README.md` updated: domain, bucket
     names as placeholders, backups section, first-launch runbook.

## Owner steps (console, with exact values from me)

| # | Where | What | Status |
|---|---|---|---|
| 1 | GoDaddy | Buy `sohus.fun`; A `@` -> static IP; CNAME `www` -> `sohus.fun` | done |
| 2 | Lightsail | Instance `cc-prod`, static IP, firewall 22/80/443 | check SSH |
| 3 | S3 | `cc-prod-media-gmirca`: private, SSE-S3, CORS for `https://sohus.fun`, abort uploads 7 days | bucket done |
| 4 | S3 | `cc-prod-backups-gmirca`: private, expire after 14 days (whole bucket) | done |
| 5 | Mac | CloudFront key pair (`openssl`), never committed | |
| 6 | CloudFront | Public key, key group `cc-media` | |
| 7 | ACM us-east-1 | Certificate `media.sohus.fun`, DNS validation CNAME at GoDaddy | |
| 8 | CloudFront | Response headers policy `cc-media-cors` (origin `https://sohus.fun`) | |
| 9 | CloudFront | Distribution: origin access control, key group, `media.sohus.fun` | |
| 10 | S3 | Media bucket policy: CloudFront reads `crews/*`; TLS only | |
| 11 | GoDaddy | CNAME `media` -> the distribution's `*.cloudfront.net` | |
| 12 | IAM | Role `cc-mediaconvert-prod` | |
| 13 | IAM | User `cc-prod-app` + access key (media, backups PUT, MediaConvert) | |
| 14 | GitHub | Deploy secrets; GHCR package visibility | |
| 15 | Server | `bootstrap-host.sh`, `/opt/cc/.env` (chmod 600), CloudFront key file | |

## First launch

1. First deploy from GitHub Actions; `https://sohus.fun` answers with a valid certificate.
2. `manage.py check --deploy` clean; create the Django admin user.
3. Create the family crew, send invites, install on an iPhone and an Android phone.
4. Upload a large video with a network cut and resume it; watch it convert and play (HLS).
5. Run `backup-db.sh` by hand once, then restore that file into a scratch database.

## Never

- No demo seeds in production (they refuse without DEBUG).
- No account ids, keys or the IP in the repo; placeholders only.
- Agents do not run AWS commands, SSH into the server or run deploys; the owner does.
