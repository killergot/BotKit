import ssl
import unittest

from aiogram.client.session.aiohttp import AiohttpSession


class TelegramTlsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = AiohttpSession()

    async def asyncTearDown(self):
        await self.session.close()

    def test_client_verifies_certificate_and_hostname(self):
        context = self.session._connector_init['ssl']
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)

    def test_compromised_emsign_g3_root_is_not_trusted(self):
        # The maintainer restored unaffected emSign roots after the initial removal.
        # Check the affected G3 root, rather than rejecting all emSign certificates.
        certificates = self.session._connector_init['ssl'].get_ca_certs()
        self.assertTrue(certificates)
        names = {value for cert in certificates for rdn in cert['subject']
                 for key, value in rdn if key == 'commonName'}
        self.assertNotIn('emSign ECC Root CA - G3', names)
