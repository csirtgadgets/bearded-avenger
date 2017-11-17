import os
from setuptools import setup, find_packages
import versioneer
import sys

ENABLE_INSTALL = os.getenv('CIF_ENABLE_INSTALL')

# vagrant doesn't appreciate hard-linking
if os.environ.get('USER') == 'vagrant' or os.path.isdir('/vagrant'):
    del os.link

# https://www.pydanny.com/python-dot-py-tricks.html
if sys.argv[-1] == 'test':
    test_requirements = [
        'pytest',
        'coverage',
        'pytest_cov',
    ]
    try:
        modules = map(__import__, test_requirements)
    except ImportError as e:
        err_msg = e.message.replace("No module named ", "")
        msg = "%s is not installed. Install your test requirements." % err_msg
        raise ImportError(msg)
    r = os.system('py.test test -v --cov=cif --cov-fail-under=35')
    if r == 0:
        sys.exit()
    else:
        raise RuntimeError('tests failed')

if sys.argv[-1] == 'install':
    if not ENABLE_INSTALL:
        print('')
        print('CIFv3 Should NOT be installed using traditional install methods')
        print('Please see the DeploymentKit Wiki and use the EasyButton')
        print('the EasyButton uses Ansible to customize the underlying OS and all the moving parts..')
        print('')
        print('https://github.com/csirtgadgets/bearded-avenger-deploymentkit/wiki')
        print('')
        raise SystemError

setup(
    name="cif",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="CIFv3",
    long_description="",
    url="https://github.com/csirtgadgets/bearded-avenger",
    license='LGPL3',
    classifiers=[
               "Topic :: System :: Networking",
               "Environment :: Other Environment",
               "Intended Audience :: Developers",
               "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
               "Programming Language :: Python",
               ],
    keywords=['security'],
    author="Wes Young",
    author_email="wes@csirtgadgets.org",
    packages=find_packages(),
    install_requires=[
        'html5lib',
        'Flask-Limiter',
        'limits',
        'maxminddb',
        'geoip2',
        'pygeoip',
        'dnspython',
        'Flask',
        'PyYAML',
        'SQLAlchemy',
        'elasticsearch',
        'elasticsearch_dsl',
        'ujson',
        'pyzmq>=16.0',
        'csirtg_indicator',
        'cifsdk>=3.0.0a24,<4.0',
        'csirtg_smrt',
        'csirtg_dnsdb'
    ],
    scripts=[],
    entry_points={
        'console_scripts': [
            'cif-router=cif.router:main',
            'cif-hunter=cif.hunter:main',
            'cif-gatherer=cif.gatherer:main',
            'cif-httpd=cif.httpd:main',
            'cif-store=cif.store:main',
        ]
    },
)
