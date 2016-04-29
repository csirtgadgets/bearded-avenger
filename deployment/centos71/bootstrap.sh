#!/bin/bash

set -e

echo 'remove this line, not supported yet, use at your own risk'
exit 0

echo 'updating apt-get tree and installing python-pip'
sudo yum install python-pip python-devel git

echo 'installing ansible...'
sudo pip install 'ansible==2.0.2.0' versioneer markupsafe

echo 'cleaning up dist..'
rm -rf dist/*.tar.gz

echo 'building dist'
python setup.py sdist

echo 'moving sdist into ansible dir..'
cp -f dist/bearded-avenger-*.tar.gz deployment/centos71/roles/bearded-avenger/files/bearded-avenger3.tar.gz

echo 'running ansible...'
ansible-playbook -i "localhost," -c local deployment/centos71/ansible/localhost.yml

echo 'testing connectivity'
cif -d -p

echo 'testing query'
cif --search -n example.com -d
