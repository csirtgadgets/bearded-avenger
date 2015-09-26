# https://github.com/phusion/baseimage-docker/blob/master/Makefile
# https://github.com/ansible/ansible/blob/devel/Makefile#L230
NAME = bearded-avenger
VERSION := $(shell cat VERSION | cut -f1 -d' ')
OS = $(shell uname -s)
PYTHON = python

.PHONY: all build docker docker-run test develop

all: build test

test:
	py.test

pep8:
	@echo "#############################################"
	@echo "# Running PEP8 Compliance Tests"
	@echo "#############################################"
	-pep8 -r --ignore=E501,E221,W291,W391,E302,E251,E203,W293,E231,E303,E201,E225,E261,E241 cif/

python:
	$(PYTHON) setup.py build

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

install:
	$(PYTHON) setup.py install

clean:
	@echo "Cleaning up distutils stuff"
	rm -rf build
	rm -rf dist
	@echo "Cleaning up byte compiled python stuff"
	find . -type f -regex ".*\.py[co]$$" -delete
	@echo "Cleaning up output from test runs"
	rm -rf tests/__pycache__
	@echo "Cleaning up RPM building stuff"
	rm -rf MANIFEST rpm-build
	@echo "Cleaning up Debian building stuff"
	find . -type f -name '*.pyc' -delete

sdist: clean
	$(PYTHON) setup.py sdist

# DEB build parameters
DEBUILD_BIN ?= debuild
DEBUILD_OPTS = --source-option="-I"
DPUT_BIN ?= dput
DPUT_OPTS ?=
DEB_DATE := $(shell date +"%a, %d %b %Y %T %z")
ifeq ($(OFFICIAL),yes)
    DEB_RELEASE = $(RELEASE)ppa
    # Sign OFFICIAL builds using 'DEBSIGN_KEYID'
    # DEBSIGN_KEYID is required when signing
    ifneq ($(DEBSIGN_KEYID),)
        DEBUILD_OPTS += -k$(DEBSIGN_KEYID)
    endif
else
    DEB_RELEASE = 0.git$(DATE)$(GITINFO)
    # Do not sign unofficial builds
    DEBUILD_OPTS += -uc -us
    DPUT_OPTS += -u
endif
DEBUILD = $(DEBUILD_BIN) $(DEBUILD_OPTS)
DEB_PPA ?= ppa:wes-8/ppa
# Choose the desired Ubuntu release: lucid precise saucy trusty
DEB_DIST ?= unstable

debian:
	@for DIST in $(DEB_DIST) ; do \
	    mkdir -p deb-build/$${DIST}/$(NAME)-$(VERSION)/dist ; \
	    cp -a packaging/pyinstaller/dist/* deb-build/$${DIST}/$(NAME)-$(VERSION)/dist ; \
	    cp -a packaging/debian deb-build/$${DIST}/$(NAME)-$(VERSION)/ ; \
		sed -ie "s|%VERSION%|$(VERSION)|g;s|%RELEASE%|$(DEB_RELEASE)|;s|%DIST%|$${DIST}|g;s|%DATE%|$(DEB_DATE)|g" deb-build/$${DIST}/$(NAME)-$(VERSION)/debian/changelog ; \
	done

deb: debian
	@for DIST in $(DEB_DIST) ; do \
	    (cd deb-build/$${DIST}/$(NAME)-$(VERSION)/ && $(DEBUILD) -b) ; \
	done
	@echo "#############################################"
	@for DIST in $(DEB_DIST) ; do \
	    echo deb-build/$${DIST}/$(NAME)_$(VERSION)-$(DEB_RELEASE)~$${DIST}_amd64.changes ; \
	done
	@echo "#############################################"

deb-upload: deb
	@for DIST in $(DEB_DIST) ; do \
	    $(DPUT_BIN) $(DPUT_OPTS) $(DEB_PPA) deb-build/$${DIST}/$(NAME)_$(VERSION)-$(DEB_RELEASE)~$${DIST}_amd64.changes ; \
	done

PYINSTALLER = pyinstaller
PYINSTALLER_DIST_PATH = pyinstaller_dist
PYINSTALLER_WORK_PATH = pyinstaller_temp
PYINSTALLER_OPTS = --distpath=$(PYINSTALLER_DIST_PATH) --workpath=$(PYINSTALLER_WORK_PATH) -y --onefile
PYINSTALLER_SPEC_DIR = packaging/pyinstaller
PYINSTALLER_SPECS = cif.spec cif-router.spec cif-smrt.spec cif-httpd.spec

pyinstaller:
	@for SPEC in $(PYINSTALLER_SPECS) ; do \
		$(PYINSTALLER) $(PYINSTALLER_OPTS) $(PYINSTALLER_SPEC_DIR)/$${SPEC} ; \
	done

pyinstaller-clean:
	rm -rf $(PYINSTALLER_WORK_PATH)
	rm -rf $(PYINSTALLER_DIST_PATH)