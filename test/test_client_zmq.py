import py.test

from cif.client.zeromq import Client


def test_client_zmq():
    cli = Client('https://localhost:3000', '12345')
    assert cli.remote == 'https://localhost:3000'

    assert cli.token == '12345'
