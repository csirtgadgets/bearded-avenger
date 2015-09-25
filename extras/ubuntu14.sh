#!/bin/bash

set -e

if [ `whoami` != "root" ]; then
    echo "This script must be run as root"
    exit 1 
fi

echo "adding bleeding edge python2.7 ppa"
add-apt-repository -y ppa:fkrull/deadsnakes-python2.7

echo "installing the basics"
apt-get install -y libzmq3 python-zmq python2.7 python-dev virtualenvwrapper git build-essential

echo "upgrading pip"
sudo pip install pip --upgrade
