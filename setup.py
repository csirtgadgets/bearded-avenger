import os
from setuptools import setup, find_packages
import versioneer

# vagrant doesn't appreciate hard-linking
if os.environ.get('USER') == 'vagrant' or os.path.isdir('/vagrant'):
    del os.link

with open('requirements.txt') as f:
    reqs = f.read().splitlines()

setup(
    name="bearded-avenger",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="CIF",
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
    install_requires=[],
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
