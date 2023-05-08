#!/bin/bash

foddir="$1"
shift 1

#set -x

if cat /etc/centos-release | grep -q "release 7."; then 

  sqlite_version="$(sqlite3 -version)"

  if [ "$sqlite_version" != "${sqlite_version#3.7.}" ]; then

    echo "$0: sqlite_version=$sqlite_version is too old, trying to fix this" 1>&2

    # https://stackoverflow.com/questions/60826836/improperlyconfiguredsqlite-3-8-3-or-later-is-required-found-s-database

    yum install -y make
    #cd ~ && curl https://www.sqlite.org/2020/sqlite-autoconf-3320100.tar.gz > sqlite-autoconf-3320100.tar.gz && tar xvfz sqlite-autoconf-3320100.tar.gz && cd sqlite-autoconf-3320100 && ./configure && make && make install
    cd ~ && curl https://www.sqlite.org/2023/sqlite-autoconf-3410200.tar.gz > sqlite-autoconf.tar.gz && tar xvfz sqlite-autoconf.tar.gz && cd sqlite-autoconf-3410200 && ./configure && make && make install

    ##

    echo 'export LD_LIBRARY_PATH="/usr/local/lib:$LD_LIBRARY_PATH"' >> "$foddir/fodenv.sh"
    echo 'export LC_ALL=en_US.UTF-8' >> "$foddir/fodenv.sh"
    echo 'export LANG=en_US.UTF-8' >> "$foddir/fodenv.sh"

    ##

#    if [ ! -f "$foddir/supervisord.conf" ]; then
#      echo "$foddir/supervisord.conf not found, not adapting it" 1>&2
#    else
#      yum install -y ed
#      cp -f "$foddir/supervisord.conf" "$foddir/supervisord.conf.prep"
#      #ed /etc/supervisord.conf <<EOF
#      ed "$foddir/supervisord.conf.prep" <<EOF
#/^.program:gunicorn./
#/^command=/
#a
#environment=LD_LIBRARY_PATH=/usr/local/lib
#.
#/^.program:celeryd./
#/^command=/
#a
#environment=LD_LIBRARY_PATH=/usr/local/lib
#.
#w
#EOF
#
#    fi

  fi

fi

