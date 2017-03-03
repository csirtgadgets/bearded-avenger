#!/bin/bash

set -e

if [ `whoami` != 'root' ]; then
    echo "must be run as root"
    exit 1
fi

# Check for an Internet Connection as it is required during installation
HTTP_HOST=http://github.com
if [ -x /usr/bin/wget ]; then
    echo "Checking for an Internet connection"
    wget -q --tries=3 --timeout=10 --spider $HTTP_HOST
    if [[ $? -eq 0 ]]; then
        echo "$HTTP_HOST appears to be available via HTTP"
    else
        echo "$HTTP_HOST does not appear to be available via HTTP"
        echo "Exiting installation"
        exit 1
    fi
else
    echo "/usr/bin/wget does not exist, skipping Internet connection test"
fi

ARCH=$(uname -m | sed 's/x86_//;s/i[3-6]86/32/')

if [ -f /etc/lsb-release ]; then
    . /etc/lsb-release
    OS=$DISTRIB_ID
    VER=$DISTRIB_RELEASE
elif [ -f /etc/debian_version ]; then
    OS=Debian  # XXX or Ubuntu??
    VER=$(cat /etc/debian_version)
elif [ -f /etc/centos-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    OS=$(uname -s)
    VER=$(uname -r)
fi

case $OS in
    "Ubuntu" )
    	if [ $VER == "14.04" ]; then
    	    cd ubuntu14
    	    bash bootstrap.sh
    	elif [ $VER == "16.04" ]; then
    	    cd ubuntu16
    	    bash bootstrap.sh
    	else
    	    echo "Currently only 14.04 or 16.04 LTS is supported"
    		echo "We accept Pull Requests! =)"
       	fi
       	;;

    "Debian" )
        echo 'Debian not yet supported...'
        echo "We accept Pull Requests! =)"
        exit 1;;

    "Darwin" )
        echo 'Darwin not yet supported...'
        echo "We accept Pull Requests! =)"
        exit 1;;

    "Redhat" )
        echo 'Redhat not yet supported...'
        echo "We accept Pull Requests! =)"
        exit 1;;

    "CentOS Linux" )
        if [ $VER == '7' ]; then
            cd centos7
            bash bootstrap.sh
        else
            echo 'only CentOS 7 is supported'
            echo "We accept Pull Requests! =)"
        fi
        ;;

esac
