#!/bin/bash
IFINDEX=$(docker exec freertr cat /sys/class/net/eth0/iflink)
IFNAME=$(ip a | grep ^${IFINDEX} | awk -F\: '{print $2}' | awk -F\@ '{print $1}')
ethtool -k $IFNAME | awk '$2=="on" { sub(/:$/, "", $1); print $1; }' | while read key; do ethtool -K $IFNAME "$key" off; done
