#!/bin/bash

set -e

VERSION=3.0.0a16

docker push csirtgadgets/cif:$VERSION
docker push csirtgadgets/cif:latest
