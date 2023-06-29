#!/bin/bash

if systemctl cat redis &>/dev/null; then
  SYSTEMD_COLORS=1 systemctl status "redis" | cat 
else
  SYSTEMD_COLORS=1 systemctl status "redis-server" | cat
fi
echo

SYSTEMD_COLORS=1 systemctl status "exabgpForFod" | cat
echo

SYSTEMD_COLORS=1 systemctl status "fod-gunicorn" | cat
echo

SYSTEMD_COLORS=1 systemctl status "fod-celeryd" | cat
echo

