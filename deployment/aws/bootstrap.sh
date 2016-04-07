#!/bin/bash

set -e

echo 'cleaning up dist..'
rm -rf dist/*.tar.gz

echo 'building dist'
python setup.py sdist

echo 'moving sdist into ansible dir..'
cp -f dist/bearded-avenger-*.tar.gz deployment/aws/roles/bearded-avenger/files/bearded-avenger3.tar.gz

cd deployment/aws/

if [ ! -f site.yml ]; then
    echo "copy site.yml.example to site.yml, fill in the variables with your VPC information and try again"
fi

echo 'running ansible...'
ansible-playbook site.yml
