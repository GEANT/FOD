#!/bin/bash

arg1="$1" 
shift 1

source ./venv/bin/activate 

##

case "$arg1" in

  -p|--process-status)
    set -e
    echo "# basic process status:" 
    ./manage.py fodinfo -s
    ;;

  -D|--database-access-status)
    nopwds=1
    if [ "$1" = "--with-passwords" ]; then
      nopwds=0
      shift 1
    fi

    set -e
    echo "# database access status:" 
    ./manage.py diffsettings | grep -E "DATABASES" | if [ "$nopwds" = 1 ]; then
      sed -E -e "s/('PASSWORD': *)'[^']+'/\\1'XXXXXX'/"
    else
      cat
    fi
    echo "SELECT 1" | ./manage.py dbshell
    ;;


  -H|--gunicorn-http-status)
    set -e
    port="$( ./manage.py fodinfo -P)"
    echo "gunicorn http port=$port" 
    set +e
    http_ret_code="$(curl -k --write-out "%{http_code}" --silent --output "/dev/null" "http://localhost:$port/altlogin/")"
    echo "gunicorn http_ret_code=$http_ret_code" 
    [ "$http_ret_code" = "200" ]
    ;;  

  -N|--netconf-access-status)
    nopwds=1
    if [ "$1" = "--with-passwords" ]; then
      nopwds=0
      shift 1
    fi

    set -e
    echo "# NETCONF access status:" 
    ./manage.py diffsettings | grep -E "(NETCONF)|(SNMP_IP)" | if [ "$nopwds" = 1 ]; then
    sed -E -e "s/(NETCONF_PASS\s*=\s*).*$/\1'XXXXXX'/" -e "s/('community': *)'[^']+'/\\1'XXXXXX'/" 
    else
        cat
    fi
    env DJANGO_SETTINGS_MODULE=flowspy.settings python -c '
from utils.proxy import *; 
proxy = Applier(); 
xml = proxy.get_existing_config_xml();
#print(xml);
print("access to NETCONF seems to be working");
' "$@" < /dev/null 
    ;;

  --sensu-status)
    "$0" --status
    statusx="$?"
    echo "status=$statusx"
    if [ "$statusx" = 0 ]; then
      echo "all basic checks passed: OK"
      exit 0
    else 
      echo "something went wrong during basic checks: ERROR"
      exit 2
    fi
  ;;


  -S|status-detailed)
    #set -e

    "$0" --process-status
    pstatus="$?"
    echo "process status=$pstatus"
    echo

    "$0" --database-access-status --with-passwords
    dstatus="$?"
    echo "database access status=$dstatus"
    echo

    "$0" --gunicorn-http-status
    hstatus="$?"
    echo "gunicorn http status=$hstatus"
    echo

    "$0" --netconf-access-status --with-passwords
    nstatus="$?"
    echo "NETCONF access status=$nstatus"
    echo

    all_status=$(( $pstatus | $dstatus | $hstatus | $nstatus ))
    echo "all_status=$all_status"

    exit "$all_status"
    ;;

  *|-s|--status)
    #set -e

    "$0" --process-status
    pstatus="$?"
    echo "process status=$pstatus"
    echo

    "$0" --database-access-status
    dstatus="$?"
    echo "database access status=$dstatus"
    echo

    "$0" --gunicorn-http-status
    hstatus="$?"
    echo "gunicorn http status=$hstatus"
    echo

    "$0" --netconf-access-status
    nstatus="$?"
    echo "NETCONF access status=$nstatus"
    echo

    all_status=$(( $pstatus | $dstatus | $hstatus | $nstatus ))
    echo "all_status=$all_status (0=OK)"

    exit "$all_status"

  ;;


esac

