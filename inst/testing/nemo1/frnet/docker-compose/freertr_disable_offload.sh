#!/bin/bash


for container_interface in 0 1 2 3 4 5; do
  IFINDEX="$(docker exec freertr cat "/sys/class/net/eth$container_interface/iflink")"
  [ -n "$IFINDEX" ] || continue

  IFNAME="$(ip a | grep ^${IFINDEX} | awk -F\: '{print $2}' | awk -F\@ '{print $1}')"
  IFNAME="${IFNAME# }"
  [ -n "$IFNAME" ] || continue

  echo "# container_interface eth$container_interface => IFINDEX=$IFINDEX => IFNAME of pair endpoint interface in current net ns=$IFNAME" 1>&2

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

    ethtool -k "$IFNAME" | awk '{ sub(/^\s+/, ""); } $2=="on" { sub(/:$/, "", $1); print $1; }' 

  } | while read key; do (ethtool -K "$IFNAME" "$key" off); done

  echo "# resulting ethtool settings for interface $IFNAME (pair end point of eth$container_interface in container freertr):"
  ethtool -k "$IFNAME" | grep " on"
  echo

done

