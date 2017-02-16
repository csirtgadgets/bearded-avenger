#!/bin/bash

set -e

echo 'updating apt-get tree and installing python-pip'
sudo apt-get update && sudo apt-get install -y python2.7 python-pip python-dev git libffi-dev libssl-dev sqlite3 \
software-properties-common libxml2-dev libxslt1-dev python-lxml

echo 'installing ansible...'
sudo pip install 'setuptools>=18.5,<34.0' 'ansible>=2.1,<3.0' versioneer markupsafe

echo 'running ansible...'
ansible-playbook -i "localhost," -c local elasticsearch.yml -vv

bash ../test.sh