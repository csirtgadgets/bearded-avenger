#!/bin/bash

set -e

# Drop root privileges if we are running cif allow the container to be started with `--user`
if [ "$1" = 'cif' -a "$(id -u)" = '0' ]; then
	# Change the ownership of /data to cif
	chown -R cif:cif /data

	# create cif tokens

	set -- gosu cif "$@"
	#exec gosu cif "$BASH_SOURCE" "$@"


fi

# As argument is not related to cif, then assume that user wants to run his own process, for example a `bash` shell to
# explore this image
exec "$@"