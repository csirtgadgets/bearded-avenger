# https://github.com/phusion/baseimage-docker/blob/master/Makefile
NAME = cif
VERSION = latest # make this a version number!

.PHONY: all build docker docker-run test develop

all: build test

test:
	py.test

build:
	python setup.py build

develop:
	(bash ./helpers/develop.sh)

ubuntu14:
	(bash ./helpers/ubuntu14.sh)

docker:
	(cd builds/docker && make build)

docker-run:
	(cd builds/docker && make run)

run:
	supervisord

vagrant:
	vagrant up --provider virtualbox

vagrant-destroy:
	vagrant destroy --force

vagrant-reload: vagrant-destroy vagrant
