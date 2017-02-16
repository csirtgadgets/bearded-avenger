#!/bin/bash

sudo rpm -iUvh http://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

set -e

yum -y update

echo 'updating apt-get tree and installing python-pip'
sudo yum install -y gcc python-pip python-devel git libffi-devel openssl-devel python-virtualenv \
    python-virtualenvwrapper libselinux-python

echo 'installing ansible...'
sudo pip install 'setuptools>=18.3,<34.0' 'ansible>=2.1,<3.0' versioneer markupsafe

echo 'running ansible...'
ansible-playbook -i "localhost," -c local localhost.yml -vv

bash ../test.sh