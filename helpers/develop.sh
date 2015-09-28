#!/bin/bash

set -e

echo "setting up environment"
pip install Cython==0.23.2
pip install git+https://github.com/pyinstaller/pyinstaller.git@f5c305452cfec603d7bf6940437607567144372a
pip install git+https://github.com/zeromq/pyzmq@768836c93a07c29623da16d511301caae34906c3 --install-option="--zmq=bundled"
pip install -r requirements.txt
python setup.py develop
