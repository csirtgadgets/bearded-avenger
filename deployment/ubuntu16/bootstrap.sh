#!/bin/bash

set -e

export CIF_ELASTICSEARCH=$CIF_ELASTICSEARCH
export CIF_ANSIBLE_SDIST=$CIF_ANSIBLE_SDIST

echo 'installing the basics'
sudo apt-get update && apt-get install -y build-essential python-dev python2.7 python-pip python-dev aptitude \
    python-pip libffi-dev libssl-dev sqlite3 software-properties-common

bash ../ansible.sh

bash ../test.sh