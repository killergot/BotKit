import asyncio
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from app.core.config import load_config

ENV = {
    'MODE': 'prod', 'BOT_TOKEN': '123456:offline-test-token', 'ID_ADMIN': '1',
    'DB_NAME': 'test', 'DB_USER': 'botkit_app', 'DB_PASS': 'p@ss:/?#%word',
    'DB_HOST_PROD': 'postgres', 'REDIS_HOST_PROD': 'redis',
    'REDIS_USER': 'botkit', 'REDIS_PASSWORD': 'redis-secret',
}


class ConfigTests(unittest.TestCase):
    def test_production_does_not_load_dotenv(self):
        with patch.dict(os.environ, ENV, clear=True), patch('environs.Env.read_env') as read:
            config = load_config()
            read.assert_not_called()
            self.assertEqual(config.database.password, ENV['DB_PASS'])
            self.assertEqual(config.redis.username, 'botkit')

    def test_production_requires_runtime_password(self):
        env = dict(ENV)
        env.pop('DB_PASS')
        env['DB_PASS_PROD'] = 'old-admin-password'
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(Exception):
                load_config()

    def test_database_url_preserves_reserved_characters(self):
        with patch.dict(os.environ, ENV, clear=True):
            from app.database.psql import DATABASE_URL
            self.assertEqual(DATABASE_URL.password, ENV['DB_PASS'])
            self.assertEqual(DATABASE_URL.username, 'botkit_app')
            self.assertNotIn(ENV['DB_PASS'], str(DATABASE_URL))


class ReadinessTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'scripts/check_runtime.py'
        spec = importlib.util.spec_from_file_location('check_runtime', path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    async def test_failure_output_does_not_leak_driver_secrets(self):
        out = io.StringIO()
        with patch.object(self.module, 'check_dependencies', AsyncMock(side_effect=RuntimeError('password=secret'))):
            with contextlib.redirect_stderr(out):
                result = await self.module.main()
        self.assertEqual(result, 1)
        self.assertNotIn('secret', out.getvalue())

    async def test_wait_checks_dependencies_before_startup(self):
        check = AsyncMock(side_effect=[ConnectionError(), None])
        with patch.object(self.module, 'check_dependencies', check), patch.object(asyncio, 'sleep', AsyncMock()):
            self.assertEqual(await self.module.main(wait=True), 0)
        self.assertEqual(check.await_count, 2)


if __name__ == '__main__':
    unittest.main()
