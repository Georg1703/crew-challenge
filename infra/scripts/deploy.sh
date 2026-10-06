#!/usr/bin/env bash
# Run one release of Crew Challenges: a git sha whose images GitHub Actions pushed to GHCR.
#
#   GitHub Actions:  ssh deploy@<host> <sha>          (forced command: this script)
#   By hand:         sudo -u deploy /opt/cc/bin/deploy.sh <sha>
#
# Steps: fetch the release files at that sha, pull the images, migrate, copy static files,
# start everything and wait for the health checks, then check /api/health through Caddy.
# If the new release does not come up, the previous one is started again. Migrations are not
# undone, so they must stay compatible with the release before (add first, remove later).
# Every run ends with the date of the last database backup.

set -euo pipefail

CC=/opt/cc
# shellcheck source=/dev/null
. "$CC/deploy.conf" # REPO, IMAGE_PREFIX

sha="${1:-${SSH_ORIGINAL_COMMAND:-}}"
if [[ ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
  echo "usage: deploy.sh <full 40-character git sha>" >&2
  exit 2
fi

exec 9>"$CC/.deploy.lock"
flock -n 9 || { echo "Another deploy is running." >&2; exit 1; }

log() { printf '%s  %s\n' "$(date -u +%H:%M:%S)" "$*"; }
env_value() { sed -n "s/^$1=//p" "$CC/.env" | tail -n 1; }

domain="$(env_value APP_DOMAIN)"
[ -n "$domain" ] || { echo "APP_DOMAIN is missing from $CC/.env" >&2; exit 1; }

compose() {
  local release="$1"
  shift
  TAG="$release" IMAGE_PREFIX="$IMAGE_PREFIX" \
    docker compose -f "$CC/releases/$release/compose.prod.yaml" --project-directory "$CC" "$@"
}

fetch() {
  local release="$1" dir="$CC/releases/$1" file
  mkdir -p "$dir"
  for file in compose.prod.yaml infra/scripts/deploy.sh infra/scripts/backup-db.sh \
    infra/scripts/restore-db.sh; do
    curl -fsSL --retry 3 "https://raw.githubusercontent.com/$REPO/$release/$file" \
      -o "$dir/$(basename "$file")"
  done
}

healthy() {
  local _
  for _ in $(seq 1 30); do
    # -k: the app's health, not the certificate's (checked separately below).
    if curl -fsSk --max-time 5 --resolve "$domain:443:127.0.0.1" "https://$domain/api/health" \
      >/dev/null; then
      return 0
    fi
    sleep 4
  done
  return 1
}

release() {
  local release="$1"
  log "pull images for $release"
  compose "$release" --profile release pull --quiet || return 1
  log "migrate"
  compose "$release" run --rm migrate || return 1
  log "static files"
  compose "$release" run --rm static || return 1
  log "start"
  compose "$release" up -d --remove-orphans --wait --wait-timeout 180 || return 1
  log "check https://$domain/api/health"
  healthy || return 1
}

install_scripts() {
  local release="$1" script
  for script in deploy.sh backup-db.sh restore-db.sh; do
    # Replace by rename: a running copy of this script keeps reading the old file.
    install -m 755 "$CC/releases/$release/$script" "$CC/bin/.$script.new"
    mv -f "$CC/bin/.$script.new" "$CC/bin/$script"
  done
}

previous="$(cat "$CC/current_sha" 2>/dev/null || true)"
status=0

log "deploy $sha (running: ${previous:-nothing})"
fetch "$sha"
if release "$sha"; then
  echo "$sha" > "$CC/current_sha"
  install_scripts "$sha"
  # Keep the last 5 releases' files and a week of images.
  find "$CC/releases" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' | sort -rn |
    tail -n +6 | cut -d' ' -f2- | xargs -r rm -rf
  docker image prune -af --filter "until=168h" >/dev/null || true
  if ! curl -fsS --max-time 10 "https://$domain/api/health" >/dev/null; then
    log "WARNING: https://$domain does not answer with a valid certificate yet"
  fi
  log "deployed $sha"
else
  status=1
  log "release $sha did not come up"
  compose "$sha" ps || true
  compose "$sha" logs --tail 50 backend web || true
  if [ -n "$previous" ] && [ "$previous" != "$sha" ]; then
    log "rolling back to $previous"
    if release "$previous"; then
      log "back on $previous"
    else
      log "ROLLBACK FAILED: the site may be down"
    fi
  fi
fi

log "last database backup: $(cat "$CC/last-backup" 2>/dev/null || echo 'none yet')"
exit "$status"
