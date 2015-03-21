from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import logging
import textwrap
import requests
import time
import ujson as json
import select

from pprint import pprint

from cif import LOG_FORMAT, REMOTE


class Client(object):

    def __init__(self, remote=REMOTE, logger=logging.getLogger(__name__),
                 token=None, proxy=None, timeout=300, verify_ssl=True, **kwargs):
        self.logger = logger
        self.remote = remote
        self.token = str(token)
        self.proxy = proxy
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        self.session = requests.session()
        self.session.headers["Accept"] = 'application/vnd.cif.v3+json'
        self.session.headers['User-Agent'] = 'cif-sdk-python/0.0.0a'
        self.session.headers['Authorization'] = 'Token token=' + self.token
        self.session.headers['Content-Type'] = 'application/json'

    def get(self, uri, params={}):
        uri = self.remote + uri
        body = self.session.get(uri, params=params, verify=self.verify_ssl)

        if body.status_code > 303:
            err = 'request failed: %s' % str(body.status_code)
            self.logger.debug(err)
            try:
                err = json.loads(body.content).get('message')
            except ValueError as e:
                err = body.content

            self.logger.error(err)
            raise RuntimeWarning(err)

        self.logger.debug(body.content)
        body = json.loads(body.content)
        return body

    def post(self, uri, data):
        data = json.dumps(data)

        body = self.session.post(uri, data=data, verify=self.verify_ssl)

        if body.status_code > 303:
            err = 'request failed: %s' % str(body.status_code)
            self.logger.debug(err)
            err = body.content

            if body.status_code == 401:
                err = 'unauthroized'
                raise RuntimeError(err)
            elif body.status_code == 404:
                err = 'not found'
                raise RuntimeError(err)
            else:
                try:
                    err = json.loads(err).get('message')
                except ValueError as e:
                    err = body.content

                self.logger.error(err)
                raise RuntimeWarning(err)

        self.logger.debug(body.content)
        body = json.loads(body.content)
        return body

    def search(self):
        pass

    def submit(self):
        pass

    def ping(self, write=False):
        t0 = time.time()

        self.get('/ping')

        t1 = (time.time() - t0)
        self.logger.debug('return time: %.15f' % t1)
        return t1


def main():
    parser = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif -q example.org -d
            $ cif --search 1.2.3.0/24
            $ cif --ping
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif'
    )

    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="set verbosity level [default: %(default)s]")
    parser.add_argument('-d', '--debug', dest='debug', action="store_true")

    parser.add_argument('--token', dest='token', help='specify api token')
    parser.add_argument('-p', '--ping', dest='ping', action="store_true") #meg

    args = parser.parse_args()

    loglevel = logging.WARNING
    if args.verbose:
        loglevel = logging.INFO
    if args.debug:
        loglevel = logging.DEBUG

    console = logging.StreamHandler()
    logging.getLogger('').setLevel(loglevel)
    console.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger('').addHandler(console)
    logger = logging.getLogger(__name__)

    options = vars(args)

    logger.info('running ping')
    for num in range(0,4):
        ret = Client(**options).ping()
        print "roundtrip: %s ms" % ret
        select.select([],[],[],1)

if __name__ == "__main__":
    main()