from setuptools import setup, find_packages

with open('requirements.txt') as f:
    reqs = f.read().splitlines()

setup(
      name="cif",
      version='0.0.0a0',
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
      author_email="wes@barely3am.com",
      packages=find_packages(),
      install_requires=reqs,
      scripts=[],
      entry_points = {
          'console_scripts': [
              'cif=cif.client:main',
              'cif-smrt=cif.smrt:main',
              'cif-router=cif.router:main',
              'cif-hunter=cif.hunter:main',
              'cif-gatherer=cif.gatherer:main',
              'cif-api=cif.api:main',
              'cif-storage=cif.storage:main'
              ]
      },
      test_suite="cif.test"
)
