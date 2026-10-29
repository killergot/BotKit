#!/usr/bin/env bash
# Executed by SSH CI on the server. Production data volumes are never removed.
set -Eeuo pipefail
umask 077
cd -- "$(dirname -- "$0")/.."
[[ $(id -u) == 0 ]] || { echo 'Run as root' >&2; exit 1; }
state=/var/lib/botkit
mkdir -p "$state" /var/backups/botkit
chmod 700 "$state" /var/backups/botkit
exec 9>"$state/deploy.lock"
flock -w 600 9
revision=$(git rev-parse HEAD)
export BOTKIT_IMAGE_TAG="$revision"
compose=(docker compose --project-name botkit)

# Validate before interrupting the currently running service.
"${compose[@]}" config --quiet
for volume in botkit_postgres_data botkit_redis_data botkit_grafana_data botkit_prometheus_data; do
    docker volume inspect "$volume" >/dev/null
done
[[ -f /etc/botkit/redis-users.acl && -f "$state/last-good.json" ]] || {
    echo 'Provision secrets, database roles and the initial rollback configuration first' >&2
    exit 1
}
chmod 600 .env
"${compose[@]}" build bot
# No production environment, network or data is supplied to these tests.
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
    --mount "type=bind,source=$PWD/tests,target=/app/tests,readonly" \
    "botkit-bot:$revision" python -m unittest discover -s tests -v
cp "$state/last-good.json" "$state/rollback.json"

rollback() {
    result=$?
    trap - ERR
    echo "Deployment failed; restoring the previous container configuration (data volumes remain intact)" >&2
    if docker compose --project-name botkit --project-directory "$PWD" -f "$state/rollback.json" up -d --remove-orphans; then
        printf 'rolled-back %s\n' "$revision" > "$state/deploy-status"
    else
        printf 'rollback-needs-attention %s\n' "$revision" > "$state/deploy-status"
        echo "Rollback needs attention: $state/rollback.json" >&2
    fi
    exit "$result"
}
trap rollback ERR
printf 'deploying %s\n' "$revision" > "$state/deploy-status"
backup=$(python3 scripts/backup.py --leave-stopped)
printf '%s\n' "$backup" > "$state/latest-backup"
bash scripts/install-firewall.sh
"${compose[@]}" up -d --wait --wait-timeout 120 postgres redis prometheus grafana
"${compose[@]}" --profile tools run --rm --no-deps migrate
"${compose[@]}" up -d --no-deps --wait --wait-timeout 180 bot

# Keep a resolved root-only configuration with exact image IDs for the next rollback.
"${compose[@]}" config --format json > "$state/next-good.json"
python3 - "$state/next-good.json" <<'PY'
import json, subprocess, sys
from pathlib import Path
p=Path(sys.argv[1])
d=json.loads(p.read_text())
d['services'].pop('migrate',None)
for s in d['services'].values():
    c=json.loads(subprocess.check_output(['docker','inspect',s['container_name']]))[0]
    s['image']=c['Image']
    s.pop('build',None)
p.write_text(json.dumps(d))
p.chmod(0o600)
PY
mv "$state/next-good.json" "$state/last-good.json"
printf 'healthy %s\n' "$revision" > "$state/deploy-status"
trap - ERR
echo "BotKit deployed: $revision; backup: $backup"
