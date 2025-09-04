#!/bin/bash

set -e

[ -d nfdump/ ] || git clone https://github.com/phaag/nfdump
cd nfdump/ || exit

git status
git checkout v1.6.25

apt-get install -y libtool pkg-config flex bison libbz2-dev libpcap-dev

[ -f ./configure ] || ./autogen.sh 
./configure --enable-nfpcapd   
make

