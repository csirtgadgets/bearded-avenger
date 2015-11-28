# Documentation

See: http://bearded-avenger.readthedocs.org

# Getting Started
## QuickStart
```
$ mkvirtualenv cif
$ python setup.py develop
$ supervisord
```

## Vagrant
### Ubuntu 14 LTS
```
$ make vagrant
$ vagrant ssh
$ workon cif
$ cd /vagrant; supervisord
$ cif-smrt -r rules/default -d --test
```

### CentOS 7.1
```
$ export VAGRANT_VAGRANT_FILE=Vagrantfile.centos7
$ make vagrant-centos7
$ workon cif
$ cd /vagrant; supervisord
$ supervisord
$ cif-smrt -r rules/default -d --test
```

## Clean Install
### Ubuntu 14 LTS
```
$ cd bearded-avenger
$ sudo pip install ansible
$ ansible-playbook -i "localhost," -c local deployment/ansible/ubuntu14.yml
```

### CentOS 7.1
```
$ cd bearded-avenger
$ sudo pip install ansible
$ ansible-playbook -i "localhost," -c local deployment/ansible/centos7.yml
```

# Getting Involved
There are many ways to get involved with the project. If you have a new and exciting feature, or even a simple bugfix, simply [fork the repo](https://help.github.com/articles/fork-a-repo), create some simple test cases, [generate a pull-request](https://help.github.com/articles/using-pull-requests) and give yourself credit!

If you've never worked on a GitHub project, [this is a good piece](https://guides.github.com/activities/contributing-to-open-source) for getting started.

* [How To Contribute](contributing.md)  
* [Mailing List](https://groups.google.com/forum/#!forum/ci-framework)  
* [Project Page](http://csirtgadgets.org/collective-intelligence-framework/)

# COPYRIGHT AND LICENCE

Copyright (C) 2015 [the CSIRT Gadgets Foundation](http://csirtgadgets.org)

Free use of this software is granted under the terms of the GNU Lesser General Public License (LGPLv3). For details see the files `COPYING` included with the distribution.


