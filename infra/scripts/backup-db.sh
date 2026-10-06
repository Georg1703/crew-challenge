#!/usr/bin/env bash
# Nightly database backup. Run by the systemd timer cc-backup (03:30 Europe/Chisinau, see
# bootstrap-host.sh); by hand: sudo -u deploy /opt/cc/bin/backup-db.sh
#
#   pg_dump (custom format, compressed) -> /opt/cc/backups/YYYY-MM-DD.dump
#   -> s3://$BACKUP_BUCKET/db/YYYY-MM-DD.dump
#
# The bucket deletes each file 14 days after upload (its lifecycle rule), so the last 14 nights
# are always there. The server's IAM user may only PUT into db/: it cannot list, read or delete
# backups, so a broken server cannot erase them. The last 3 dumps also stay on the server.
# Restore: restore-db.sh. Policy: docs/architecture/environments.md, "Backups".

set -euo pipefail

CC=/opt/cc
# shellcheck source=/dev/null
. "$CC/deploy.conf" # IMAGE_PREFIX

log() { printf '%s  %s\n' "$(date -u +%FT%TZ)" "$*"; }
env_value() { sed -n "s/^$1=//p" "$CC/.env" | tail -n 1; }

bucket="$(env_value BACKUP_BUCKET)"
[ -n "$bucket" ] || { log "BACKUP_BUCKET is missing from $CC/.env" >&2; exit 1; }
release="$(cat "$CC/current_sha")"
day="$(TZ=Europe/Chisinau date +%F)"
dump="$CC/backups/$day.dump"

db() {
  TAG="$release" IMAGE_PREFIX="$IMAGE_PREFIX" \
    docker compose -f "$CC/releases/$release/compose.prod.yaml" --project-directory "$CC" \
    exec -T db "$@"
}

log "dump the database"
mkdir -p "$CC/backups"
# shellcheck disable=SC2016 # expanded inside the container
db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --compress=9' \
  > "$dump.partial"
# A dump pg_restore can read, and not suspiciously small.
db pg_restore --list < "$dump.partial" > /dev/null
[ "$(stat -c %s "$dump.partial")" -gt 2048 ] || { log "dump is too small" >&2; exit 1; }
mv "$dump.partial" "$dump"

log "upload s3://$bucket/db/$day.dump ($(du -h "$dump" | cut -f1))"
AWS_ACCESS_KEY_ID="$(env_value AWS_ACCESS_KEY_ID)" \
  AWS_SECRET_ACCESS_KEY="$(env_value AWS_SECRET_ACCESS_KEY)" \
  AWS_DEFAULT_REGION="$(env_value AWS_REGION)" \
  docker run --rm -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION \
  -v "$CC/backups:/backups:ro" amazon/aws-cli:latest \
  s3 cp "/backups/$day.dump" "s3://$bucket/db/$day.dump" --only-show-errors

find "$CC/backups" -name '*.dump' -mtime +2 -delete
find "$CC/backups" -name '*.partial' -delete
echo "$day ($(du -h "$dump" | cut -f1))" > "$CC/last-backup"
log "backup $day done"
