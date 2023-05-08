

./prep_fod_exabgp2_on_ubuntu.sh : script to install FoD exabgp version on an DEBIAN or UBUNTU OS running systemd, ../ubuntu_os_docker may be used as a base for this, if host OS is not DEBIAN or UBUNTU running systemd

1.
after running of this script, FoD (version with exabgp support) 
should be git-cloned in /opt/FOD and fully setup-ed to run from that very same directory
and should be started by systemd
it comprises 2 systemd units 
fod-gunicorn and fod-celeryd
(bridged via redis and a local sqlite database file named /opt/FOD/example-data)

2.
Generally, after FoD installation, first admin user has still to be setup, either in cli (check ./prep_fod_exabgp2_on_ubuntu.sh for examples as comments)
or via http://.../setup web UI
Alternatively, ./install.sh now supports options to setup the first admin user
(check ./prep_fod_exabgp2_on_ubuntu.sh)

3.
exabgp has still to be started manually with local BGP node id/ip address/AS and remote BGP node id/ip address/AS (freertr peer)
examples can be found in ./prep_fod_exabgp2_on_ubuntu.sh as comments,
e.g.,

cd /opt/FOD
source ./venv/bin/activate
./exabgp/run-exabgp-generic 172.17.0.1 172.17.0.1 1001 172.17.0.2 172.17.0.2 2001 # in case FoD is running directly on host OS (not in a docker container; ./prep_fod_exabgp2_on_ubuntu having been executed on the host OS directly) and rtr-flowspec1 docker container is first started docker container, so having probably 172.17.0.2 as eth's IP address

or

cd /opt/FOD
source ./venv/bin/activate
./exabgp/run-exabgp-generic 172.17.0.2 172.17.0.2 1001 172.17.0.3 172.17.0.3 2001 # in case FoD is running in first started docker container (./prep_fod_exabgp2_on_ubuntu.sh having been executed in that docker container, e.g. using ../ubuntu_os_docker/ container) and so probably having eth0 IP address 172.17.0.2 and rtr-flowspec1 docker container is second started docker container
 started docker container, so having probably 172.17.0.2 as eth's IP address




