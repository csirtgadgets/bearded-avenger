#!/bin/bash

set -e

VERSION=`git describe --tags`

docker build -t csirtgadgets/cif:$VERSION .
docker build -t csirtgadgets/cif:3-latest .
