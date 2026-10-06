#!/usr/bin/env bash
# Prepare a fresh Lightsail Ubuntu 24.04 instance for Crew Challenges. Run once as the default
# user (ubuntu), with sudo; safe to run again (it only adds what is missing).
#
#   curl -fsSL https://raw.githubusercontent.com/Georg1703/crew-challenge/main/infra/scripts/bootstrap-host.sh -o bootstrap-host.sh
#   sudo bash bootstrap-host.sh "ssh-ed25519 AAAA... github-deploy"
#
# The argument is the PUBLIC half of the key GitHub Actions deploys with. That key can only run
# /opt/cc/bin/deploy.sh <sha> (a forced command), nothing else.
#
# What it does:
#   - system updates, unattended security upgrades, fail2ban, a 2 GB swap file
#   - Docker Engine with the compose plugin (Docker's own apt repository)
#   - SSH: keys only, no root login
#   - user "deploy" (in the docker group) owning /opt/cc, with the scripts in /opt/cc/bin
#   - the nightly database backup: systemd timer cc-backup at 03:30 Europe/Chisinau
# Afterwards, write /opt/cc/.env and copy the CloudFront key (it prints how).

set -euo pipefail

REPO="${REPO:-Georg1703/crew-challenge}"
REF="${REF:-main}" # branch or sha to take the scripts from
IMAGE_PREFIX="${IMAGE_PREFIX:-ghcr.io/georg1703/crew-challenge}"
CC=/opt/cc
DEPLOY_KEY="${1:-}"

log() { printf '\n==> %s\n' "$*"; }

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo." >&2; exit 1; }
. /etc/os-release
[ "${ID:-}" = ubuntu ] || { echo "Expected Ubuntu, found ${ID:-unknown}." >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive

log "System updates and base packages"
apt-get update -q
apt-get upgrade -yq
apt-get install -yq ca-certificates curl gnupg fail2ban unattended-upgrades

log "Automatic security updates"
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

log "Docker Engine and compose"
if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -q
  apt-get install -yq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
systemctl enable --now docker

log "Swap file (2 GB of headroom next to 2 GB of RAM)"
if ! swapon --show=NAME --noheadings | grep -q '^/swapfile$'; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null
  swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
echo 'vm.swappiness=10' > /etc/sysctl.d/90-cc-swap.conf
sysctl -q --system

log "SSH: keys only, no root login; fail2ban on"
cat > /etc/ssh/sshd_config.d/10-cc.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
EOF
sshd -t
systemctl reload ssh
cat > /etc/fail2ban/jail.d/sshd.local <<'EOF'
[sshd]
enabled = true
EOF
systemctl enable --now fail2ban
systemctl restart fail2ban

log "User deploy and /opt/cc"
id deploy >/dev/null 2>&1 || useradd --create-home --shell /bin/bash deploy
usermod -aG docker deploy
install -d -o deploy -g deploy -m 750 "$CC" "$CC/bin" "$CC/releases" "$CC/backups"
if [ ! -f "$CC/deploy.conf" ]; then
  cat > "$CC/deploy.conf" <<EOF
# Read by deploy.sh: where release files and images come from.
REPO=$REPO
IMAGE_PREFIX=$IMAGE_PREFIX
EOF
  chown deploy:deploy "$CC/deploy.conf"
fi
for script in deploy.sh backup-db.sh restore-db.sh; do
  curl -fsSL --retry 3 "https://raw.githubusercontent.com/$REPO/$REF/infra/scripts/$script" \
    -o "$CC/bin/$script.new"
  install -o deploy -g deploy -m 755 "$CC/bin/$script.new" "$CC/bin/$script"
  rm -f "$CC/bin/$script.new"
done

if [ -n "$DEPLOY_KEY" ]; then
  log "GitHub Actions key: may only run deploy.sh"
  install -d -o deploy -g deploy -m 700 /home/deploy/.ssh
  echo "restrict,command=\"$CC/bin/deploy.sh\" $DEPLOY_KEY" > /home/deploy/.ssh/authorized_keys
  chown deploy:deploy /home/deploy/.ssh/authorized_keys
  chmod 600 /home/deploy/.ssh/authorized_keys
fi

log "Nightly database backup: 03:30 Europe/Chisinau"
cat > /etc/systemd/system/cc-backup.service <<EOF
[Unit]
Description=Crew Challenges database backup to S3
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
User=deploy
ExecStart=$CC/bin/backup-db.sh
EOF
cat > /etc/systemd/system/cc-backup.timer <<'EOF'
[Unit]
Description=Nightly Crew Challenges database backup

[Timer]
OnCalendar=*-*-* 03:30:00 Europe/Chisinau
# A night missed while the server was off runs at the next boot.
Persistent=true

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now cc-backup.timer

log "Done. Next, as the owner:"
cat <<EOF
  1. Write $CC/.env (template in the runbook), then:
       sudo chown deploy:deploy $CC/.env && sudo chmod 600 $CC/.env
  2. Copy the CloudFront private key to $CC/cloudfront-private.pem, then:
       sudo chown 10001:10001 $CC/cloudfront-private.pem && sudo chmod 400 $CC/cloudfront-private.pem
  3. Push to main (or re-run the deploy workflow); GitHub Actions runs deploy.sh.
  Backups: systemctl list-timers cc-backup.timer; journalctl -u cc-backup
EOF
