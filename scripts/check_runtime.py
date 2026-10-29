"""Check dependencies without importing handlers or starting Telegram polling."""
import argparse
import asyncio
import os
import sys
import urllib.request

import asyncpg
from redis.asyncio import Redis


async def check_dependencies():
    conn = await asyncpg.connect(
        host=os.environ['DB_HOST_PROD'], database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'], password=os.environ['DB_PASS'], timeout=5,
    )
    try:
        await conn.fetchval('SELECT 1', timeout=5)
    finally:
        await conn.close(timeout=5)
    redis = Redis(
        host=os.environ['REDIS_HOST_PROD'], port=int(os.getenv('REDIS_PORT', '6379')),
        username=os.getenv('REDIS_USER'), password=os.environ['REDIS_PASSWORD'],
        db=int(os.getenv('REDIS_DB', '0')), socket_connect_timeout=5, socket_timeout=5,
    )
    try:
        await redis.ping()
    finally:
        await redis.aclose()


async def main(wait=False):
    for attempt in range(12 if wait else 1):
        try:
            await check_dependencies()
            if not wait:
                with urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3) as r:
                    if r.status != 200:
                        raise RuntimeError('Metrics endpoint is not ready')
            return 0
        except Exception:
            # Driver errors may contain connection details or user data.
            if not wait or attempt == 11:
                print('BotKit dependency check failed', file=sys.stderr)
                return 1
            await asyncio.sleep(5)
    return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--wait', action='store_true')
    sys.exit(asyncio.run(main(parser.parse_args().wait)))
