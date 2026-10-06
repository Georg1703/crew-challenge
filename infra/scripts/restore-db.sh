#!/usr/bin/env bash
# Restore a database backup made by backup-db.sh (a pg_dump custom-format .dump file).
#
# Test a backup (the app keeps running; restores into a separate database):
#   sudo -u deploy /opt/cc/bin/restore-db.sh /tmp/2026-10-06.dump --into restore_test
# Replace the live database (stops the app, asks you to type the domain to confirm):
#   sudo -u deploy /opt/cc/bin/restore-db.sh /tmp/2026-10-06.dump
#
# Getting the file: the server cannot read its own backups (PUT-only). On your Mac, with an
# AWS profile that can read the backups bucket:
#   aws s3 cp s3://<BACKUPS_BUCKET>/db/2026-10-06.dump .
#   scp 2026-10-06.dump ubuntu@<APP_DOMAIN>:/tmp/
# Or use a recent copy kept on the server in /opt/cc/backups.

set -euo pipefail

CC=/opt/cc
# shellcheck source=/dev/null
. "$CC/deploy.conf" # IMAGE_PREFIX

usage() {
  echo "usage: restore-db.sh <file.dump> [--into <database>]" >&2
  exit 2
}
log() { printf '%s  %s\n' "$(date -u +%H:%M:%S)" "$*"; }
env_value() { sed -n "s/^$1=//p" "$CC/.env" | tail -n 1; }

file="${1:-}"
[ -f "$file" ] || usage
file="$(realpath "$file")"
cd "$CC" # docker compose reads the current directory; sudo -u deploy keeps the caller's
target=""
if [ "${2:-}" = "--into" ]; then
  target="${3:-}"
  [[ "$target" =~ ^[a-z_][a-z0-9_]*$ ]] || usage
elif [ -n "${2:-}" ]; then
  usage
fi

release="$(cat "$CC/current_sha")"
live="$(env_value POSTGRES_DB)"
user="$(env_value POSTGRES_USER)"
domain="$(env_value APP_DOMAIN)"

compose() {
  TAG="$release" IMAGE_PREFIX="$IMAGE_PREFIX" \
    docker compose -f "$CC/releases/$release/compose.prod.yaml" --project-directory "$CC" "$@"
}
psql_admin() { compose exec -T db psql -v ON_ERROR_STOP=1 -U "$user" -d postgres -c "$1"; }
restore_into() {
  compose exec -T db pg_restore -U "$user" -d "$1" --no-owner --exit-on-error < "$file"
}

compose exec -T db pg_restore --list < "$file" > /dev/null || {
  echo "$file is not a backup pg_restore can read." >&2
  exit 1
}

if [ -n "$target" ]; then
  [ "$target" != "$live" ] || { echo "Use the form without --into for the live database." >&2; exit 2; }
  log "restore into $target (the app keeps running on $live)"
  psql_admin "DROP DATABASE IF EXISTS $target WITH (FORCE)"
  psql_admin "CREATE DATABASE $target"
  restore_into "$target"
  count="$(compose exec -T db psql -U "$user" -d "$target" -tAc 'SELECT count(*) FROM checkins_checkin')"
  log "restored: $count check-ins in $target. Drop it when done:"
  echo "  docker exec crew-challenges-db-1 psql -U $user -d postgres -c 'DROP DATABASE $target'"
  exit 0
fi

echo "This replaces the live database ($live) with $file. Everything after that backup is lost."
read -r -p "Type the domain ($domain) to continue: " answer
[ "$answer" = "$domain" ] || { echo "Cancelled."; exit 1; }

log "stop the app"
compose stop backend worker beat
log "replace $live"
psql_admin "DROP DATABASE $live WITH (FORCE)"
psql_admin "CREATE DATABASE $live"
restore_into "$live"
log "start the app"
compose up -d --wait --wait-timeout 180 backend worker beat
log "restored $file into $live"
