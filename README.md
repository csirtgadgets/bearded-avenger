# Getting Started
### MAKE SURE YOU'RE USING ONE OF THE [RELEASES](https://github.com/csirtgadgets/bearded-avenger/releases).
Releases are usually a little more stable than the master branch, in that *some* basic deployment testing for Ubuntu and CentOS has been performed using an SQLite backend.

## QuickStart
This assumes you have a proper Python dev already environment properly configured. If you need help getting started with this, checkout one of our [installation guides](https://github.com/csirtgadgets/bearded-avenger/wiki/Ubuntu14LTS).

```
$ git clone https://github.com/csirtgadgets/bearded-avenger.git
$ cd bearded-avenger
$ pip install -r requirements.txt
$ python setup.py develop
$ mkdir -p log && cp hacking/develop.conf hacking/local.conf
$ cif-store -d --token-create-admin cif.yml
$ cif-store -d --token-create-hunter cif-router.yml
$ cif-store -d --token-create-smrt csirtg-smrt.yml
$ supervisord -c hacking/local.conf

# new window
$ cif --config cif.yml -p
$ csirtg-smrt --config csirtg-smrt.yml --test -r rules/default/csirtg.yml -d
$ cif --config cif.yml --itype ipv4
```

## Getting Help
 * [the Wiki](https://github.com/csirtgadgets/bearded-avenger/wiki)
 * [Known Issues](https://github.com/csirtgadgets/bearded-avenger/issues?labels=bug&state=open) 
 * [FAQ](https://github.com/csirtgadgets/bearded-avenger/issues?labels=faq)

# Getting Involved
There are many ways to get involved with the project. If you have a new and exciting feature, or even a simple bugfix, simply [fork the repo](https://help.github.com/articles/fork-a-repo), create some simple test cases, [generate a pull-request](https://help.github.com/articles/using-pull-requests) and give yourself credit!

If you've never worked on a GitHub project, [this is a good piece](https://guides.github.com/activities/contributing-to-open-source) for getting started.

* [How To Contribute](contributing.md)  
* [Mailing List](https://groups.google.com/forum/#!forum/ci-framework)  
* [Project Page](http://csirtgadgets.org/collective-intelligence-framework/)

# COPYRIGHT AND LICENSE

Copyright (C) 2017 [the CSIRT Gadgets Foundation](http://csirtgadgets.org)

Free use of this software is granted under the terms of the [Mozilla Public License (MPLv2)](https://www.mozilla.org/en-US/MPL/2.0/).
