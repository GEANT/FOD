# Installation on DEBIAN/UBUNTU

For the installation on recent DEBIAN or UBUNTU, e.g., UBUNTU focal (20.04),
there is ./install-debian.sh .

It understands several command line switches:

- --fod_dir DIRNAME : specify FoD run-time directory, where FoD files are to be copied and to be run from 
- --venv_dir DIRNAME : specify where Python virtualenv used by FoD will be located
- --base-dir DIRNAME : specify base directory where FoD run-time directory and virtualenv directory will be sub directories
- --here : do not copy FoD files into a separate FoD run-time directory, but instead install and make to run from current directory (probably not so useful for production)

- --systemd : enable Systemd support explicitly, by default will be enabled if Systemd is detected 
- --no_systemd : disable Systemd support explicitly, even if Systemd is detected
- --systemd_only_install : when enabling Systemd support, but do not try to contact a running Systemd to reload, only install Systemd service files (useful during Docker build)
- --systemd_check_start : when enabling Systemd support, do try to contact a running Systemd to reload and show status (default)

- --supversiord : enable Supversiord instead of Systemd, inside Docker Supversiord is now enabled by default in case no Systemd running s detected
- --no_supversiord : disable Supversiord explicitly

- --basesw : only install FoD dependencies (OS packages + Python Pip packages in virtualenv directory), do not install and setup FoD run-time directory (combines --basesw_os and --basesw_python)
- --basesw_os : only install FoD OS dependencies 
- --basesw_python : only install FoD Python/Pip dependencies in virtualenv directory
- --fodproper : skip installing FoD dependencies, only install and setup FoD run-time directory 

- --setup_admin_user : setup default admin 
- --setup_admin_user5 : setup admin specified by user name, password, email address, peer name, first IP prefix 

- --netconf : setup NETCONF specified by device address, TCP port, user name, password
- --exabgp : setup exabgp specified by BGP nodeid, IP address, AS number, peer IP address, peer AS number (only for the new FoD version, currently available in git branch "feature/exabgp_support2")

- --with-mta-postfix : if no MTA is installed, will try to install postfix (FoD operation is dependant on e-mail sending being available)

- --with-db-sqlite : use a SQLite DB for FoD DB (not recommended for production, but easy for testing)
- --with-db-mysql : will try to install MySQL and to setup FoD database in MySQL
- --with-db-mariadb : will try to install MariaDB and to setup FoD database in MariaDB
- --with-db-mysqllike : assumes that MySQL or MariaDB is installed and will try to setup FoD database based on this

## Systemd support / Starting FoD

FoD installation currently supports Systemd, i.e., it installs Systemd startup files (./systemd/fod-\*.service) when a running Systemd is detected. Otherwise, in case of running inside docker Supversiord is enabled.
Also, Supversiord can be enabled instead of Systemd explicitly (check options above)

When not running under systemd,
alternatives for startup of FoD 
are either
./runfod-fg.sh for directly starting FoD processes together with Redis task broker 
or
./runfod-supervisord.sh for starting FoD processes and Redis task broker via Supervisord
or
the overall wrapper script ./runfod.sh which uses either of the startup method depending 
on the choice selected by options for install-debian.sh.

The Systemd support also includes an experimental e-mail notification for startup-failures of the FoD processes

## FoD run-time status 

There is ./systemd/fod-status.sh, a generic script (not limited to Systemd) for determining the process status of FoD along with some further aspects, e.g., Database connection, NETCONF configuration and reachability


