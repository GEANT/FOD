#!/bin/bash

set -e
set -x

mkdir -p /opt
cd /opt

if [ ! -d "./FOD" ]; then
  git clone https://github.com/GEANT/FOD    
fi

cd FOD

git checkout refs/remotes/origin/feature/exabgp_support2
git checkout -b feature/exabgp_support2

#./install-debian.sh --here # make sure user fod has access right to /opt/FOD
./install-debian.sh --here --setup_admin_user "$@" # make sure user fod has access right to /opt/FOD

chown -R fod: /opt/FOD/ # fix potentially wrong permissions # TODO

#echo "now open http://localhost1:8000/setup/ in your browser"
echo "now open http://localhost1:8000/altlogin/ in your browser"

#. ./venv/bin/activate
#./manage dbshell # delete from auth_user;
#./manage changepassword
#./manage createsuperuser

#. ./venv/bin/activate
#pip install exabgp
#useradd exabgp
#./exabgp/run-exabgp-generic 127.0.0.1 127.0.0.1

