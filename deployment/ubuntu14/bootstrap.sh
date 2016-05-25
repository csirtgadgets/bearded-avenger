#!/bin/bash

set -e

echo 'updating apt-get tree and installing python-pip'
sudo apt-get update && sudo apt-get install -y python-pip python-dev git libffi-dev libssl-dev sqlite3

echo 'installing ansible...'
sudo pip install 'setuptools>=11.3' 'ansible==2.0.2.0' versioneer markupsafe

echo 'running ansible...'
cd deployment/ubuntu14
ansible-playbook -i "localhost," -c local localhost.yml -vvv

echo 'testing connectivity'
sudo -u cif cif --config /home/cif/.cif.yml -p

echo 'testing query'
sudo -u cif cif --config /home/cif/.cif.yml --search example.com

echo 'testing query'
sudo -u cif cif --config /home/cif/.cif.yml --search example.com

sudo -u cif cif --config /home/cif/.cif.yml --itype ipv4

sudo -u cif cif --config /home/cif/.cif.yml --q 93.184.216.34

sudo -u cif cif --config /home/cif/.cif.yml --q 93.184.216.34