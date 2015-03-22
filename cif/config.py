import yaml
import logging


class Config(dict):

    def __init__(self, logger=logging.getLogger(__name__), path=None, **kwargs):
        self.logger = logger
        with open(path) as f:
            try:
                ## TODO - http://pyyaml.org/wiki/PyYAMLDocumentation#LoadingYAML
                d = yaml.load(f)
            except:
                self.logger.error('unable to parse {0}'.format(path))
                raise RuntimeError
        f.close()

        self.token = d.get('token')
        self.remote = d.get('remote')