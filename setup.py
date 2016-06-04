import os
from setuptools import setup, find_packages
import versioneer

# vagrant doesn't appreciate hard-linking
if os.environ.get('USER') == 'vagrant' or os.path.isdir('/vagrant'):
    del os.link

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
        'mock>=2.0.0',
        'Flask-Limiter>=0.9.3',
        'limits==1.1.1',
        'feedparser>=5.2.1',
        'nltk==3.2',
        'maxminddb>=1.2.0',
        'geoip2==2.2.0',
        'dnspython>=1.12.0',
        'Flask==0.10.1',
        'Jinja2==2.7.3',
        'MarkupSafe==0.23',
        'PyYAML>=3.11',
        'SQLAlchemy==0.9.9',
        'Werkzeug==0.10.1',
        'meld3>=1.0.2',
        'passlib>=1.6.2',
        'pyparsing>=2.0.3',
        'python-magic>=0.4.6',
        'pytricia>=0.9.0',
        'pyzmq==14.7.0',
        'requests>=2.6.0',
        'ujson>=1.35',
        'urllib3>=1.10.2',
        'supervisor==3.1.3',
        'elasticsearch>=2.3.0',
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
