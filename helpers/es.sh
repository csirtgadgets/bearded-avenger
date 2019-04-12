#!/bin/bash

set -e

VERSION=5.6.16

docker run -p 9200:9200 -p 9300:9300 elasticsearch:$VERSION
