import yaml
import json
import logging


class Rule(dict):

    def __init__(self, logger=logging.getLogger(__name__), path=None, rule=None, **kwargs):
        self.logger = logger
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

            f.close()
        else:
            self.defaults = rule.get('defaults')
            self.feeds = rule.get('feeds')
            self.parser = rule.get('parser')

    def __repr__(self):
        return json.dumps({
            "defaults": self.defaults,
            "feeds": self.feeds,
            "parser": self.parser
        }, sort_keys=True, indent=4, separators=(',', ': '))
