from unittest import TestCase

import cif


class TestClient(TestCase):
    def test_cli(self):
        cli = cif.Client(remote='https://localhost:3000')
        self.assertEqual(cli.remote, 'https://localhost:3000')