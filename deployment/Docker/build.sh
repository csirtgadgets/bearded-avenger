#!/bin/bash

set -e

VERSION=`git describe`

docker build -t csirtgadgets/cif:$VERSION .
docker build -t csirtgadgets/cif:3-latest .
