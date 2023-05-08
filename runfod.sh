#!/bin/sh

if [ -f "./runfod.conf" ]; then
  . "./runfod.conf"
fi

#

if [ -n "$ifc_setup__name" ]; then
  echo "$0: setting ip address of $ifc_setup__name to $ifc_setup__ip_addr_and_subnetmask" 1>&2

  if [ "$ifc_setup__wait_for_ifc__in_runfod" = 1 ]; then
    while ! ifconfig "$ifc_setup__name" 1>&2; do
      echo "$0: interface $ifc_setup__name not available yet, waiting" 1>&2
      sleep 1
    done
  fi

  ifconfig "$ifc_setup__name" "$ifc_setup__ip_addr_and_subnetmask"

fi

#

if [ "$FOD_RUNMODE" = "via_systemd" ]; then
  echo "$0: using runmode via_systemd, nothing todo" 1>&2

  SYSTEMD_COLORS=1 systemctl status "fod-gunicorn" | cat
  echo

  SYSTEMD_COLORS=1 systemctl status "fod-celeryd" | cat
  echo

  SYSTEMD_COLORS=1 systemctl status "redis" | cat
  echo

  SYSTEMD_COLORS=1 systemctl status "exabgpForFod" | cat
  echo

elif [ "$FOD_RUNMODE" = "via_supervisord" ]; then
  echo "$0: using runmode via_supervisord" 1>&2
  exec ./runfod-supervisord.sh "$@"
else
  echo "$0: using runmod fg" 1>&2
  exec ./runfod-fg.sh "$@"
fi

