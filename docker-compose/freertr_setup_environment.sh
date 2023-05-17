#!/bin/bash

ethtool -k eth0 | awk '$2=="on" { sub(/:$/, "", $1); print $1; }' | while read key; do ethtool -K eth0 "$key" off; done

/rtr/hwdet-init.sh

/rtr/hwdet-mgmt.sh

exec java -Xmx1024m -jar /rtr/rtr.jar routerc /rtr/run/conf/rtr-
