#!/bin/bash

use_bg=0
if [ "$1" = "--use_bg" ]; then
  shift 1
  use_bg=1
fi

#

/rtr/hwdet-init.sh

/rtr/hwdet-mgmt.sh

#ethtool -K eth0 generic-receive-offload off
/root/myethtool_disable_offload eth0

if [ "$use_bg" != 1 ]; then
  exec java -Xmx1024m -jar /rtr/rtr.jar routerc /rtr/run/conf/rtr-
else
  exec java -Xmx1024m -jar /rtr/rtr.jar router /rtr/run/conf/rtr-
fi

