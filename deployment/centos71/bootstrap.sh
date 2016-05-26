#!/bin/bash

set -e

#echo 'remove this line, not supported yet, use at your own risk'
#exit 0

echo 'updating apt-get tree and installing python-pip'
sudo yum install -y python-pip python-devel git libffi-devel

echo 'installing ansible...'
sudo pip install 'setuptools>=11.3' 'ansible==2.1' versioneer markupsafe

echo 'running ansible...'
ansible-playbook -i "localhost," -c local localhost.yml -vv

echo 'testing connectivity'
sudo -u cif cif --config /home/cif/.cif.yml -p -d

echo 'testing query'
sudo -u cif cif --config /home/cif/.cif.yml --search example.com

echo 'testing query'
sudo -u cif cif --config /home/cif/.cif.yml --search example.com

sudo -u cif cif --config /home/cif/.cif.yml --itype ipv4

sudo -u cif cif --config /home/cif/.cif.yml -q 93.184.216.34

sudo -u cif cif --config /home/cif/.cif.yml -q 93.184.216.34
