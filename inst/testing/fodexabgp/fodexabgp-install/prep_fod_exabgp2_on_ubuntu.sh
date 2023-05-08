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
#./install-debian.sh --here --setup_admin_user --supervisord --setup_admin_user5 admin adminpwd admin@localhost.local testpeer 0.0.0.0/0 # make sure user fod has access right to /opt/FOD
#./install-debian.sh --git-checkout https://github.com/GEANT/FOD feature/exabgp_support2 /opt/FOD --here --setup_admin_user --setup_admin_user5 admin adminpwd admin@localhost.local testpeer 0.0.0.0/0 --exabgp0 "$@"
./install-debian.sh --here --setup_admin_user --setup_admin_user5 admin adminpwd admin@localhost.local testpeer 0.0.0.0/0 --exabgp0 "$@"

#chown -R fod: /opt/FOD/ # fix maybe wrong permissions # not necessary anymore 

#echo "now open http://localhost1:8000/setup/ in your browser"
echo "now open http://localhost1:8000/ in your browser (user admin, pwd adminpwd)"

#. ./venv/bin/activate
#./manage dbshell # delete from auth_user;
#./manage changepassword
#./manage createsuperuser

#. ./venv/bin/activate
#pip install exabgp
#useradd exabgp
#./exabgp/run-exabgp-generic 127.0.0.1 127.0.0.1

