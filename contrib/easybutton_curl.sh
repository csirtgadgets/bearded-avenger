#!/bin/bash

set -e

if [ `whoami` != 'root' ]; then
    echo "must be run as root"
    exit 0
fi

ARCH=$(uname -m | sed 's/x86_//;s/i[3-6]86/32/')
BRANCH="master"

if [ -f /etc/lsb-release ]; then
    . /etc/lsb-release
    OS=$DISTRIB_ID
    VER=$DISTRIB_RELEASE
elif [ -f /etc/debian_version ]; then
    OS=Debian  # XXX or Ubuntu??
    VER=$(cat /etc/debian_version)
elif [ -f /etc/redhat-release ]; then
    # TODO add code for Red Hat and CentOS here
    ...
else
    OS=$(uname -s)
    VER=$(uname -r)
fi

case $OS in
    "Ubuntu" )
        sudo apt-get update && sudo apt-get upgrade -y && sudo apt-get install -y htop build-essential automake autoconf git
        git clone https://github.com/csirtgadgets/bearded-avenger.git -b $BRANCH
        cd bearded-avenger
        sudo bash ./contrib/ubuntu/easybutton.sh

    "Debian" )
        echo 'Debian not yet supported...';;

    "Darwin" )
        echo 'Darwin not yet supported...' ;;

    "Redhat" )
        echo 'Redhat not yet supported...' ;;

    "CentOS" )
        echo 'CentOS not yet supported...' ;;

esac
