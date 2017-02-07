#!/bin/bash

sudo rpm -iUvh http://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

set -e

yum -y update

echo 'updating apt-get tree and installing python-pip'
sudo yum install -y gcc python-pip python-devel git libffi-devel openssl-devel

selinuxenabled		# Check if selinux is enabled
if [ $? -eq 0 ]; then	# Yes
	sudo yum install -y libselinux-python
elsif [ $? -eq 1 ]; then	# No
	# NOP
else  # unexpected condition
	echo "Unexpected exit code from selinuxenabled ($?)"
	exit 1
fi

echo 'installing ansible...'
sudo pip install 'setuptools>=18.3' 'ansible>=2.1' versioneer markupsafe

echo 'running ansible...'
ansible-playbook -i "localhost," -c local localhost.yml -vv

echo 'testing connectivity'
sudo -u cif cif --config /home/cif/.cif.yml -p -d

echo 'testing query'
sudo -u cif cif --config /home/cif/.cif.yml --search example.com

echo 'testing query'
sudo -u cif cif --config /home/cif/.cif.yml --search example.com

sudo -u cif cif --config /home/cif/.cif.yml --itype ipv4

sudo -u cif cif --config /home/cif/.cif.yml -q 93.184.216.34

sudo -u cif cif --config /home/cif/.cif.yml -q 93.184.216.34
