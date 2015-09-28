#!/bin/bash

## WARNING
## CENTOS support extremely unstable atm

set -e

sudo rpm -iUvh https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
sudo yum -y update
sudo yum groupinstall -y development
sudo yum install -y zlib-dev openssl-devel sqlite-devel bzip2-devel zeromq-devel git python-virtualenvwrapper

bash /vagrant/helpers/python27.sh

sudo pip install virtualenvwrapper
