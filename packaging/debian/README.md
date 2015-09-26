bearded-avenger Debian Package
==============================

To create a DEB package:

    sudo apt-get install python-yaml python-setuptools debhelper dpkg-dev git-core reprepro python-support fakeroot asciidoc devscripts
    git clone git://github.com/csirtgadgets/bearded-avenger.git
    cd bearded-avenger
    make deb

The debian package file will be placed in the `packaging/` directory. This can then be added to an APT repository or 
installed with `dpkg -i <package-file>`.

Note that `dpkg -i` does not resolve dependencies.

To install the bearded-avenger DEB package and resolve dependencies:

    sudo dpkg -i <package-file>
    sudo apt-get -fy install