#!/bin/bash

export VAGRANT_VAGRANTFILE=Vagrantfile
export CIF_BOOTSTRAP_TEST=1
export CIF_ANSIBLE_SDIST=/vagrant
export CIF_HUNTER_THREADS=2
export CIF_HUNTER_ADVANCED=1
export CIF_ANSIBLE_ES=localhost:9200
export CIF_ELASTICSEARCH_TEST=1
#export CIF_GATHERER_GEO_FQDN=1

time vagrant up
