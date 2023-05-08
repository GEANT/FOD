#!/bin/bash

force_reinstall=0
testonly=0
if [ "$1" = "--reinstall" ]; then
  shift 1
  force_reinstall=1
elif [ "$1" = "--testonly" ]; then
  shift 1
  testonly=1
fi

#

docker_label__fod="ubuntu0"
docker_label__rtr1="rtr-flowspec1"

#####

set -e
set -x

#############################################################################
#############################################################################
# prerequistes checking

if ! docker ps &>/dev/null; then
  echo "docker.io needs to be installed and needs to be reunning" 1>&2
  exit 1
fi

#############################################################################
#############################################################################

if [ "$force_reinstall" = 1 ]; then
  dockerid_fod="$(docker ps | awk '$2==docker_label { print $1; }' docker_label="$docker_label__fod")"
  dockerid_rtr1="$(docker ps | awk '$2==docker_label { print $1; }' docker_label="$docker_label__rtr1")"
  if [ -n "$dockerid_fod" -o -n "$dockerid_rtr1" ]; then
    docker stop $dockerid_fod $dockerid_rtr1
  fi
  docker rmi -f "$docker_label__fod" "$docker_label__rtr1"
fi

#############################################################################
#############################################################################
# actual buidling and running the docker images

if [ "$testonly" != 1 ]; then

(
  cd ./ubuntu_os_docker 

  if ! docker inspect "$docker_label__rtr1" &>/dev/null || ! docker ps | grep -q "$docker_label__rtr1"; then
    ./mybuildrun_ubuntu0 --bg_no_enter
  fi

  # ./fodexabgp-install/prep_fod_exabgp2_on_ubuntu.sh
  ./myenter_ubuntu0 sh -c "cd /root/fodexabgp-install && ./prep_fod_exabgp2_on_ubuntu.sh"
)

dockerid_fod="$(docker ps | awk '$2==docker_label { print $1; }' docker_label="$docker_label__fod")"
echo "$0: dockerid_fod=$dockerid_fod" 1>&2

ip_address_fod="$(docker inspect "$dockerid_fod" | grep '"IPAddress":' | tr -d '":,' | awk 'NR==1 { print $2; }')"
echo "$0: ip_address_fod=$ip_address_fod" 1>&2

##

(
  cd ./freertr-flowspec1_docker/

  # ./freertr-flowspec1_docker/mybuildrun-rtr-flowspec1
  ./mybuildrun-rtr-flowspec1 --bg "$ip_address_fod"
)

dockerid_rtr1="$(docker ps | awk '$2==docker_label { print $1; }' docker_label="$docker_label__rtr1")"
echo "$0: dockerid_rtr1=$dockerid_rtr1" 1>&2

ip_address_rtr1="$(docker inspect "$dockerid_rtr1" | grep '"IPAddress":' | tr -d '":,' | awk 'NR==1 { print $2; }')"
echo "$0: ip_address_rtr1=$ip_address_rtr1" 1>&2

##

# configure and run exabgp in foreground:
#./ubuntu_os_docker/myenter_ubuntu0 sh -c 'cd /opt/FOD && . venv/bin/activate && "$@"' -- ./exabgp/run-exabgp-generic "$ip_address_fod" "$ip_address_fod" 1001 "$ip_address_rtr1" "$ip_address_rtr1" 2001

# configure and start exabgp in background controlled by systemd
./ubuntu_os_docker/myenter_ubuntu0 sh -c 'cd /opt/FOD && . venv/bin/activate && "$@"' -- ./exabgp/run-exabgp-generic --init-conf "$ip_address_fod" "$ip_address_fod" 1001 "$ip_address_rtr1" "$ip_address_rtr1" 2001 -- --systemd --enable

fi #endif testonly!=1

#############################################################################
#############################################################################
# do some test access

./ubuntu_os_docker/myenter_ubuntu0 sh -c 'cd /opt/FOD && . venv/bin/activate && "$@"' -- exabgpcli show adj-rib out
echo

./ubuntu_os_docker/myenter_ubuntu0 sh -c 'cd /opt/FOD && . venv/bin/activate && "$@"' -- ./vnet_router/fodtest_netconf_get --raw
echo

./ubuntu_os_docker/myenter_ubuntu0 sh -c 'cd /opt/FOD && . venv/bin/activate && "$@"' -- ./vnet_router/fodtest_netconf_get
echo

#

./freertr-flowspec1_docker/myenter_rtr-flowspec1 --rcmd show interfaces
echo

./freertr-flowspec1_docker/myenter_rtr-flowspec1 --rcmd show ipv4 bgp 1 flowspec summary
echo

./freertr-flowspec1_docker/myenter_rtr-flowspec1 --rcmd show ipv4 bgp 1 flowspec database
echo

./freertr-flowspec1_docker/myenter_rtr-flowspec1 --rcmd show policy-map flowspec OOB ipv4
echo

#############################################################################
#############################################################################

