#!/bin/bash
#!/bin/sh
#
# This script installs all dependencies for Firewall-on-Demand running in Python3
# with Celery, Redis, and sqlite.
#

SCRIPT_NAME="install-debian.sh"

fod_dir="/srv/flowspy"
venv_dir="/srv/venv"

inside_docker=0

install_basesw=1
install_fodproper=1

install_systemd_services=0
ensure_installed_pythonenv_wrapper=1

install_mta=""

try_install_docu=1

#

install_db=""
init_db=""
conf_db_access=""
          
DB__FOD_DBNAME=""
DB__FOD_USER=""
DB__FOD_PASSWORD=""

##############################################################################
##############################################################################

function init_mysqllikedb() {
  DB__FOD_DBNAME="$1"
  shift 1
  DB__FOD_USER="$1"
  shift 1
  DB__FOD_PASSWORD="$1"
  shift 1

  set -e

  echo 1>&2
  echo "trying to init mysqllike database '$DB__FOD_DBNAME' for DB USER '$DB__FOD_USER'" 1>&2

  echo "CREATE DATABASE IF NOT EXISTS $DB__FOD_DBNAME;" | mysql
  echo "ALTER DATABASE $DB__FOD_DBNAME CHARACTER SET utf8;" | mysql
  echo "DROP USER IF EXISTS '$DB__FOD_USER'@'%';" | mysql
  #echo "CREATE USER IF NOT EXISTS '$DB__FOD_USER'@'%' IDENTIFIED BY '$DB__FOD_PASSWORD';" | mysql
  echo "CREATE USER '$DB__FOD_USER'@'%' IDENTIFIED BY '$DB__FOD_PASSWORD';" | mysql
  #echo "GRANT ALL PRIVILEGES ON *.* TO '$DB__FOD_USER'@'%';" | mysql
  #echo "GRANT ALL ON *.* to '$DB__FOD_USER'@'172.18.0.2' IDENTIFIED BY '$DB__FOD_PASSWORD' WITH GRANT OPTION;" | mysql
  echo "GRANT ALL PRIVILEGES ON *.* to '$DB__FOD_USER'@'%' WITH GRANT OPTION;" | mysql
  
  echo "current users:" 1>&2
  echo "SELECT User,Host FROM mysql.user;" | mysql
  echo 1>&2
  echo "current grants:" 1>&2
  echo "SHOW GRANTS FOR '$DB__FOD_USER'@'%';" | mysql
  
  mysqladmin flush-privileges

  echo "SELECT 1 " | mysql -u"$DB__FOD_USER" -p"$DB__FOD_PASSWORD" 
  
  echo "done with initalizing mysqllike database '$DB__FOD_DBNAME' for DB USER '$DB__FOD_USER'" 1>&2
  echo 1>&2

}

function get_random_password() {
  dd status=noxfer bs=1 count=16 < /dev/random 2> /dev/null | hexdump | grep "0000000" | awk '{ OFS=""; $1=""; print; }'
}

function conf_db_access () {
  fod_dir="$1"
  shift 1
  conf_db_access="$1"
  shift 1
  DB__FOD_DBNAME="$1"
  shift 1
  DB__FOD_USER="$1"
  shift 1
  DB__FOD_PASSWORD="$1"
  shift 1

  (set -e
   sed -i "s/^\s*'ENGINE':.*#\s*DB_ENGINE/        'ENGINE': 'django.db.backends.$conf_db_access',  # DB_ENGINE # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'./" "$fod_dir/flowspy/settings.py"
   sed -i "s/^\s*'NAME':.*#\s*DB_NAME/        'NAME': '$DB__FOD_DBNAME',  # DB_NAME/" "$fod_dir/flowspy/settings.py"
   sed -i "s/^\s*'USER':.*#\s*DB_USER/        'USER': '$DB__FOD_USER',  # DB_USER/" "$fod_dir/flowspy/settings.py"
   sed -i "s/^\s*'PASSWORD':.*#\s*DB_PASSWORD/        'PASSWORD': '$DB__FOD_PASSWORD',  # DB_PASSWORD/" "$fod_dir/flowspy/settings.py"
  )

}

function debug_python_deps()
{
  venv_file="$1"
  exit_code="$2"

  echo "debug_python_deps(): venv_file=$venv_file exit_code=$exit_code" 1>&2

  [ -z "$venv_file" ] || . "$venv_file"

  echo 1>&2
  echo "# Python version: " 1>&2  
  python --version

  echo 1>&2
  echo "# Python dependencies: " 1>&2  
  pip list
  echo "# End of Python dependencies" 1>&2  

  [ -z "$exit_code" ] || exit "$exit_code"
}

