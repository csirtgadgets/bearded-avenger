#!/bin/bash

export CIF_BOOTSTRAP_TEST=1
export CIF_ANSIBLE_SDIST=/vagrant
export CIF_HUNTER_THREADS=2
export CIF_HUNTER_ADVANCED=1
#export CIF_GATHERER_GEO_FQDN=1
export CIF_VAGRANT_DISTRO=centos

vagrant box update
time vagrant up
