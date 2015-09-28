!#/bin/bash

TMP_PATH=~/tmp_install_python

# Versions section
PYTHON_MAJOR=2.7
PYTHON_VERSION=$PYTHON_MAJOR.10

mkdir $TMP_PATH
cd $TMP_PATH

# Download and extract Python and Setuptools
wget -N https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tgz
wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py
wget https://raw.githubusercontent.com/pypa/pip/master/contrib/get-pip.py
tar -zxvf Python-$PYTHON_VERSION.tgz

# Compile Python
cd Python-$PYTHON_VERSION
./configure --prefix=/usr/local --enable-unicode=ucs2
make && sudo make altinstall
export PATH="/usr/local/bin:$PATH"

# Install Setuptools and PIP
cd $TMP_PATH
sudo /usr/local/bin/python$PYTHON_MAJOR ./ez_setup.py
sudo /usr/local/bin/python$PYTHON_MAJOR ./get-pip.py

# Finish installation
sudo ln -s /usr/local/bin/python2.7 /usr/local/bin/python
sudo ln -s /usr/local/bin/pip /usr/bin/pip
rm -rf $TMP_PATH