# https://github.com/phusion/baseimage-docker/blob/master/Makefile
NAME = cif
VERSION = latest # make this a version number!

.PHONY: all build run

all: build

build:
	@docker build -t $(NAME):$(VERSION) .

build-clean:
	@docker build -t $(NAME):$(VERSION) --no-cache .

run:
	@docker run $(NAME):$(VERSION)
