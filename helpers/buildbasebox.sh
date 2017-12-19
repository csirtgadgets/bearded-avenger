#!/bin/bash

export VAGRANT_VAGRANTFILE=Vagrantfile_buildbox

if [ -e cifv3.box ]; then
  rm cifv3.box
fi

time vagrant up
vagrant package --output cifv3.box
vagrant box add cifv3 cifv3.box