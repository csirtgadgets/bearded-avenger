#!/bin/bash

set -e

VERSION=`git describe`

docker push csirtgadgets/cif:$VERSION
docker push csirtgadgets/cif:latest
