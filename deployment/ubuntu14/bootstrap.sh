#!/bin/bash

set -e

echo 'updating apt-get tree and installing python-pip'
sudo apt-get update && sudo apt-get install -y python-pip python-dev git libffi-dev libssl-dev

echo 'installing ansible...'
sudo pip install 'setuptools>=11.3' 'ansible==1.9.6' versioneer markupsafe

echo 'cleaning up dist..'
rm -rf dist/*.tar.gz

echo 'building dist'
python setup.py sdist

echo 'moving sdist into ansible dir..'
cp -f dist/bearded-avenger-*.tar.gz deployment/ubuntu14/roles/bearded-avenger/files/bearded-avenger3.tar.gz

echo 'running ansible...'
ansible-playbook -i "localhost," -c local deployment/ubuntu14/localhost.yml

echo 'testing connectivity'
cif -d -p

echo 'testing query'
cif --search example.com -d
