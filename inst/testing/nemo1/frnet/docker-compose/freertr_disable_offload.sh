#!/bin/bash

set -x

for container_interface in 0 1 2 3; do
  #IFINDEX=$(docker exec freertr cat /sys/class/net/eth0/iflink)
  IFINDEX=$(docker exec freertr cat "/sys/class/net/eth$container_interface/iflink")
  IFNAME=$(ip a | grep ^${IFINDEX} | awk -F\: '{print $2}' | awk -F\@ '{print $1}')
  ethtool -k $IFNAME | awk '$2=="on" { sub(/:$/, "", $1); print $1; }' | while read key; do ethtool -K $IFNAME "$key" off; done
done

