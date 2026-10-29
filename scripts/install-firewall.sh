#!/bin/sh
set -eu
[ "$(id -u)" = 0 ] || { echo 'Run as root' >&2; exit 1; }
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
/usr/sbin/nft --check -f "$repo/deployment/botkit-guard.nft"
install -d -m 0755 /etc/nftables.d
install -m 0600 "$repo/deployment/botkit-guard.nft" /etc/nftables.d/botkit-guard.nft
cat > /etc/systemd/system/botkit-guard.service <<'UNIT'
[Unit]
Description=BotKit container network isolation
After=nftables.service
Before=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/sbin/nft -f /etc/nftables.d/botkit-guard.nft
ExecReload=/usr/sbin/nft -f /etc/nftables.d/botkit-guard.nft

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable botkit-guard.service
systemctl restart botkit-guard.service
