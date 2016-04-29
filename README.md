# Getting Started
Current master build status: 

[![Circle CI](https://circleci.com/gh/csirtgadgets/bearded-avenger.svg?style=svg&circle-token=e08a0a7ec010e17feb6724dbbc93ce584b9868cd)](https://circleci.com/gh/csirtgadgets/bearded-avenger)
## QuickStart
```
$ pip install -r requirements.txt supervisor==3.2.1
$ python setup.py develop
$ supervisord -c hacking/develop.conf
$ cif-smrt -r rules/default -d --token 1234 --test
$ cif -d -p
$ cif -q bigclarks.com -d
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

# Development
## Some of the tools we use:

* [PyCharm](https://www.jetbrains.com/pycharm/)
* [VirtualenvWrapper](https://virtualenvwrapper.readthedocs.org/en/latest/)
* [Ansible](http://ansible.com)
* [Vagrant](https://www.vagrantup.com/)
* [Docker](https://docker.io)

## Some useful books:

* [Ansible Up & Running](http://www.amazon.com/Ansible-Up-Running-Lorin-Hochstein/dp/1491915323/ref=sr_1_1?ie=UTF8&qid=1450109562&sr=8-1&keywords=ansible+up+and+running)
* [Vagrant Up & Running](http://www.amazon.com/Vagrant-Up-Running-Mitchell-Hashimoto/dp/1449335837/ref=sr_1_3?ie=UTF8&qid=1450109562&sr=8-3&keywords=ansible+up+and+running)
* [Docker Up & Running](http://www.amazon.com/Docker-Up-Running-Karl-Matthias/dp/1491917571/ref=sr_1_2?ie=UTF8&qid=1450109562&sr=8-2&keywords=ansible+up+and+running)


# COPYRIGHT AND LICENCE

Copyright (C) 2016 [the CSIRT Gadgets Foundation](http://csirtgadgets.org)

Free use of this software is granted under the terms of the GNU Lesser General Public License (LGPLv3). For details see the files `COPYING` included with the distribution.