##
##############################################################################
##############################################################################

if [ -e "/.dockerenv" ]; then 
  echo "running inside docker assummed" 1>&2
  inside_docker=1
fi

if grep -q -E '^systemd$' /proc/1/comm; then 
  echo "system is running systemd as init process, setting default install_systemd_services=1" 1>&2
  install_systemd_services=1
elif [ "$inside_docker" = 1 ]; then 
  echo "inside_docker=$inside_docker, so setting default install_systemd_services=0" 1>&2
  install_systemd_services=0
fi

##############################################################################
##############################################################################

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
  elif [ $# -ge 1 -a "$1" = "--both" ]; then
    shift 1
    install_basesw=1
    install_fodproper=1
  elif [ $# -ge 1 -a "$1" = "--basesw" ]; then 
    shift 1
    install_basesw=1
    install_fodproper=0
  elif [ $# -ge 1 -a "$1" = "--fodproper" ]; then
    shift 1
    install_basesw=0
    install_fodproper=1
  elif [ $# -ge 1 -a "$1" = "--systemd" ]; then
    shift 1
    install_systemd_services=1
  elif [ $# -ge 1 -a "$1" = "--no_systemd" ]; then
    shift 1
    install_systemd_services=0
  elif [ $# -ge 1 -a "$1" = "--with_mta_postfix" ]; then
    shift 1
    install_mta="postfix"
  elif [ $# -ge 1 -a "$1" = "--with_db_sqlite" ]; then
    shift 1
    install_db="sqlite3"
    init_db="sqlite3"
    conf_db_access="sqlite3"
    DB__FOD_DBNAME="example-data"
    DB__FOD_USER=""
    DB__FOD_PASSWORD=""
  elif [ $# -ge 1 -a "$1" = "--with_db_mysql" ]; then
    shift 1
    install_db="mysql"
    init_db="mysql"
    conf_db_access="mysql"
    DB__FOD_DBNAME="fod"
    DB__FOD_USER="fod"
    DB__FOD_PASSWORD="$(get_random_password)"
  elif [ $# -ge 1 -a "$1" = "--with_db_mariadb" ]; then
    shift 1
    install_db="mariadb"
    init_db="mariadb"
    conf_db_access="mysql"
    DB__FOD_DBNAME="fod"
    DB__FOD_USER="fod"
    DB__FOD_PASSWORD="$(get_random_password)"
  elif [ $# -ge 1 -a "$1" = "--use_db_mysqllike" ]; then
    shift 1
    install_db=""
    init_db="mysql"
    conf_db_access="mysql"
    DB__FOD_DBNAME="fod"
    DB__FOD_USER="fod"
    DB__FOD_PASSWORD="$(get_random_password)"
  else
    break
  fi

done

if [ $# -gt 0 ]; then
  echo "remaining unprocessed arguments: $*, aborting" 1>&2
  exit 2
fi

##

echo "conf_db_access=$conf_db_access DB_NAME=$DB__FOD_DBNAME DB_USER=$DB__FOD_USER DB_PASSWORD=$DB__FOD_PASSWORD" 1>&2

##
  
venv_dir_base="$(dirname "$venv_dir")"

static_dir="$fod_dir/static"

inst_dir="$(dirname "$0")"

mkdir -p "$fod_dir" || exit

if [ "$(stat -Lc "%i" "$inst_dir/" "$fod_dir/" | sort -n -k 1 -u | wc -l)" = "1" ]; then
  inst_dir_is_fod_dir=1
else
  inst_dir_is_fod_dir=0
fi

echo "$0: inst_dir=$inst_dir fod_dir=$fod_dir => inst_dir_is_fod_dir=$inst_dir_is_fod_dir venv_dir=$venv_dir static_dir=$static_dir" 1>&2
#exit

#############################################################################
#############################################################################

if [ "$install_basesw" = 1 ]; then

  echo "$0: step 1: installing base software dependencies (OS packages)" 1>&2

  if [ "$install_db" = "" ]; then
    mysql_server_pkg=("")
  elif [ "$install_db" = "mysql" ]; then
    mysql_server_pkg=("mysql-server")
  else
    mysql_server_pkg=("mariadb-server")
  fi

  set -e

  echo 1>&2
  echo "Install dependencies" 1>&2
  apt-get -qqy update
  apt-get -qqy install virtualenv python3-venv python3-setuptools \
    python3-dev vim git build-essential libevent-dev libxml2-dev libxslt1-dev \
    "${mysql_server_pkg[@]}" libmariadb-dev patch redis-server sqlite3 \
    rustc libssl-dev \
    procps 
  echo 1>&2

  set +e

fi

##

if [ -n "$install_mta" ]; then

  set -e

  echo 1>&2
  if [ -x "/usr/sbin/sendmail" ]; then
    echo "MTA /usr/sbin/sendmail seems to be already available, not trying to install another one" 1>&2
  elif [ "$install_mta" = "postfix" ]; then
    echo "trying to install postfix MTA" 1>&2
    apt-get -qqy update
    apt-get -qqy install postfix
  fi
  echo 1>&2

  set +e

fi

##

if [ -n "$install_db" ]; then

  set -e

  echo 1>&2
  if [ "$install_db" = "mariadb" ]; then
    echo "trying to install mariadb" 1>&2
    apt-get -qqy update
    apt-get -y install mariadb-server

  elif [ "$install_db" = "mysql" ]; then
    echo "trying to install mysql" 1>&2
    apt-get -qqy update
    apt-get -y install mysql-server 

  elif [ "$install_db" = "sqlite3" ]; then
    : 
  else
    echo "unknown db '$install_db'" 1>&2
  fi
  echo 1>&2

  set +e

  echo "$0: step 1 done" 1>&2

fi

##

echo "$0: step 1a: handling sqlite3 too old fixup post actions" 1>&2 # only needed for CENTOS

echo "$0: step 1b: preparing database system" 1>&2

if [ -n "$init_db" ]; then

  set -e

  echo 1>&2
  if [ "$init_db" = "mysql" -o "$init_db" = "mariadb" ]; then

    echo "trying to init mysql" 1>&2
    init_mysqllikedb "$DB__FOD_DBNAME" "$DB__FOD_USER" "$DB__FOD_PASSWORD"

  elif [ "$init_db" = "sqlite3" ]; then
    : 
  else
    echo "unknown db '$init_db'" 1>&2
  fi
  echo 1>&2

  set +e

fi

##

python_version="$(python3 --version | cut -d ' ' -f 2,2)"
#if [ "$assume__sqlite_version__to_old" = 1 ]; then
#  echo "$0: assume__sqlite_version__to_old=$assume__sqlite_version__to_old => using requirements-centos.txt" 1>&2
#  cp "$fod_dir/requirements-centos.txt" "$fod_dir/requirements.txt"
if [ -e "$fod_dir/requirements.txt.python$python_version" ]; then
  echo "$0: using python version specific $fod_dir/requirements.txt.python$python_version" 1>&2
  cp "$fod_dir/requirements.txt.python$python_version" "$fod_dir/requirements.txt"
else
  echo "$0: using $fod_dir/requirements.txt" 1>&2
fi

#############################################################################
#############################################################################

if [ "$install_fodproper" = 0 ]; then
  
  echo "$0: step 2a: installing Python dependencies only" 1>&2

  set -e

  echo "Setup partial python environment for FoD"

  #mkdir -p /srv
  mkdir -p "$venv_dir_base"
  if [ -x pyvenv ]; then
    #pyvenv /srv/venv
    pyvenv "$venv_dir"
  else
    #virtualenv /srv/venv
    virtualenv --python=python3 "$venv_dir"
  fi
  ln -sf "$venv_dir" "$fod_dir/venv"

  #source /srv/venv/bin/activate
  source "$venv_dir/bin/activate"

  ##

  # fix for broken anyjson and cl
  # TODO: fix this more cleanly
  pip install 'setuptools==57.5.0'
  pip install wheel

  pip install -r requirements.txt

  echo "$0: step 2a done" 1>&2

else

  echo "$0: step 2: installing FoD in installation dir + ensuring Python dependencies are installed + setting-up FoD settings, database preparations, and FoD run-time environment" 1>&2

  set -e
  
  echo "$0: step 2.0" 1>&2
  
  id fod &>/dev/null || useradd -m fod  


  #mkdir -p /var/log/fod /srv
  mkdir -p /var/log/fod "$venv_dir_base"

  ##

  echo "Setup python environment for FoD"

  if [ -x pyvenv ]; then
    #pyvenv /srv/venv
    pyvenv "$venv_dir"
  else
    #virtualenv /srv/venv
    virtualenv --python=python3 "$venv_dir"
  fi
  ln -sf "$venv_dir" "$fod_dir/venv"

  (
  set +e
  #source /srv/venv/bin/activate
  source "$venv_dir/bin/activate"

  ##

  #mkdir -p /srv/flowspy/
  mkdir -p "$fod_dir"

  if [ "$inst_dir_is_fod_dir" = 0 ]; then
  
    echo "$0: step 2.1: coyping from source dir to installation dir $fod_dir" 1>&2

    MYSELF="$(basename "$0")"

    # Select source dir and copy FoD into /srv/flowspy/
    if [ "$MYSELF" = "$SCRIPT_NAME" ]; then # if started as main script, e.g., in Docker or on OS-installation
      # this script is in the source directory
      #cp -f -r "`dirname $0`"/* /srv/flowspy/
      cp -f -r "$inst_dir"/* "$fod_dir"
    elif [ -e /vagrant ]; then # running in vagrant with /vagrant available
      # vagrant's copy in /vagrant/
      #cp -f -r /vagrant/* /srv/flowspy/
      cp -f -r /vagrant/* "$fod_dir"
    elif [ -e "$SCRIPT_NAME" ]; then # running in vagrant with script current dir == install dir
      # current directory is with the sourcecode
      #cp -f -r ./* /srv/flowspy/
      cp -f -r ./* "$fod_dir"
    else
      echo "Could not find FoD src directory tried `dirname $0`, /vagrant/, ./"
      exit 1
    fi

  fi

   #find "$fod_dir/" -not -user fod -exec chown -v fod: {} \;
   find "$fod_dir/" -not -user fod -exec chown fod: {} \;

 ###

  set -e
  
  echo "$0: step 2.2: setting-up FoD settings" 1>&2

  #cd /srv/flowspy/
  cd "$fod_dir"
  (
    cd flowspy # jump into settings subdir flowspy

    if [ "$inside_docker" = 1 -a -e settings.py.docker.debian ]; then # user has own settings prepared yet ?

      cp -f settings.py.docker.debian settings.py

    elif [ -e settings.py.debian ]; then # user has own settings prepared yet ?

      cp -f settings.py.debian settings.py

    elif [ "$inside_docker" = 1 -a -e settings.py.docker ]; then # user has own settings prepared yet ?

      cp -f settings.py.docker settings.py

    elif [ -e settings.py ]; then # user has prepared a generic settings yet ?

      : # nothing todo

    else # prepare from settings.py.dist + settings.py.patch

      cp -f settings.py.dist settings.py
      patch settings.py < settings.py.patch
      sed -i "s#/srv/flowspy#$fod_dir#" "settings.py"

    fi
  )

  if [ ! -e "flowspy/settings_local.py" ]; then
    touch flowspy/settings_local.py
  fi
  
  echo "$0: step 2.3: ensuring Python dependencies are installed" 1>&2

  if [ "$install_basesw" = 1 ]; then #are we running in --both mode, i.e. for the venv init is run for the first time, i.e. the problematic package having issues with to new setuptools is not yet installed?
    # fix for broken anyjson and cl
    # TODO: fix this more cleanly
    pip install 'setuptools==57.5.0'
  fi

  # actual proper installation of python requirements
  pip install -r requirements.txt

  ##

  echo "$0: step 2.3.1: preparing log sub dirs" 1>&2

  mkdir -p "$fod_dir/log" "$fod_dir/logs"
  touch "$fod_dir/debug.log"
  chown -R fod: "$fod_dir/log" "$fod_dir/logs" "$fod_dir/debug.log"

  if [ "$try_install_docu" = 1 ]; then
    echo "$0: step 2.3.2: compiling internal docu" 1>&2
    echo "trying to install mkdocs-based documentation" 1>&2
    (
      set -e
      which mkdocs 2>/dev/null >/dev/null || apt-get install -y mkdocs
      cd "$fod_dir" && mkdocs build
      true # in case of failure override failure status, as the documentation is non-essential
    )
  fi

  ##

  echo "$0: step 2.4: preparing FoD static files and database" 1>&2

  echo "$0: step 2.4.1: preparing FoD static files" 1>&2

  #mkdir -p /srv/flowspy/static/
  mkdir -p "$static_dir"

  (
    set -e

    [ ! -f "fodenv.sh" ] || source "./fodenv.sh"; 
    
    source "$venv_dir/bin/activate"

    cd "$fod_dir"

    ./manage.py collectstatic -c --noinput || debug_python_deps "$venv_dir/bin/activate" 1
  )

  ##

  echo "$0: step 2.4.2.0: preparing DB and DB access" 1>&2

        #if [ "$init_db" = "mariadb" -o "$init_db" = "mysql" ]; then
        #  init_mysqllikedb "$DB__FOD_DBNAME" "$DB__FOD_USER" "$DB__FOD_PASSWORD"
        #fi

        if [ -n "$conf_db_access" ]; then
          echo "setting DB access config" 1>&2
          conf_db_access "$fod_dir" "$conf_db_access" "$DB__FOD_DBNAME" "$DB__FOD_USER" "$DB__FOD_PASSWORD"
          echo 1>&2
        fi

  ##    

  echo "$0: step 2.4.2.0: preparing FoD DB schema and basic data" 1>&2

  echo "deploying/updating database schema" 1>&2
  (
    set -e

    [ ! -f "fodenv.sh" ] || source "./fodenv.sh"

    source "$venv_dir/bin/activate"

    cd "$fod_dir"

    #./manage.py syncdb --noinput

    ./manage.py migrate
    ./manage.py loaddata initial_data
  )
  echo 1>&2

  ##

  # ./manage.py above may have created debug.log with root permissions:
  chown -R fod: "$fod_dir/log" "$fod_dir/logs" "$fod_dir/debug.log" 
  [ ! -d "/var/log/fod" ] || chown -R fod: "/var/log/fod"

  #
  echo "$0: step 2.5: preparing FoD run-time environment" 1>&2

  echo "$0: step 2.5.1: preparing necessary dirs" 1>&2

  mkdir -p /var/run/fod
  chown fod: /var/run/fod 

  ##

  echo "$0: step 2.5.2: preparing FoD python wrapper" 1>&2

  if [ "$ensure_installed_pythonenv_wrapper" = 1 -a \( "$inside_docker" = 1 -o ! -e "$fod_dir/pythonenv" \) ]; then
    echo "adding pythonev wrapper" 1>&2
    cat > "$fod_dir/pythonenv" <<EOF
#!/bin/bash
. "$venv_dir/bin/activate"
[ ! -e "$fod_dir/fodenv.sh" ] || . "$fod_dir/fodenv.sh"
exec "\$@"
EOF
    chmod +x "$fod_dir/pythonenv"
    echo 1>&2
  fi

  ##

  echo "$0: step 2.5.3: preparing supervisord.conf" 1>&2

  cp -f "$fod_dir/supervisord.conf.dist" "$fod_dir/supervisord.conf"
  sed -i "s#/srv/flowspy#$fod_dir#" "$fod_dir/supervisord.conf"
  echo 1>&2

  ##

  
  echo "$0: step 2.5.5: preparing systemd files" 1>&2

  fod_systemd_dir="$fod_dir/systemd"
  cp -f "$fod_systemd_dir/fod-gunicorn.service.dist" "$fod_systemd_dir/fod-gunicorn.service"
  sed -i "s#/srv/flowspy#$fod_dir#g" "$fod_systemd_dir/fod-gunicorn.service"

  cp -f "$fod_systemd_dir/fod-celeryd.service.dist" "$fod_systemd_dir/fod-celeryd.service"
  sed -i "s#/srv/flowspy#$fod_dir#g" "$fod_systemd_dir/fod-celeryd.service"

  cp -f "$fod_systemd_dir/fod-status-email-user@.service.dist" "$fod_systemd_dir/fod-status-email-user@.service"
  sed -i "s#/srv/flowspy#$fod_dir#g" "$fod_systemd_dir/fod-status-email-user@.service"

  if [ "$install_systemd_services" = 1 ]; then
    echo 1>&2
    echo "Installing systemd services" 1>&2
    echo 1>&2
    #cp -f "$fod_systemd_dir/fod-gunicorn.service" "$fod_systemd_dir/fod-celeryd.service" "/etc/systemd/system/"
    cp -v -f "$fod_systemd_dir/fod-gunicorn.service" "$fod_systemd_dir/fod-celeryd.service" "$fod_systemd_dir/fod-status-email-user@.service" "/etc/systemd/system/" 1>&2
    systemctl daemon-reload

    systemctl enable fod-gunicorn
    systemctl enable fod-celeryd

    systemctl restart fod-gunicorn
    systemctl restart fod-celeryd

    sleep 5
    SYSTEMD_COLORS=1 systemctl status fod-gunicorn | cat
    echo
    SYSTEMD_COLORS=1 systemctl status fod-celeryd | cat
    echo

  fi

  )
  
  echo "$0: step 2 done" 1>&2

  set +e

fi

#############################################################################
#############################################################################

