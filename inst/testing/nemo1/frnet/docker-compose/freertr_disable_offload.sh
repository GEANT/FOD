#!/bin/bash


for container_interface in 0 1 2 3; do
  #IFINDEX=$(docker exec freertr cat /sys/class/net/eth0/iflink)
  IFINDEX=$(docker exec freertr cat "/sys/class/net/eth$container_interface/iflink")
  IFNAME=$(ip a | grep ^${IFINDEX} | awk -F\: '{print $2}' | awk -F\@ '{print $1}')
  echo "IFINDEX=$IFINDEX => IFNAME=$IFNAME" 1>&2

  { 
    echo rx 
    echo tx 
    echo sg 
    echo tso 
    echo ufo 
    echo gso 
    echo gro 
    echo lro
    echo rxvlan 
    echo txvlan 
    echo ntuple 
    echo rxhash 

    ethtool -k $IFNAME | awk '{ sub(/^\s+/, ""); } $2=="on" { sub(/:$/, "", $1); print $1; }' 

  } | while read key; do (ethtool -K $IFNAME "$key" off); done

  ethtool -k $IFNAME | grep " on"
  echo

done

