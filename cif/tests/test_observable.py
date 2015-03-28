from unittest import TestCase

from cif.observable import Observable


class TestObservable(TestCase):
    def test_obs_ipv4(self):
        o = Observable('192.168.1.1')
        self.assertTrue(o.is_private())
        self.assertEqual(o.observable, '192.168.1.1')
        self.assertEqual(o.otype, 'ipv4')

    def test_obs_fqdn(self):
        o = Observable('example.org')
        self.assertFalse(o.is_private())
        self.assertEqual(o.observable, 'example.org')
        self.assertEqual(o.otype, 'fqdn')

    def test_obs_url(self):
        o = Observable('http://example.org')
        self.assertFalse(o.is_private())
        self.assertEqual(o.observable, 'http://example.org')
        self.assertEqual(o.otype, 'url')