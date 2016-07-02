#!/bin/bash

set -e

VERSION=`git describe --tags`

docker push csirtgadgets/cif:$VERSION
docker push csirtgadgets/cif:latest
