#!/bin/bash

set -e

VERSION=3.0.0a16

docker build -t csirtgadgets/cif:$VERSION .
docker build -t csirtgadgets/cif:latest .
