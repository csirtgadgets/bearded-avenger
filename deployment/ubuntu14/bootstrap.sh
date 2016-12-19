#!/bin/bash

set -e

#echo 'yes' | sudo add-apt-repository 'ppa:fkrull/deadsnakes-python2.7'

echo 'updating apt-get tree and installing python-pip'
sudo apt-get update && sudo apt-get install -y python2.7 python-pip python-dev git libffi-dev libssl-dev sqlite3 software-properties-common libxml2-dev libxslt1-dev python-lxml

echo 'installing ansible...'
sudo pip install 'setuptools>=18.5' 'ansible>=2.1,<3.0' versioneer markupsafe

echo 'running ansible...'
ansible-playbook -i "localhost," -c local localhost.yml -vv

echo 'testing connectivity'
sudo -u cif cif --config /home/cif/.cif.yml -p

echo 'testing query'
sudo -u cif cif --config /home/cif/.cif.yml --search example.com

echo 'waiting...'
sleep 5

echo 'testing query'
sudo -u cif cif --config /home/cif/.cif.yml --search example.com

echo 'waiting...'
sleep 5

sudo -u cif cif --config /home/cif/.cif.yml --itype ipv4

sudo -u cif cif --config /home/cif/.cif.yml -q 93.184.216.34

echo 'waiting...'
sleep 5

sudo -u cif cif --config /home/cif/.cif.yml -q 93.184.216.34