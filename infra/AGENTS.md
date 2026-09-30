# infra/AGENTS.md

Production runs on one Amazon Lightsail instance with Docker Compose. AWS resources are created
**by hand by the owner**. Read the root `AGENTS.md` and `docs/architecture/environments.md` first.

## What agents may do here
- Write and review the JSON documents in `infra/aws/` (bucket CORS, lifecycle rules, IAM policies).
- Write and update the step-by-step console runbook `docs/runbooks/aws-setup.md`.
- Write Caddy configuration, compose files, and shell scripts (`deploy.sh`, `backup-db.sh`,
  `bootstrap-host.sh`).
- Lint scripts with `shellcheck` and validate JSON.

## What agents must never do
- Run AWS CLI commands that create, change, or delete anything.
- SSH into the server, run deploy scripts, or read production secrets.
- Put account ids, access keys, or passwords in any file. Use placeholders like
  `<ACCOUNT_ID>` and `<APP_DOMAIN>`, and document where the owner fills them in.

## Layout
```
infra/
|-- aws/      # JSON pasted into the AWS console; one file per policy or bucket setting
|-- caddy/    # Caddyfile: HTTPS, SPA fallback, /api + /admin proxy, cache headers
`-- scripts/  # bootstrap-host.sh, deploy.sh, backup-db.sh, restore-db.sh
```

## Principles
- Least privilege: the server's IAM user can only reach `cc-prod-media`, `cc-prod-backups`, and
  start MediaConvert jobs with `iam:PassRole` on the MediaConvert role. Nothing else.
- Scripts are idempotent, use `set -euo pipefail`, and print what they do.
- Every manual step has a runbook entry, and every created resource is recorded in
  `docs/runbooks/aws-inventory.md` (names and ARNs only, no secrets).
