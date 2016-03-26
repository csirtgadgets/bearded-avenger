import yaml
import json
import logging


class Rule(dict):

    def __init__(self, path=None, rule=None, **kwargs):
        self.logger = logging.getLogger(__name__)
        if path:
            with open(path) as f:
                try:
                    ## TODO - http://pyyaml.org/wiki/PyYAMLDocumentation#LoadingYAML
                    d = yaml.load(f)
                except:
                    self.logger.error('unable to parse {0}'.format(path))
                    raise RuntimeError

            self.defaults = d.get('defaults')
            self.feeds = d.get('feeds')
            self.parser = d.get('parser')
            self.fetcher = d.get('fetcher')
            self.skip = d.get('skip')
            self.remote = d.get('remote')
        else:
            self.defaults = rule.get('defaults')
            self.feeds = rule.get('feeds')
            self.parser = rule.get('parser')
            self.fetcher = rule.get('fetcher')
            self.skip = rule.get('skip')
            self.remote = d.get('remote')

    def __repr__(self):
        return json.dumps({
            "defaults": self.defaults,
            "feeds": self.feeds,
            "parser": self.parser,
            "fetcher": self.fetcher,
            'skip': self.skip,
            'remote': self.remote
        }, sort_keys=True, indent=4, separators=(',', ': '))
