import py.test

from cif.client import Client


def test_cli():
    cli = Client('https://localhost:3000', 12345)
    assert cli.remote == 'https://localhost:3000'
