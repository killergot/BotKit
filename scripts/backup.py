#!/usr/bin/env python3
"""Root-only backups outside the build context; never print secrets or records."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess

TABLES = ('users', 'medicine_kits', 'medicines', 'medicine_items', 'user_medicine_kits', 'reminders')
INVENTORY_SQL = '\n'.join(
    "SELECT '%s', count(*), md5(coalesce(string_agg(md5(row_to_json(t)::text), '' ORDER BY row_to_json(t)::text), '')) FROM public.%s t;" % (t, t)
    for t in TABLES
) + "\nSELECT 'revision',version_num FROM public.alembic_version;\nSELECT sequencename,last_value FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename;\n"


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def inspect(name):
    return json.loads(subprocess.check_output(['docker', 'inspect', name]))[0]


def pg_query(sql, db, container='medicine_postgres'):
    return subprocess.check_output(
        ['docker', 'exec', '-i', container, 'psql', '-X', '-v', 'ON_ERROR_STOP=1',
         '-At', '-U', 'postgres', '-d', db], input=sql.encode(),
    )


def redis_command(info, command):
    env = dict(v.split('=', 1) for v in info['Config'].get('Env', []))
    if 'REDISCLI_AUTH' in env:
        password, username = env['REDISCLI_AUTH'], 'admin'
    else:
        args = info['Config']['Cmd']
        password, username = args[args.index('--requirepass') + 1], 'default'
    return subprocess.check_output(
        ['docker', 'exec', '-i', 'medicine_redis', 'sh', '-c',
         'IFS= read -r REDISCLI_AUTH; export REDISCLI_AUTH; exec redis-cli --user "$1" "$2"',
         'backup', username, command], input=(password + '\n').encode(),
    )


def backup(root, quiesce=True, leave_stopped=False):
    if os.geteuid() != 0:
        raise SystemExit('Run as root')
    os.umask(0o077)
    dest = Path(root) / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    dest.mkdir(parents=True, mode=0o700)
    bot, pg, redis = (inspect(n) for n in ('medicine_bot', 'medicine_postgres', 'medicine_redis'))
    db = dict(v.split('=', 1) for v in pg['Config']['Env'])['POSTGRES_DB']
    was_running = bot['State']['Running']
    if quiesce and was_running:
        run(['docker', 'stop', '--time', '30', 'medicine_bot'], stdout=subprocess.DEVNULL)
    try:
        with (dest / 'database.dump').open('wb') as out:
            run(['docker', 'exec', 'medicine_postgres', 'pg_dump', '-U', 'postgres', '-d', db, '-Fc'], stdout=out)
        with (dest / 'globals.sql').open('wb') as out:
            run(['docker', 'exec', 'medicine_postgres', 'pg_dumpall', '-U', 'postgres', '--globals-only'], stdout=out)
        (dest / 'data-inventory.txt').write_bytes(pg_query(INVENTORY_SQL, db))
        reply = redis_command(redis, 'SAVE').strip()
        if reply != b'OK':
            raise RuntimeError('Redis snapshot failed')
        (dest / 'redis-key-count.txt').write_bytes(redis_command(redis, 'DBSIZE'))
        run(['docker', 'cp', 'medicine_redis:/data/dump.rdb', str(dest / 'redis.rdb')], stdout=subprocess.DEVNULL)
        repo = Path(os.environ.get('BOTKIT_REPO', str(Path(__file__).resolve().parent.parent)))
        for name in ('.env', 'docker-compose.yml', 'Dockerfile'):
            if (repo / name).is_file():
                shutil.copyfile(repo / name, dest / name)
        # This contains credentials and stays in the root-only backup directory.
        (dest / 'containers.json').write_text(json.dumps([
            inspect(n) for n in ('medicine_bot', 'medicine_postgres', 'medicine_redis', 'medicine_grafana', 'medicine_prometheus')
        ]))
        grafana = inspect('medicine_grafana')
        mount = next(m['Source'] for m in grafana['Mounts'] if m['Destination'] == '/var/lib/grafana')
        source = Path(mount) / 'grafana.db'
        if source.exists():
            with sqlite3.connect(f'file:{source}?mode=ro', uri=True) as src:
                with sqlite3.connect(dest / 'grafana.db') as dst:
                    src.backup(dst)
        if Path('/etc/botkit').exists():
            shutil.copytree('/etc/botkit', dest / 'secrets', dirs_exist_ok=True)
        (dest / 'complete').write_text('Logical PG dump, globals, Redis RDB and consistent Grafana SQLite backup.\n')
        for p in dest.rglob('*'):
            p.chmod(0o700 if p.is_dir() else 0o600)
    finally:
        if quiesce and was_running and not leave_stopped:
            run(['docker', 'start', 'medicine_bot'], stdout=subprocess.DEVNULL)
    print(dest)
    return dest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='/var/backups/botkit')
    parser.add_argument('--leave-stopped', action='store_true')
    args = parser.parse_args()
    backup(args.root, leave_stopped=args.leave_stopped)
