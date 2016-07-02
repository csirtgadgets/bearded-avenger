#!/bin/bash

set -e

VERSION=`git describe`

docker build -t cif:$VERSION .
docker push csirtgadgets/cif:$VERSION
docker push csirtgadgets/cif:latest
