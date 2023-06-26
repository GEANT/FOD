#!/bin/bash

ethtool -k eth0 | awk '$2=="on" { sub(/:$/, "", $1); print $1; }' | while read key; do ethtool -K eth0 "$key" off; done
ethtool -k eth1 | awk '$2=="on" { sub(/:$/, "", $1); print $1; }' | while read key; do ethtool -K eth1 "$key" off; done
ethtool -k eth2 | awk '$2=="on" { sub(/:$/, "", $1); print $1; }' | while read key; do ethtool -K eth2 "$key" off; done
ethtool -k eth3 | awk '$2=="on" { sub(/:$/, "", $1); print $1; }' | while read key; do ethtool -K eth3 "$key" off; done

/rtr/hwdet-init.sh

/rtr/hwdet-mgmt.sh

ip addr flush dev eth1
ip addr flush dev eth2
ip addr flush dev eth3

exec java -Xmx1024m -jar /rtr/rtr.jar routerc /rtr/run/conf/rtr-
