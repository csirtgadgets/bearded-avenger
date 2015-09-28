This portfile installs ansible from the git repository, it will install the
latest and greatest version of ansible. This portfile does not install the
required dependencies to run in accelerated mode.

## Installing the stable version of ansible via macports

If you wish to run a stable version of bearded-avenger please do the following

First update your macports repo to the latest versions

  $ sudo port sync

Then install bearded-avenger

  $ sudo port install bearded-avenger

## Installing the devel version of bearded-avenger via macports

To use this Portfile to install the development version of ansible one should
follow the instructions at
<http://guide.macports.org/#development.local-repositories>

The basic idea is to add the _bearded-avenger/packaging/macports_ directory to your
_/opt/local/etc/macports/sources.conf_ file. You should have something similar
to this at the end of the file

  file:///Users/jtang/develop/bearded-avenger/packaging/macports
  rsync://rsync.macports.org/release/tarballs/ports.tar [default]

In the _bearded-avenger/packaging/macports_ directory, do this

  $ portindex

Once the index is created the _Portfile_ will override the one in the upstream
macports repository.

Installing newer development versions should involve an uninstall, clean,
install process or else the Portfile will need its version number/epoch
bumped.
