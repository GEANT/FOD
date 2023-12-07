#!/bin/bash

# to be run from FoD main dir

# ./docker-compose/README.txt

#################################

use_novol=1

if [ "$use_novol" = 1 ]; then
  #docker_compose_spec__file="./docker-compose-novol.yml"
  docker_compose_spec__file="./docker-compose-singlefodctr-novol.yml"
  fod_container_name="fodnovol"
else
  #docker_compose_spec__file="./docker-compose.yml"
  #fod_container_name="fod"
  docker_compose_spec__file="./docker-compose-singlefodctr-vol.yml"
  fod_container_name="fodvol"
fi

#################################
# helper functions

function echocol1n() {
   echo -n -e "\e[33;1m$*\e[0m"
}

function echocol1() {
   echo -e "\e[33;1m$*\e[0m"
}

function waitdelay1 () {
  (set +e
    arg1="$1"

    [ -n "$arg1" ] || arg1="$wait1"

    echo 1>&2
    if [ "$arg1" = "-1" ]; then
      echocol1 "press RETURN" 1>&2
      read	
    else
      echocol1 "waiting $arg1 seconds" 1>&2
      sleep "$arg1"
    fi
  )
}

function echo0 () {
  (set +e	
    echocol1 "$@"
    echo 1>&2
  )
}

function echo1waitpress() {
  echocol1n "."
  (stty -echo
   trap 'stty echo' EXIT
   read
   stty echo
   trap '' EXIT)
  echo -e -n "  "      
}

function echo1 () {
  (set +e	

    if [ "$waite" = "-1" ]; then
      echo1waitpress
    fi

    echocol1 "$@"
    echo 1>&2

    if [ "$waite" = "-1" ]; then
      #sleep "2"
      echo1waitpress
    elif [ "$waite" != 0 ]; then 
      sleep "$waite"
    fi
  ) 
}

#################################

function output_with_specific_colormarks() {
  regex="$1"
  shift 1

  if type awk &>/dev/null; then
    awk '
      $0 ~ regex {  
        print "\x1b[31;1m" $0 "\x1b[0m"
        next
      }
      { print; }      
    ' regex="$regex"
  else
    cat
  fi
}  

function show_container_overview()
{
  echo 'container overview:'
  echo 
  echo "                 <---> host 1 (attacker $attacker_ip)"
  echo '                /'
  echo ' FoD <-> Freertr '
  echo '                \'
  echo "                 <---> host 2 (victim   $victim_ip)"
  echo 
  echo 
}

#################################

wait1=30
waite=2

if [ "$1" = "--waittime" ]; then
  shift 1
  wait1="$1"
  shift 1
elif [ "$1" = "--waitkey" -o "$1" = "--wk" ]; then
  shift 1
  wait1="-1"
  waite=2
fi

if [ "$1" = "--echotime" ]; then
  shift 1
  waite=2
elif [ "$1" = "--noechotime" ]; then
  shift 1
  waite=0
elif [ "$1" = "--echokey" -o "$1" = "--ek" ]; then
  shift 1
  wait1="-1"
  waite="-1"
fi  

#################################

set -e

##


##

# helpers defintions
attacker_ip="10.1.10.11"
victim_ip="10.2.10.12"

##

count_up="$(docker-compose -f "$docker_compose_spec__file" ps | grep Up | wc -l)"

if [ "$1" = "rebuild" ]; then 
  shift 1
  count_up=0
fi

if [ "$count_up" != 4 ]; then

  echo1 "$0: 0.a. docker-compose set not fully setup, trying to do so" 1>&2

  echo1 "$0: 0.a.1. tearing down docker-compse set completely" 1>&2
  (set -x; docker-compose -f "$docker_compose_spec__file" down)
  echo 1>&2

  echo1 "$0: 0.a.2. (re-)building docker-compose set" 1>&2
  (set -x; docker-compose -f "$docker_compose_spec__file" build)
  echo 1>&2

  echo1 "$0: 0.a.3. bringing docker-compose set up" 1>&2
  (set -x; docker-compose -f "$docker_compose_spec__file" up -d)
  echo 1>&2

  reinit_done=1

else
  echo1 "$0: 0.a. docker-compose seems to be ready" 1>&2
  reinit_done=0
fi

#

echo0 "$0: 0.b. running freertr_disable_offload hack" 1>&2
(set -x; ./docker-compose/freertr_disable_offload.sh) || true
echo 1>&2

#

if [ "$1" = "stop" ]; then 
  shift 1
  exit 
fi

#

if [ "$use_novol" != 1 ]; then # compare ./docker-compose/fod_setup_environment-step3.sh used by ./docker-compose/Dockerfile_FOD (in case $novol == 0)
  echo1 "$0: 0.c. making sure bind-mounted FoD dir is setup from within container" 1>&2
  while ! docker exec -ti "$fod_container_name" ls /opt/setup_ok &>/dev/null; do
    echo1 "$0: 0.c. docker container has not yet fully completed setup of FoD dir from inside container, so waiting 1 sec" 1>&2
    sleep 1  
  done
else
  true
fi

#############################################################################
#############################################################################
# start proper of demo

clear
echo 1>&2

echo1 "$0: demo proper:" 1>&2
#echo 1>&2

show_container_overview

echo1 "$0: 1. demo part1: initial ping between host1 and host2" 1>&2
#echo 1>&2


echo1 "$0: 1.a. disabling any left-over rules in FoD:" 1>&2
(set -x; docker exec -ti "$fod_container_name" ./inst/helpers/enable_rule.sh 10.1.10.11/32 10.2.10.12/32 1 -1 "" 0)

