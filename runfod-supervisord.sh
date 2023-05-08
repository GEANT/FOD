#!/bin/bash

export LC_ALL="C" # this will unfortunatelly break ./manage.py createsuperuser as locale string is literally used to derive encoding

##

#fod_dir="/srv/flowspy"
#venv_dir="/srv/venv"

fod_dir="$(dirname "$0")"
venv_dir="$fod_dir/venv"

echo "$0: ini fod_dir=$fod_dir venv_dir=$venv_dir" 1>&2

#

while [ $# -gt 0 ]; do

  if [ $# -ge 1 -a "$1" = "--here" ]; then
    shift 1
    fod_dir="$PWD"
    venv_dir="$PWD/venv"
  elif [ $# -ge 1 -a "$1" = "--base_dir" ]; then
    shift 1
    base_dir="$1"
    shift 1
    fod_dir="$base_dir/flowspy"
    venv_dir="$base_dir/venv"
  elif [ $# -ge 1 -a "$1" = "--fod_dir" ]; then
    shift 1
    fod_dir="$1"
    shift 1
  elif [ $# -ge 1 -a "$1" = "--venv_dir" ]; then
    shift 1
    venv_dir="$1"
    shift 1
  else
    break
  fi

done

##############################################################################
##############################################################################

if [ -e "$fod_dir/fodenv.sh" ]; then
  . "$fod_dir/fodenv.sh"
fi

#. /srv/venv/bin/activate
. "$venv_dir/bin/activate"

#if [ ! -e /srv/flowspy/pythonenv ]; then
if [ ! -e "$fod_dir/pythonenv" ]; then
  #cat > /srv/flowspy/pythonenv <<EOF
  cat > "$fod_dir/pythonenv" <<EOF
#!/bin/bash
. "$venv_dir/bin/activate"
[ ! -e "$fod_dir/fodenv.sh" ] || . "$fod_dir/fodenv.sh"
exec "\$@"
EOF
  #chmod +x /srv/flowspy/pythonenv
  chmod +x "$fod_dir/pythonenv"
fi

##

cd "$(dirname "$0")"

#if [ ! -x ./fodcli_db_is_mysql ] || ./fodcli_db_is_mysql; then
#  echo "Starting DB services FoD might be depending on (depending on its config): mysql" 1>&2
#  systemctl start mysql.service
#fi

# hook to initiallize (without any user interaction admin user and its peer data)
[ -x "$fod_dir/fodcli_insert_basic_data.sh" ] && "$fod_dir/fodcli_insert_basic_data.sh"

#echo "starting redis" 1>&2
#/usr/bin/redis-server &

#echo "Starting FoD celeryd in background" 1>&2
#celery worker -A flowspy -B --concurrency=2 --detach -l debug -f celery.log

#echo "Starting FoD gunicorn in foreground" 1>&2
#exec ./manage.py runserver 0.0.0.0:8000 
#exec ./manage.py runserver 0.0.0.0:8000 --nothreading
#exec gunicorn -w 1 --limit-request-fields 10000 --worker-class gevent --timeout 30
#exec gunicorn -b 0.0.0.0:8000 flowspy.wsgi -w 1 --limit-request-fields 10000 --timeout 30
#exec gunicorn -b 0.0.0.0:8000 flowspy.wsgi -w 1
#exec gunicorn -b 0.0.0.0:8000 flowspy.wsgi -w 1 -k gevent --limit-request-fields 10000 --timeout 30 #--preload
#exec gunicorn -b 0.0.0.0:8000 flowspy.wsgi -w 1 -k gevent --limit-request-fields 10000 --timeout 30 

##

if ! which supervisord; then 
  echo "supervisor not installed, trying to do this" 1>&2
  if [ -f /etc/debian_version ]; then
    apt-get install -qqy supervisor
  else
    yum install -y supervisor
  fi
fi

# TODO
if grep -q -E '^systemd$' /proc/1/comm; then
  systemctl disable supervisord
  systemctl disable supervisor
  systemctl disable redis
  systemctl disable redis-server
fi

#useradd -m fod
(
  #set -x
  #source /srv/venv/bin/activate
  source "$venv_dir/bin/activate"
  #cd /srv/flowspy && ./manage.py collectstatic --noinput
  cd "$fod_dir" && ./manage.py collectstatic --noinput
)

# needed for redis
sysctl vm.overcommit_memory=1

if [ ! -f /etc/supervisord.conf -o ! -e /etc/.supervisord.conf.fodready ]; then

  # supervisord.conf
  if [ -f supervisord.conf.prep ]; then
    echo "$0: using supervisord.conf.prep" 1>&2
    cp -f supervisord.conf.prep /etc/supervisord.conf
  else
    echo "$0: using supervisord.conf" 1>&2
    cp -f supervisord.conf /etc
  fi

fi

mkdir -p /var/run/fod /var/log/fod
chown -R fod /var/run/fod /var/log/fod
mkdir -p log/fod
mkdir -p logs 
#chown fod /srv/flowspy /srv/flowspy/log /srv/flowspy/logs /srv/flowspy/log/* /srv/flowspy/logs/* /srv/flowspy/debug.log /srv/flowspy/example-data
chown fod "$fod_dir" "$fod_dir/log" "$fod_dir/logs" "$fod_dir/log/"* "$fod_dir/logs/"* "$fod_dir/debug.log" "$fod_dir/example-data"

##

mkdir -p /var/run/supervisor
exec /usr/bin/supervisord -n -c /etc/supervisord.conf

##############################################################################
##############################################################################

