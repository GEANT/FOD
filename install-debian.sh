#!/bin/bash
#!/bin/sh
#
# This script installs all dependencies for Firewall-on-Demand running in Python3
# with Celery, Redis, and sqlite.
#

SCRIPT_NAME="install-debian.sh"

#############################################################################
#############################################################################

# allow for easy clean-slate installation
if [ "$1" = "--git-checkout" ]; then 
  shift 1
  gitrepo="$1" 
  shift 1
  git_branch="$1"
  shift 1
  git_checkout_dir="$1"
  shift 1

  [ -n "$gitrepo" ] || gitrepo="https://github.com/GEANT/FOD"

  [ -n "$git_branch" ] || git_branch="python3"

  echo "$0: git-checkout: gitrepo=$gitrepo git_branch="$git_branch" git_checkout_dir=$git_checkout_dir" 1>&2

  ##

  set -e
  set -x

  git_checkout_dir_parentdir="$(dirname "$git_checkout_dir")"
  mkdir -p "$git_checkout_dir_parentdir"

  git clone "$gitrepo" "$git_checkout_dir"

  cd "$git_checkout_dir"

  git checkout "refs/remotes/origin/$git_branch"
  git checkout -b "$git_branch"

  exec "./$SCRIPT_NAME" "$@" 

fi

#############################################################################
#############################################################################

fod_dir="/srv/flowspy"
venv_dir="/srv/venv"

FOD_SYSUSER="fod"

inside_docker=0

install_default_used=1
#install_basesw_os=1
install_basesw_os=0
#install_basesw_python=1
install_basesw_python=0
#install_basesw_python=1
install_fodproper=0

install_with_supervisord=0
install_systemd_services=0
install_systemd_services__onlyinstall=0
ensure_installed_pythonenv_wrapper=1

try_install_docu=1

install_mta=""

#

use__database_schema_migrate__fake_initial=0

#

install_db=""
init_db=""
conf_db_access=""
          
DB__FOD_DBNAME=""
DB__FOD_USER=""
DB__FOD_PASSWORD=""

#

setup_adminuser=0
setup_adminuser__username="admin"
setup_adminuser__pwd="admin"
#setup_adminuser__email="admin@localhost"
setup_adminuser__peer_name="testpeer"
setup_adminuser__peer_ip_prefix1="0.0.0.0/0"

#

setup_netconf=0

setup_netconf__device=
setup_netconf__port=830
setup_netconf__user="netconf"
setup_netconf__pass="netconf"

#

setup_exabgp=0
setup_exabgp_full=0

setup_exabgp__nodeid=1.1.1.1
setup_exabgp__ip_addr=127.0.0.1
setup_exabgp__asnr=1234
setup_exabgp__peer_nodeid=2.2.2.2
setup_exabgp__peer_ip_addr=127.0.0.2
setup_exabgp__peer_asnr=2345

#

ifc_setup__name=""
ifc_setup__ip_addr_and_subnetmask=""
ifc_setup__wait_for_ifc__in_runfod=0

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

  ls -l log/ 1>&2

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
  install_systemd_services__onlyinstall=0
elif [ "$inside_docker" = 1 ]; then 
  echo "inside_docker=$inside_docker, so setting default install_systemd_services=0" 1>&2
  install_systemd_services=0
  install_systemd_services__onlyinstall=1
  #install_with_supervisord=1
fi

##############################################################################
##############################################################################

