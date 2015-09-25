#!/bin/bash

set -e

echo "adding bleeding edge python2.7 ppa"
sudo add-apt-repository -y ppa:fkrull/deadsnakes-python2.7

echo "adding zmq ppa"
sudo add-apt-repository -y ppa:chris-lea/zeromq

echo "updating repos..."
sudo apt-get update

echo "installing the basics"
sudo apt-get install -y libzmq3 libzmq3-dev python-zmq python2.7 python-dev virtualenvwrapper git build-essential dh-make bzr-builddeb

echo "upgrading pip"
sudo pip install pip --upgrade --force-reinstall