echo1 "$0:      list demo rules in FoD:" 1>&2
(set -x; docker exec -ti "$fod_container_name" ./inst/helpers/list_rules_db.sh | grep "10.1.10.11/32.*10.2.10.12/32" || true) | output_with_specific_colormarks 'testrtr1_'

waitdelay1 

#

clear
echo 1>&2

echo1 "$0: 1.b. initial ping between host1 (attacker 10.1.10.11) and host2 (victim 10.2.10.12):" 1>&2

show_container_overview

echo1 "$0:        show exabgp current exported rules/routes:" 1>&2
((set -x; docker exec -ti "$fod_container_name" sh -c '. /opt/venv/bin/activate && exabgpcli show adj-rib out extensive') | grep . || echo "no rules in exabgp DB") | output_with_specific_colormarks .
echo 1>&2

echo1 "$0:        freertr policy-map and block counters:" 1>&2
(set -x; docker exec -ti freertr sh -c '{ echo "show ipv4 bgp 1 flowspec summary"; echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | netcat 127.1 2323') | output_with_specific_colormarks "drp=[0-9]"
echo 1>&2

sleep 2

echo1 "$0:        ping proper NOT to be blocked (attacker 10.1.10.11 -> victim 10.2.10.12):" 1>&2
docker exec -d -ti host1 ping -c 1 10.2.10.12
(set -x; docker exec -ti host1 ping -c 5 10.2.10.12)
echo 1>&2

echo1 "$0:        freertr policy-map and block counters:" 1>&2
(set -x; docker exec -ti freertr sh -c '{ echo "show ipv4 bgp 1 flowspec summary"; echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | netcat 127.1 2323') | output_with_specific_colormarks "drp=[0-9]"

waitdelay1

#

clear
echo 1>&2

#echo 1>&2
echo1 "$0: 2. demo part2: blocked ping between host1 and host2" 1>&2
#echo 1>&2

sleep 2

show_container_overview

echo1 "$0: 2.a. adding of blocking rule:" 1>&2
#echo 1>&2

echo1 "$0:        show exabgp current exported rules/routes (before adding the blocking rule):" 1>&2
((set -x; docker exec -ti "$fod_container_name" sh -c '. /opt/venv/bin/activate && exabgpcli show adj-rib out extensive') | grep . || echo "no rules in exabgp DB") | output_with_specific_colormarks .
echo 1>&2

echo1 "$0:        show freertr flowspec status/statistics (before adding the blocking rule):" 1>&2
(set -x; docker exec -ti freertr sh -c '{ echo "show ipv4 bgp 1 flowspec summary"; echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | netcat 127.1 2323') | output_with_specific_colormarks '(f01:200a:20a:c02:200a:10a:b03:8101)|(drp=.*1-1.*10.1.10.11.*10.2.10.12)'
echo 1>&2

echo1 "$0:        proper adding of blocking rule:" 1>&2
#docker exec -ti "$fod_container_name" ./inst/helpers/add_rule.sh 10.1.10.11 10.2.10.12 1
(set -x; docker exec -ti "$fod_container_name" ./inst/helpers/enable_rule.sh 10.1.10.11/32 10.2.10.12/32 1 "" "" 0)
echo 1>&2

echo1 "$0:        list demo rules in FoD:" 1>&2
(set -x; docker exec -ti "$fod_container_name" ./inst/helpers/list_rules_db.sh | grep "10.1.10.11/32.*10.2.10.12/32" || true) | output_with_specific_colormarks 'testrtr1_'
echo 1>&2

echo1 "$0:        show exabgp current exported rules/routes (after adding the blocking rule):" 1>&2
((set -x; docker exec -ti "$fod_container_name" sh -c '. /opt/venv/bin/activate && exabgpcli show adj-rib out extensive') | grep . || echo "no rules in exabgp DB") | output_with_specific_colormarks .
echo 1>&2

echo1 "$0:        show freertr flowspec status/statistics (after adding the blocking rule):" 1>&2
(set -x; docker exec -ti freertr sh -c '{ echo "show ipv4 bgp 1 flowspec summary"; echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | netcat 127.1 2323') | output_with_specific_colormarks '(f01:200a:20a:c02:200a:10a:b03:8101)|(drp=.*1-1.*10.1.10.11.*10.2.10.12)'

waitdelay1

#

clear
echo 1>&2
echo1 "$0: 2.b. blocked ping between host1 and host2:" 1>&2
#echo 1>&2

sleep 2

show_container_overview

echo1 "$0:        show exabgp current exported rules/routes:" 1>&2
((set -x; docker exec -ti "$fod_container_name" sh -c '. /opt/venv/bin/activate && exabgpcli show adj-rib out extensive') | grep . || echo "no rules in exabgp DB") | output_with_specific_colormarks .
echo 1>&2

echo1 "$0:        show freertr flowpec status/statistics (before ping to be blocked):" 1>&2
(set -x; docker exec -ti freertr sh -c '{ echo "show ipv4 bgp 1 flowspec summary"; echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | netcat 127.1 2323') | output_with_specific_colormarks "drp=[0-9]"
echo 1>&2

echo1 "$0:        ping proper to be blocked (attacker 10.1.10.11 -> victim 10.2.10.12):" 1>&2
(set -x; docker exec -ti host1 ping -c 5 10.2.10.12) || true
echo 1>&2

echo1 "$0:        show freertr flowspec status/statistics (after ping to be blocked):" 1>&2
(set -x; docker exec -ti freertr sh -c '{ echo "show ipv4 bgp 1 flowspec summary"; echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | netcat 127.1 2323') | output_with_specific_colormarks "drp=[0-9]"
echo 1>&2


