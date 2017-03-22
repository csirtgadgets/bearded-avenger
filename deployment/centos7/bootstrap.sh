#!/bin/bash

export CIF_ELASTICSEARCH=$CIF_ELASTICSEARCH
export CIF_ANSIBLE_SDIST=$CIF_ANSIBLE_SDIST

set -e

yum -y install epel-release

yum -y update

echo 'updating apt-get tree and installing python-pip'
sudo yum install -y gcc python2-pip python-devel git libffi-devel openssl-devel

bash ../ansible.sh

bash ../test.sh