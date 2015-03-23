from unittest import TestCase

from cif.observable import Observable


class TestObservable(TestCase):
    def test_obs_ipv4(self):
        o = Observable('192.168.1.1')
        self.assertTrue(o.is_private())
        self.assertEqual(o.subject, '192.168.1.1')
        self.assertEqual(o.object, 'ipv4')

    def test_obs_fqdn(self):
        o = Observable('example.org')
        self.assertFalse(o.is_private())
        self.assertEqual(o.subject, 'example.org')
        self.assertEqual(o.object, 'fqdn')

    def test_obs_url(self):
        o = Observable('http://example.org')
        self.assertFalse(o.is_private())
        self.assertEqual(o.subject, 'http://example.org')
        self.assertEqual(o.object, 'url')