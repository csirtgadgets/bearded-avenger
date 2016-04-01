#!/bin/bash

set -e

echo 'updating apt-get tree and installing python-pip'
sudo apt-get update && sudo apt-get install -y python-pip python-dev

echo 'installing ansible...'
sudo pip install ansible==1.9.4

echo 'running ansible...'
ansible-playbook -i "localhost," -c local deployment/ubuntu14/ansible/localhost.yml

echo 'testing connectivity'
cif -d -p

echo 'testing query'
cif --search example.com -d
