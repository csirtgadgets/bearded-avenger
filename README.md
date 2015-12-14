# Documentation

See: http://bearded-avenger.readthedocs.org

# Getting Started
## QuickStart
```
$ mkvirtualenv cif
$ python setup.py develop
$ supervisord -c hacking/develop.conf
```

## Vagrant
### Ubuntu 14 LTS
```
$ vagrant up
$ vagrant ssh
$ workon cif
$ cd /vagrant; supervisord -c hacking/develop.conf
$ cif-smrt -r rules/default -d --test
```

### CentOS 7.1
```
$ export VAGRANT_VAGRANT_FILE=Vagrantfile.centos
$ vagrant up
$ workon cif
$ cd /vagrant; supervisord -c hacking/develop.conf
$ cif-smrt -r rules/default -d --test
```

## Clean Install [localhost]
### Ubuntu 14 LTS
```
$ sudo apt-get update && sudo apt-get install -y python-pip
$ sudo pip install ansible
$ tar -zxvf bearded-avenger-X.X.X.tar.gz
$ cd bearded-avenger-X.X.X
$ sudo ansible-playbook -i "localhost," -c local deployment/ansible/ubuntu.yml
$ cif -V
```

## Testing
```
$ sudo su - cif
$ cif -V
$ ps aux | grep cif   # make sure cif-router/cif-httpd/cif-storage, etc are running
$ cif-smrt -r /etc/cif/rules/default/drg.yml -f ssh -d --test

# find an address from https://www.dragonresearchgroup.org/insight/sshpwauth.txt
$ cif -q 188.10.149.221
```

# Getting Involved
There are many ways to get involved with the project. If you have a new and exciting feature, or even a simple bugfix, simply [fork the repo](https://help.github.com/articles/fork-a-repo), create some simple test cases, [generate a pull-request](https://help.github.com/articles/using-pull-requests) and give yourself credit!

If you've never worked on a GitHub project, [this is a good piece](https://guides.github.com/activities/contributing-to-open-source) for getting started.

* [How To Contribute](contributing.md)  
* [Mailing List](https://groups.google.com/forum/#!forum/ci-framework)  
* [Project Page](http://csirtgadgets.org/collective-intelligence-framework/)

# Development
Some of the tools we use:

* [PyCharm](https://www.jetbrains.com/pycharm/)
* [VirtualenvWrapper](https://virtualenvwrapper.readthedocs.org/en/latest/)
* [Ansible](http://ansible.com)
* [Vagrant](https://www.vagrantup.com/)
* [Docker](https://docker.io)

Some useful books:

* [Ansible Up & Running](http://www.amazon.com/Ansible-Up-Running-Lorin-Hochstein/dp/1491915323/ref=sr_1_1?ie=UTF8&qid=1450109562&sr=8-1&keywords=ansible+up+and+running)
* [Vagrant Up & Running](http://www.amazon.com/Vagrant-Up-Running-Mitchell-Hashimoto/dp/1449335837/ref=sr_1_3?ie=UTF8&qid=1450109562&sr=8-3&keywords=ansible+up+and+running)
* [Docker Up & Running](http://www.amazon.com/Docker-Up-Running-Karl-Matthias/dp/1491917571/ref=sr_1_2?ie=UTF8&qid=1450109562&sr=8-2&keywords=ansible+up+and+running)


# COPYRIGHT AND LICENCE

Copyright (C) 2015 [the CSIRT Gadgets Foundation](http://csirtgadgets.org)

Free use of this software is granted under the terms of the GNU Lesser General Public License (LGPLv3). For details see the files `COPYING` included with the distribution.
