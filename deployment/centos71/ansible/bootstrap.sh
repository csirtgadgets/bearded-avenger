#!/bin/bash

set -e

echo 'updating apt-get tree and installing python-pip'
sudo yum install python-pip python-devel git

echo 'installing ansible...'
sudo pip install ansible==1.9.4 versioneer

echo 'cleaning up dist..'
rm -rf dist/*.tar.gz

echo 'building dist'
python setup.py sdist

echo 'moving sdist into ansible dir..'
cp -f dist/bearded-avenger-*.tar.gz deployment/ubuntu14/ansible/roles/bearded-avenger/files/bearded-avenger3.tar.gz

echo 'running ansible...'
ansible-playbook -i "localhost," -c local deployment/centos71/ansible/localhost.yml

echo 'testing connectivity'
cif -d -p

echo 'testing query'
cif --search example.com -d
