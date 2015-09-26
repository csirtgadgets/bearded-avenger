#!/bin/bash

set -e

echo "setting up environment"
pip install git+https://github.com/pyinstaller/pyinstaller.git@develop
pip install pyzmq --install-option="--zmq=bundled"
pip install -r requirements.txt
python setup.py develop
