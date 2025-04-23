#!/bin/bash

/rtr/veth.bin veth1 veth2 1500 1500 2:1:1:1:1:1 3:1:1:1:1:1
ifconfig veth1 up
ifconfig veth2 up

#

ethtool -k eth0 | awk '$2=="on" { sub(/:$/, "", $1); print $1; }' | while read key; do ethtool -K eth0 "$key" off; done
ethtool -k eth1 | awk '$2=="on" { sub(/:$/, "", $1); print $1; }' | while read key; do ethtool -K eth1 "$key" off; done
ethtool -k eth2 | awk '$2=="on" { sub(/:$/, "", $1); print $1; }' | while read key; do ethtool -K eth2 "$key" off; done
ethtool -k eth3 | awk '$2=="on" { sub(/:$/, "", $1); print $1; }' | while read key; do ethtool -K eth3 "$key" off; done
ethtool -k eth4 | awk '$2=="on" { sub(/:$/, "", $1); print $1; }' | while read key; do ethtool -K eth4 "$key" off; done
ethtool -k eth5 | awk '$2=="on" { sub(/:$/, "", $1); print $1; }' | while read key; do ethtool -K eth5 "$key" off; done

ethtool -k veth1 | awk '$2=="on" { sub(/:$/, "", $1); print $1; }' | while read key; do ethtool -K veth1 "$key" off; done
ethtool -k veth2 | awk '$2=="on" { sub(/:$/, "", $1); print $1; }' | while read key; do ethtool -K veth2 "$key" off; done

#

/rtr/hwdet-init.sh

/rtr/hwdet-mgmt.sh

cat /rtr/rtr-hw-add.txt >> /rtr/run/conf/rtr-hw.txt

ip addr flush dev eth1
ip addr flush dev eth2
ip addr flush dev eth3
ip addr flush dev eth4
ip addr flush dev eth5

exec java -Xmx1024m -jar /rtr/rtr.jar routerc /rtr/run/conf/rtr-
