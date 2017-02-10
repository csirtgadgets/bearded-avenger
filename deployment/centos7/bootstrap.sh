#!/bin/bash

sudo rpm -iUvh http://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

set -e

yum -y update

echo 'updating apt-get tree and installing python-pip'
sudo yum install -y gcc python-pip python-devel git libffi-devel openssl-devel python-virtualenv python-virtualenvwrapper

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
sudo pip install 'setuptools>=18.3,<34.0' 'ansible>=2.1,<3.0' versioneer markupsafe

echo 'running ansible...'
ansible-playbook -i "localhost," -c local localhost.yml -vv

echo 'testing connectivity'
sudo -u cif cif --config /home/cif/.cif.yml -p

echo 'testing query'
sudo -u cif cif --config /home/cif/.cif.yml --search example.com

echo 'waiting...'
sleep 5

echo 'testing query'
sudo -u cif cif --config /home/cif/.cif.yml --search example.com

echo 'waiting...'
sleep 5

sudo -u cif cif --config /home/cif/.cif.yml --itype ipv4

sudo -u cif cif --config /home/cif/.cif.yml -q 93.184.216.34

echo 'waiting...'
sleep 5

sudo -u cif cif --config /home/cif/.cif.yml -q 93.184.216.34

sudo systemctl stop csirtg-smrt.service

sudo su - cif
csirtg-smrt -r /etc/cif/rules/default/csirtg.yml -d --remember --client cif --config /etc/cif/csirtg-smrt.yml
cif --config /home/cif/.cif.yml --provider csirtg.io
exit

sudo systemctl start csirtg-smrt.service