while [ $# -gt 0 ]; do

  if [ $# -ge 1 -a "$1" = "--here" ]; then
    shift 1
    fod_dir="$PWD"
    venv_dir="$PWD/venv"
  elif [ $# -ge 1 -a "$1" = "--here__with_venv_relative" ]; then
    shift 1
    fod_dir="$PWD"
    venv_dir="$PWD/../venv"
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
    install_default_used=0

    install_basesw_os=1
    install_basesw_python=1
    install_fodproper=1
  elif [ $# -ge 1 -a "$1" = "--basesw" ]; then 
    shift 1
    install_default_used=0

    install_basesw_os=1
    install_basesw_python=1
    #install_fodproper=0
  elif [ $# -ge 1 -a "$1" = "--basesw_os" ]; then 
    shift 1
    install_default_used=0

    install_basesw_os=1
    #install_basesw_python=0
    #install_fodproper=0
  elif [ $# -ge 1 -a "$1" = "--basesw_python" ]; then 
    shift 1
    install_default_used=0

    #install_basesw_os=0
    install_basesw_python=1
    #install_fodproper=0
  elif [ $# -ge 1 -a "$1" = "--fodproper" ]; then
    shift 1
    install_default_used=0

    #install_basesw_os=0
    install_basesw_python=1
    install_fodproper=1
  elif [ $# -ge 1 -a "$1" = "--fodproper1" ]; then
    shift 1
    install_default_used=0

    #install_basesw_os=0
    #install_basesw_python=0
    install_fodproper=1
  elif [ $# -ge 1 -a \( "$1" = "--supervisor" -o "$1" = "--supervisord" \) ]; then
    shift 1
    install_with_supervisord=1
    install_systemd_services=0
  elif [ $# -ge 1 -a \( "$1" = "--no_supervisor" -o "$1" = "--no_supervisord" \) ]; then
    shift 1
    install_with_supervisord=0
  elif [ $# -ge 1 -a "$1" = "--systemd" ]; then
    shift 1
    install_systemd_services=1
  elif [ $# -ge 1 -a "$1" = "--systemd_only_install" ]; then
    shift 1
    install_systemd_services__onlyinstall=1
  elif [ $# -ge 1 -a "$1" = "--systemd_check_start" ]; then
    shift 1
    install_systemd_services__onlyinstall=0
  elif [ $# -ge 1 -a "$1" = "--no_systemd" ]; then
    shift 1
    install_systemd_services=0
  elif [ $# -ge 1 -a "$1" = "--db_schema_migrate__fake_initial" ]; then 
    shift 1
    db_schema_migrate__fake_initial=1    
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
  elif [ $# -ge 1 -a "$1" = "--setup_admin_user" ]; then
    shift 1
     setup_adminuser=1
  elif [ $# -ge 1 -a "$1" = "--setup_admin_user5" ]; then
    shift 1
    setup_adminuser=1
    setup_adminuser__username="$1"
    shift 1 
    setup_adminuser__pwd="$1"
    shift 1 
    setup_adminuser__email="$1"
    shift 1 
    setup_adminuser__peer_name="$1"
    shift 1 
    setup_adminuser__peer_ip_prefix1="$1"
    shift 1 
  elif [ $# -ge 1 -a "$1" = "--netconf" ]; then 
    shift 1
    setup_netconf=1
    setup_netconf__device="$1" 
    shift 1
    setup_netconf__port="$1"
    shift 1
    setup_netconf__user="$1"
    shift 1
    setup_netconf__pass="$1"
    shift 1
  elif [ $# -ge 1 -a "$1" = "--exabgp0" ]; then 
    shift 1
    setup_exabgp=1
    shift 1
    setup_exabgp_full=0
  elif [ $# -ge 1 -a "$1" = "--exabgp" ]; then # currently 6 params follow
    shift 1
    setup_exabgp=1
    setup_exabgp_full=1

    setup_exabgp__nodeid="$1"
    shift 1
    setup_exabgp__ip_addr="$1"
    shift 1
    setup_exabgp__asnr="$1"
    shift 1
    setup_exabgp__peer_nodeid="$1"
    shift 1
    setup_exabgp__peer_ip_addr="$1"
    shift 1
    setup_exabgp__peer_asnr="$1"
    shift 1
  elif [ $# -ge 1 -a "$1" = "--ip-addr-set" ]; then # for easy support for of extra veth-pair end point init in containers for containerlab 
    shift 1
    ifc_setup__name="$1"
    shift 1
    ifc_setup__ip_addr_and_subnetmask="$1"
    shift 1
    ifc_setup__wait_for_ifc__in_runfod="$1"
    shift 1
    echo "$0: init of interface $ifc_setup__name with ip_addr_and_subnetmask=$ifc_setup__ip_addr_and_subnetmask" 1>&2
    ifconfig "$ifc_setup__name" "$ifc_setup__ip_addr_and_subnetmask" 
    ifconfig "$ifc_setup__name" 1>&2
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

if [ "$install_default_used" = 1 ]; then
  install_basesw_os=1
  install_basesw_python=1
  install_fodproper=1
fi

echo "$0: install_default_used=$install_default_used ; install_basesw_os=$install_basesw_os install_basesw_python=$install_basesw_python install_fodproper=$install_fodproper" 1>&2

[ -n "$setup_adminuser__email" ] || setup_adminuser__email="$setup_adminuser__username@localhost"

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

if [ "$install_basesw_os" = 1 ]; then

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

if [ "$try_install_docu" = 1 ]; then
    echo "trying to install mkdocs for documentation" 1>&2
    apt-get -qqy install mkdocs
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

if [ "$install_systemd_services" = 0 -a "$install_with_supervisord" = 1 ]; then
  echo "trying to install supervisord" 1>&2
  apt-get -qqy update
  apt-get -y install supervisor
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

if [ "$install_fodproper" = 0 -a "$install_basesw_python" = 1 ]; then
  
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

elif [ "$install_fodproper" = 1 ]; then

  echo "$0: step 2: installing FoD in installation dir + ensuring Python dependencies are installed + setting-up FoD settings, database preparations, and FoD run-time environment" 1>&2

  set -e
  
  echo "$0: step 2.0" 1>&2
  
  id "$FOD_SYSUSER" &>/dev/null || useradd -m "$FOD_SYSUSER"

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

  echo "$0: step 2.1a: fixing permissions" 1>&2
  #find "$fod_dir/" -not -user fod -exec chown -v fod: {} \;
  find "$fod_dir/" -not -user "$FOD_SYSUSER" -exec chown "$FOD_SYSUSER:" {} \;

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
  
  if [ "$install_basesw_python" = 1 ]; then
    echo "$0: step 2.3: ensuring Python dependencies are installed" 1>&2

    if [ "$install_basesw_python" = 1 ]; then #are we running in --both mode, i.e. for the venv init is run for the first time, i.e. the problematic package having issues with to new setuptools is not yet installed?
      # fix for broken anyjson and cl
      # TODO: fix this more cleanly
      pip install 'setuptools==57.5.0'
    fi

    # actual proper installation of python requirements
    pip install -r requirements.txt
  fi

  ##

  echo "$0: step 2.3.1: preparing log sub dirs" 1>&2

  mkdir -p "$fod_dir/log" "$fod_dir/logs"
  touch "$fod_dir/debug.log"
  chown -R "$FOD_SYSUSER:" "$fod_dir/log" "$fod_dir/logs" "$fod_dir/debug.log"
  
  ##

  if [ "$try_install_docu" = 1 ]; then
    echo "$0: step 2.3.2: compiling internal docu" 1>&2
    echo "trying to install mkdocs-based documentation" 1>&2
    (
      set -e
      which mkdocs 2>/dev/null >/dev/null || apt-get install -y mkdocs
      cd "$fod_dir" && mkdocs build # ./mkdocs.yml
      find "$fod_dir/static/site" -not -user "$FOD_SYSUSER" -exec chown "$FOD_SYSUSER:" {} \; # is depending on ./mkdocs.yml var site_dir
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

    [ ! -f "fodenv.sh" ] || source "./fodenv.sh" 
    
    source "$venv_dir/bin/activate"

    cd "$fod_dir"

    ./manage.py collectstatic -c --noinput || debug_python_deps "$venv_dir/bin/activate" 1
    find "$fod_dir/staticfiles" -not -user "$FOD_SYSUSER" -exec chown "$FOD_SYSUSER:" {} \; || true # TODO is depending on flowspy/settings*.py var STATIC_ROOT 
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

    add1=()
    if [ "$db_schema_migrate__fake_initial" = 1 ]; then
      echo "using --fake-initial" 1>&2
      add1=("--fake-initial")
    fi
    ./manage.py migrate "${add1[@]}"

    ./manage.py loaddata initial_data
  )
  echo 1>&2

  ##

  if [ "$setup_adminuser" = 1 ]; then
    echo "$0: step 2.4.2.1: setup admin start user" 1>&2

    # ./inst/helpers/init_setup_params.sh
   
    (
      set +e # for now ignore potential errors, especially in case user already exists
      source ./venv/bin/activate
      echo "from flowspec.init_setup import init_admin_user; init_admin_user('$setup_adminuser__username', '$setup_adminuser__pwd', '$setup_adminuser__email', '$setup_adminuser__peer_name', '$setup_adminuser__peer_ip_prefix1')" | DJANGO_SETTINGS_MODULE="flowspy.settings" ./manage.py shell
      true
    )
 
  fi

  ##

  # ./manage.py above may have created debug.log with root permissions:
  chown -R "$FOD_SYSUSER:" "$fod_dir/log" "$fod_dir/logs" "$fod_dir/debug.log" 
  [ ! -d "/var/log/fod" ] || chown -R "$FOD_SYSUSER:" "/var/log/fod"

  #
  echo "$0: step 2.5: preparing FoD run-time environment" 1>&2

  echo "$0: step 2.5.1: preparing necessary dirs" 1>&2

  mkdir -p /var/run/fod
  chown "$FOD_SYSUSER:" /var/run/fod 

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
  
  if [ "$setup_netconf" = 1 ]; then
    echo "$0: setting up NETCONF fod conf" 1>&2
    
    (
      echo -e '\n#added by install-*.sh:' 
      echo "PROXY_CLASS=\"proxy_netconf_junos\"" 
      echo "NETCONF_DEVICE=\"$setup_netconf__device\""
      echo "NETCONF_PORT=\"$setup_netconf__port\""
      echo "NETCONF_USER=\"$setup_netconf__user\""
      echo "NETCONF_PASS=\"$setup_netconf__pass\""
    ) >> flowspy/settings_local.py

  fi

  ##
  
  if [ "$setup_exabgp" = 1 ]; then
    echo "$0: setting up exabgp fod conf" 1>&2

    echo -e '\n#added by install-*.sh:\nPROXY_CLASS="proxy_exabgp"' >> flowspy/settings_local.py
  fi

  ##
 
  echo "$0: step 2.5.5: preparing systemd/supervisord files" 1>&2

  echo "$0: step 2.5.5.1: preparing supervisord.conf templates" 1>&2

  cp -f "$fod_dir/supervisord.conf.dist" "$fod_dir/supervisord.conf"
  sed -i "s#/srv/flowspy#$fod_dir#" "$fod_dir/supervisord.conf"
  echo 1>&2

  ##

  echo "$0: step 2.5.5.2: installing systemd/supervisord files" 1>&2

  fod_systemd_dir="$fod_dir/systemd"
  cp -f "$fod_systemd_dir/fod-gunicorn.service.dist" "$fod_systemd_dir/fod-gunicorn.service"
  sed -i "s#/srv/flowspy#$fod_dir#g" "$fod_systemd_dir/fod-gunicorn.service"

  cp -f "$fod_systemd_dir/fod-celeryd.service.dist" "$fod_systemd_dir/fod-celeryd.service"
  sed -i "s#/srv/flowspy#$fod_dir#g" "$fod_systemd_dir/fod-celeryd.service"

  cp -f "$fod_systemd_dir/fod-status-email-user@.service.dist" "$fod_systemd_dir/fod-status-email-user@.service"
  sed -i "s#/srv/flowspy#$fod_dir#g" "$fod_systemd_dir/fod-status-email-user@.service"

  if [ "$install_systemd_services" = 1 ]; then
    echo 1>&2
    echo "$0: installing systemd services" 1>&2
    echo 1>&2
    #cp -f "$fod_systemd_dir/fod-gunicorn.service" "$fod_systemd_dir/fod-celeryd.service" "/etc/systemd/system/"
    cp -v -f "$fod_systemd_dir/fod-gunicorn.service" "$fod_systemd_dir/fod-celeryd.service" "$fod_systemd_dir/fod-status-email-user@.service" "/etc/systemd/system/" 1>&2


    if [ "$install_systemd_services__onlyinstall" = 1 ]; then
      #systemctl enable --machine --no-reload fod-gunicorn
      #systemctl enable --machine --no-reload fod-celeryd
      ln -s -f -v "/usr/lib/systemd/system/fod-gunicorn.service" /etc/systemd/system/multi-user.target.wants/
      ln -s -f -v "/usr/lib/systemd/system/fod-celeryd.service" /etc/systemd/system/multi-user.target.wants/
    else
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
  
    FOD_RUNMODE="via_systemd" 
  
  elif [ "$install_with_supervisord" = 1 ]; then
    echo 1>&2
    echo "$0: installing supervisord conf" 1>&2
    echo 1>&2

    # supervisord.conf
    if [ -f supervisord.conf.prep ]; then
      echo "$0: using supervisord.conf.prep" 1>&2
      cp -f supervisord.conf.prep /etc/supervisord.conf
    else
      echo "$0: using supervisord.conf" 1>&2
      cp -f supervisord.conf /etc/supervisord.conf
    fi
    touch /etc/.supervisord.conf.fodready
  
    FOD_RUNMODE="via_supervisord" 

  else

    FOD_RUNMODE="fg" 

  fi

  ##

  echo "$0: step 2.5.6: writing ./runfod.conf" 1>&2
  (
    echo "FOD_RUNMODE=\"$FOD_RUNMODE\"" 
    echo "USE_EXABGP=\"$setup_exabgp\""
    if [ -n "$ifc_setup__name" ]; then
      echo "ifc_setup__name=\"$ifc_setup__name\""
      echo "ifc_setup__ip_addr_and_subnetmask=\"$ifc_setup__ip_addr_and_subnetmask\""
      echo "ifc_setup__wait_for_ifc__in_runfod=\"$ifc_setup__wait_for_ifc__in_runfod\""
    fi
  ) > "./runfod.conf"

  ##

  if [ "$setup_exabgp" = 1 ]; then
    
    echo "$0: step 2.5.7: preparing systemd/supervisord files" 1>&2

    echo "$0: setting up exabgp" 1>&2

    add1=()
    if [ "$install_systemd_services" = 1 ]; then
      if [ "$install_systemd_services__onlyinstall" = 1 -a "$setup_exabgp_full" = 1 ]; then
        add1=("--systemd" "--enable.min")
      elif [ "$install_systemd_services__onlyinstall" = 0 -a "$setup_exabgp_full" = 1 ]; then
        add1=("--systemd" "--enable")
      else
        add1=("--systemd")
      fi
    elif [ "$install_with_supervisord" = 1 ]; then
      if [ "$setup_exabgp_full" = 1 ]; then
        add1=("--supervisord")
      else
        add1=("--supervisord" "--no-autostart")
      fi
    fi

    exabgp_systemd_servicename="exabgpForFod" # statically defined in ./exabgp/run-exabgp-generic

    # ./exabgp/run-exabgp-generic
    FOD_SYSUSER="$FOD_SYSUSER" "$fod_dir/exabgp/run-exabgp-generic" --init-conf \
            "$setup_exabgp__nodeid" "$setup_exabgp__ip_addr" "$setup_exabgp__asnr" \
            "$setup_exabgp__peer_nodeid" "$setup_exabgp__peer_ip_addr" "$setup_exabgp__peer_asnr" \
            -- "${add1[@]}"
    # ./flowspy/settings.py
    #echo -e '\n#added by install-*.sh:\nPROXY_CLASS="proxy_exabgp"' >> flowspy/settings_local.py

    if [ "$install_systemd_services" = 1 ]; then # TODO support supervisord as well
      #echo "$0: installing systemd service file for exabgpForFod" 1>&2     

      #if [ "$setup_exabgp_full" = 0 ]; then
      #  :

      #elif [ "$install_systemd_services__onlyinstall" = 1 ]; then
      #  #systemctl enable --no-reload "$exabgp_systemd_servicename"
      #  #systemctl --machine enable --no-reload "$exabgp_systemd_servicename"
      #  ln -s -f -v "/usr/lib/systemd/system/$exabgp_systemd_servicename.service" /etc/systemd/system/multi-user.target.wants/
      #else
      #  systemctl daemon-reload
      #  systemctl enable "$exabgp_systemd_servicename"
      #  systemctl restart "$exabgp_systemd_servicename"

      #  sleep 5
      #  SYSTEMD_COLORS=1 systemctl status "$exabgp_systemd_servicename" | cat
      #  echo
      #fi
      :

    elif [ "$install_with_supervisord" = 1 ]; then
      #echo "$0: adding supervisord config for exabgpForFod" 1>&2          
      :

    fi
 
  fi

  )
  
  if [ "$inst_dir_is_fod_dir" = 1 ]; then
    echo "$0: step 2.9: finally fixing permissions as inst_dir_is_fod_dir=$inst_dir_is_fod_dir" 1>&2
    find "$fod_dir/" -not -user "$FOD_SYSUSER" -exec chown -v "$FOD_SYSUSER:" {} \;
  fi
  
  echo "$0: step 2 done" 1>&2

  set +e

fi

#############################################################################
#############################################################################

