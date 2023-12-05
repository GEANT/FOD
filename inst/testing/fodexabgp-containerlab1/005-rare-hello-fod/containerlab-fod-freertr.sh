#!/bin/bash

# to be run from dir containing the script

# ./containerlab-fod-freertr.txt
# ./README.md

#################################
# helper functions

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

function echo1 () {
  (set +e	
    echo 1>&2
    echocol1 "$@"
    echo 1>&2

    [ "$waite" = 0 ] || sleep "$waite"
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

#################################

wait1=30
waite=2

if [ "$1" = "--waittime" ]; then
  shift 1
  wait1="$1"
  shift 1
fi

if [ "$1" = "--waitecho" ]; then
  shift 1
  waite=2
elif [ "$1" = "--nowaitecho" ]; then
  shift 1
  waite=0
fi  

if [ "$1" = "--keypress" ]; then
  shift 1
  wait1="-1"
  waite=2
fi



wait_time_for_time_to_read=10
if [ "$1" = "--quick" ]; then
  shift 1
  wait_time_for_time_to_read=0
fi

echo "$0: wait_time_for_time_to_read=$wait_time_for_time_to_read" 1>&2

###

set -e

##

type -p containerlab >/dev/null || { echo "containerlab must be installed"; exit 1; }

echo1 "$0: 0.a. git clone repo (dummy command):" 1>&2 
# not really executed here, as we are just working in the already check-out working dir here:
echo "git clone https://github.com/rare-freertr/freeRtr-containerlab && cd ./freeRtr-containerlab/lab/005-rare-hello-fod"

echo1 "or:"
echo "git clone -b feature/exabgp-support2 https://github.com/GEANT/FOD && cd ./FOD/inst/testing/fodexabgp-containerlab1/005-rare-hello-fod/"

#if [ ! -d ./freeRtr-containerlab/lab/005-rare-hello-fod ]; then
#  (set -x; git clone https://github.com/rare-freertr/freeRtr-containerlab && cd ./freeRtr-containerlab/lab/005-rare-hello-fod)
#  cd ./freeRtr-containerlab/lab/005-rare-hello-fod
#else
#  (set -x; cd ./freeRtr-containerlab/lab/005-rare-hello-fod)
#  cd ./freeRtr-containerlab/lab/005-rare-hello-fod
#fi

echo1 "$0: 0.b. (re-)init containerlab:" 1>&2
(set -x; containerlab destroy -t rtr005.clab.yml || true)
#(set -x; containerlab deploy --reconfigure -t rtr005.clab.yml)
(set -x; containerlab deploy -t rtr005.clab.yml)

echo1 "$0: 0.c. check containerlab:" 1>&2
(set -x; containerlab inspect -t rtr005.clab.yml) # for later inspection, if needed

# really needed
#set +x
w=10
echo1 "$0: sleeping $w seconds, to give freertr and FoD time to get ready" 1>&2
sleep "$w" # need enough time for freertr to be ready
#set -x

clear

##

echo1 "$0: 1. setup of hosts + test0: unblocked ping (FoD's exabgp not yet connected to freertr)" 1>&2
echo1 "$0: (freertr is already configured as needed by ./clab-rtr005/rtr1/run/conf/rtr-sw.txt : interface as well as server bgp config)" 1>&2

echo1 "$0: 1.a. setup of hosts" 1>&2

echo1 "$0: 1.a.1 setup of host1 (attacker 10.1.10.1)" 1>&2
(set -x; docker exec -ti clab-rtr005-host1 ifconfig eth1 10.1.10.1 netmask 255.255.255.0)
(set -x; docker exec -ti clab-rtr005-host1 route add -net 10.2.10.0 netmask 255.255.255.0 gw 10.1.10.10)

echo1 "$0: 1.a.2 setup of host2 (victim 10.2.10.2)" 1>&2
(set -x; docker exec -ti clab-rtr005-host2 ifconfig eth1 10.2.10.2 netmask 255.255.255.0)
(set -x; docker exec -ti clab-rtr005-host2 route add -net 10.1.10.0 netmask 255.255.255.0 gw 10.2.10.10)

##

echo1 "$0: 1.b. test0: unblocked ping (FoD's exabgp not yet connected to freertr)" 1>&2

echo1 "$0: 1.b.0. check freetrtr flowspec status/statistics (before unblocked ping):" 1>&2
#docker exec -ti clab-rtr005-rtr1 sh -c 'apt-get update && apt-get install netcat-traditional'
#docker exec -ti clab-rtr005-rtr1 sh -c '{ echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | netcat 127.1 2323'
(set -x; docker exec -ti clab-rtr005-rtr1 bash -c '{ echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | (exec 3<>/dev/tcp/127.0.0.1/2323; cat >&3; cat <&3; exec 3<&-)') | output_with_specific_colormarks "drp=[0-9]"


echo1 "$0: 1.b.1 unblocked ping (FoD's exabgp not yet connected to freertr)" 1>&2
(set -x; docker exec -ti clab-rtr005-host1 ping -c 5 10.2.10.2)
#(set -x; docker exec -ti clab-rtr005-host2 ping -c 5 10.1.10.1)

echo1 "$0: 1.b.2. check freetrtr flowspec status/statistics (after blocked ping):" 1>&2
(set -x; docker exec -ti clab-rtr005-rtr1 bash -c '{ echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | (exec 3<>/dev/tcp/127.0.0.1/2323; cat >&3; cat <&3; exec 3<&-)') | output_with_specific_colormarks "drp=[0-9]"

#echo 1>&2
#wait1="$wait_time_for_time_to_read"
#if [ "$wait_time_for_time_to_read" -gt 0 ]; then
#  echo "waiting $wait1 (wait_time_for_time_to_read) seconds" 1>&2
#  sleep "$wait1"
#  clear
#fi
if [ "$wait_time_for_time_to_read" -gt 0 ]; then
  waitdelay1 
  clear
  echo 1>&2
else
  echo 1>&2
fi

##

echo1 "$0: 2. add peering of fod's exabg to freertr:" 1>&2

(set -x; docker exec -ti clab-rtr005-fod1 ifconfig eth1 10.3.10.3/24)
(set -x; docker exec -ti clab-rtr005-fod1 ./exabgp/run-exabgp-generic --init-conf 10.3.10.3 10.3.10.3 1001 10.3.10.10 10.3.10.10 2001 -- --supervisord --restart)
#to check the exabgp stdout: 
sleep 10 && (set -x; docker exec -ti clab-rtr005-fod1 tail log/exabgp-stdout.log)

#

#wait1="$wait_time_for_time_to_read"
#if [ "$wait_time_for_time_to_read" -gt 0 ]; then
#  echo "waiting $wait1 (wait_time_for_time_to_read) seconds" 1>&2
#  sleep "$wait1"
#  clear
#fi
if [ "$wait_time_for_time_to_read" -gt 0 ]; then
  waitdelay1 
  clear
  echo 1>&2
else
  echo 1>&2
fi

#############################################################################
#############################################################################
# start proper of demo

clear
echo 1>&2

echo1 "$0: demo proper:" 1>&2
#echo 1>&2

echo1 "$0: 3. test1: blocked ping (with FoD's exabgp peering to freertr):" 1>&2

echo1 "$0: 3.a. test1.a: add blocking rule via BGP" 1>&2

echo1 "$0: 3.a.1.a. show exabgp current exported rules/routes (before adding the blocking rule):" 1>&2
(set -x; docker exec -ti clab-rtr005-fod1 sh -c '. ./venv/bin/activate && exabgpcli show adj-rib out extensive') | output_with_specific_colormarks .

echo1 "$0: 3.a.1.b. show freertr flowspec status/statistics (before adding the blocking rule):" 1>&2
#(set -x; docker exec -ti clab-rtr005-rtr1 bash -c '{ echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | (exec 3<>/dev/tcp/127.0.0.1/2323; cat >&3; cat <&3; exec 3<&-)') | output_with_specific_colormarks "drp=[0-9]"
(set -x; docker exec -ti clab-rtr005-rtr1 bash -c '{ echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | (exec 3<>/dev/tcp/127.0.0.1/2323; cat >&3; cat <&3; exec 3<&-)') | output_with_specific_colormarks '(f01:200a:20a:202:200a:10a:103:8101)|(drp=.*1-1.*10.1.10..*.*10.2.10..*)'

echo1 "$0: 3.a.2. proper adding of blocking rule:" 1>&2
(set -x; docker exec -ti clab-rtr005-fod1 ./inst/helpers/enable_rule.sh 10.1.10.1/32 10.2.10.2/32 1 1 "" 0) # first parameter: src IP prefix; second parameter: dst IP prefix; third parameter: 1=icmp ; 4-th parameter: 1=enable rule on router, i.e., push it now

echo1 "$0:        list demo rules in FoD:" 1>&2
(set -x; docker exec -ti clab-rtr005-fod1 ./inst/helpers/list_rules_db.sh | grep "10.1.10..*/32.*10.2.10..*/32" || true) | output_with_specific_colormarks 'testrtr1_'

echo1 "$0: 3.a.3.a. show exabgp current exported rules/routes (after adding the blocking rule):" 1>&2
(set -x; docker exec -ti clab-rtr005-fod1 sh -c '. ./venv/bin/activate && exabgpcli show adj-rib out extensive') | output_with_specific_colormarks .

echo1 "$0: 3.a.3.b. show freertr flowspec status/statistics (after adding the blocking rule):" 1>&2
#(set -x; docker exec -ti clab-rtr005-rtr1 bash -c '{ echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | (exec 3<>/dev/tcp/127.0.0.1/2323; cat >&3; cat <&3; exec 3<&-)') | output_with_specific_colormarks "drp=[0-9]"
(set -x; docker exec -ti clab-rtr005-rtr1 bash -c '{ echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | (exec 3<>/dev/tcp/127.0.0.1/2323; cat >&3; cat <&3; exec 3<&-)') | output_with_specific_colormarks '(f01:200a:20a:202:200a:10a:103:8101)|(drp=.*1-1.*10.1.10..*.*10.2.10..*)'

#

#echo 1>&2
#wait1="$wait_time_for_time_to_read"
#if [ "$wait_time_for_time_to_read" -gt 0 ]; then
#  echo "waiting $wait1 (wait_time_for_time_to_read) seconds" 1>&2
#  sleep "$wait1"
#  clear
#fi
if [ "$wait_time_for_time_to_read" -gt 0 ]; then
  waitdelay1 
  clear
  echo 1>&2
fi

##

echo1 "$0: 3.b. test1.b: perform ping to be blocked with status/statistics before and afterwards:" 1>&2

echo1 "$0: 3.b.1. show exabgp current exported rules/routes:" 1>&2
(set -x; docker exec -ti clab-rtr005-fod1 sh -c '. ./venv/bin/activate && exabgpcli show adj-rib out extensive') | output_with_specific_colormarks .

echo1 "$0: 3.b.2. show freertr flowspec status/statistics (before ping to be blocked):" 1>&2
(set -x; docker exec -ti clab-rtr005-rtr1 bash -c '{ echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | (exec 3<>/dev/tcp/127.0.0.1/2323; cat >&3; cat <&3; exec 3<&-)') | output_with_specific_colormarks "drp=[0-9]"


echo1 "$0: 3.b.3. perform proper ping to be blocked:" 1>&2
(set -x; ! docker exec -ti clab-rtr005-host1 ping -c 10 10.2.10.2)
#(set -x; ! docker exec -ti clab-rtr005-host2 ping -c 10 10.1.10.1)

echo1 "$0: 3.b.4. show freertr flowspec status/statistics (after ping to be blocked):" 1>&2
(set -x; docker exec -ti clab-rtr005-rtr1 bash -c '{ echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | (exec 3<>/dev/tcp/127.0.0.1/2323; cat >&3; cat <&3; exec 3<&-)') | output_with_specific_colormarks "drp=[0-9]"


#

#wait1="$wait_time_for_time_to_read"
#if [ "$wait_time_for_time_to_read" -gt 0 ]; then
#  echo "waiting $wait1 (wait_time_for_time_to_read) seconds" 1>&2
#  sleep "$wait1"
#  clear
#fi
if [ "$wait_time_for_time_to_read" -gt 0 ]; then
  waitdelay1 
  clear
  echo 1>&2
else
  echo 1>&2
fi

##

echo1 "$0: 4. test2: unblocked ping (with FoD's exabgp peering to freertr)" 1>&2

echo1 "$0: 4.a. test2.a: remove blocking rule via BGP" 1>&2

echo1 "$0: 4.a.1.a. show exabgp current exported rules/routes (before removing the blocking rule):" 1>&2
(set -x; docker exec -ti clab-rtr005-fod1 sh -c '. ./venv/bin/activate && exabgpcli show adj-rib out extensive') | output_with_specific_colormarks .

echo1 "$0: 4.a.1.b. show freertr flowspec status/statistics (before removing the blocking rule):" 1>&2
(set -x; docker exec -ti clab-rtr005-rtr1 bash -c '{ echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | (exec 3<>/dev/tcp/127.0.0.1/2323; cat >&3; cat <&3; exec 3<&-)')

echo1 "$0: 4.a.2. proper removing of the blocking rule via BGP:" 1>&2
(set -x; docker exec -ti clab-rtr005-fod1 ./inst/helpers/enable_rule.sh 10.1.10.1/32 10.2.10.2/32 1 0 "" 0) # first parameter: src IP prefix; second parameter: dst IP prefix; 3-rd parameter: 1=icmp ; 4-th parameter: 0=disable rule on router if it exists and is active or just create rule in INACTIVE state in FoD DB 

echo1 "$0:        list demo rules in FoD:" 1>&2
(set -x; docker exec -ti clab-rtr005-fod1 ./inst/helpers/list_rules_db.sh | grep "10.1.10..*/32.*10.2.10..*/32" || true) | output_with_specific_colormarks 'testrtr1_'

echo1 "$0: 4.a.3.a. show exabgp current exported rules/routes (after removing the blocking rule):" 1>&2
(set -x; docker exec -ti clab-rtr005-fod1 sh -c '. ./venv/bin/activate && exabgpcli show adj-rib out extensive') | output_with_specific_colormarks .

echo1 "$0: 4.a.3.b. show freertr flowspec status/statistics (after removing the blocking rule):" 1>&2
(set -x; docker exec -ti clab-rtr005-rtr1 bash -c '{ echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | (exec 3<>/dev/tcp/127.0.0.1/2323; cat >&3; cat <&3; exec 3<&-)')

#

#wait1="$wait_time_for_time_to_read"
#if [ "$wait_time_for_time_to_read" -gt 0 ]; then
#  echo "waiting $wait1 (wait_time_for_time_to_read) seconds" 1>&2
#  sleep "$wait1"
#  clear
#fi
if [ "$wait_time_for_time_to_read" -gt 0 ]; then
  waitdelay1 
  clear
  echo 1>&2
else
  echo 1>&2
fi

##

echo1 "$0: 4.b. test2.b: perform ping NOT to be blocked with status/statistics before and afterwards:" 1>&2

echo1 "$0: 4.b.1. show exabgp current exported rules/routes:" 1>&2
(set -x; docker exec -ti clab-rtr005-fod1 sh -c '. ./venv/bin/activate && exabgpcli show adj-rib out extensive')

echo1 "$0: 4.b.2. show freertr flowspec status/statistics (before ping NOT to be blocked):" 1>&2
(set -x; docker exec -ti clab-rtr005-rtr1 bash -c '{ echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | (exec 3<>/dev/tcp/127.0.0.1/2323; cat >&3; cat <&3; exec 3<&-)') | output_with_specific_colormarks "drp=[0-9]"

echo1 "$0: 4.b.3. proper ping NOT to be blocked:" 1>&2
(set -x; docker exec -ti clab-rtr005-host1 ping -c 5 10.2.10.2)

echo1 "$0: 4.b.4. show freertr flowspec status/statistics (after ping NOT to be blocked):" 1>&2
(set -x; docker exec -ti clab-rtr005-rtr1 bash -c '{ echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | (exec 3<>/dev/tcp/127.0.0.1/2323; cat >&3; cat <&3; exec 3<&-)') | output_with_specific_colormarks "drp=[0-9]"


##
