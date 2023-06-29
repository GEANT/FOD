# Installing FoD v1.7 Generic

This guide provides general information about the installation of FoD. In case you use Debian/UBUNTU, we provide detailed instructions for the installation.

Also it assumes that installation is carried out in `/srv/flowspy`
directory. If other directory is to be used, please change the
corresponding configuration files. It is also assumed that the `root` user
will perform every action.

TO UPDATE

## Requirements

### System Requirements
In order to install FoD properly, make sure the following software is installed on your computer.

- apache 2
- libapache2-mod-proxy-html
- gunicorn
- redis
- mysql
- python3
- python3-dev
- python-virtualenv
- pip
- gcc

### Download FoD
You can clone FoD from GEANT github repository. 

    mkdir -p /srv/
    cd /srv/
    git clone https://github.com/GEANT/FoD flowspy

### Python-virtualenv

    cd /srv
    virtualenv --python=python3 /srv/venv
    . /srv/venv/bin/activate

### Pip
In order to install the required python packages for FoD you can use pip:

    . /srv/venv/bin/activate
    cd /srv/flowspy
    pip install -r requirements.txt

### Create a database
If you are using mysql, you should create a database:

    mysql -u root -p -e 'create database fod'

### Copy dist files

    cd /srv/flowspy/flowspy
    cp settings.py.dist settings.py
    cp urls.py.dist urls.py

### Device Configuration
FoD generates and commits flowspec rules to a
device via netconf. You have to create an account
with rw access to flowspec and set these credentials
in settings.py. See Configuration for details.


### Adding some default data
Into `/srv/flowspy` you will notice that there is a directory called `initial_data`. In there, there is a file called `fixtures_manual.xml` which contains some default static pages for django's flatpages app. In this file we have placed 4 flatpages (2 for Greek, 2 for English) with Information and Terms of Service about the service. To import the flatpages, run from `/srv/flowspy`:

    . /srv/venv/bin/activate
    ./manage.py loaddata initial_data/fixtures_manual.xml


### Redis
Just make sure redis is installed and started

     # on DEBIAN/UBUNTU (>= DEBIAN 10/UBUNTU 18)
     apt-get install redis-server
     systemctl enable redis-server 
     systemctl start redis-server 

### mkdocs-based internal documentation
Just make sure mkdocs is installed and prepare documentation with it
(the documentation is optional and non-essential for the operation of FoD)

     # on DEBIAN/UBUNTU (>= DEBIAN 10/UBUNTU 18)
     apt-get install mkdocs
     cd /srv/flowspy
     mkdocs build

### Apache2
Apache proxies gunicorn. Things are more flexible here as you may follow your own configuration and conventions.

#### Example config
Here is an example configuration.

	<VirtualHost *:80>
	    ServerName fod.example.org
	    DocumentRoot /var/www
	    ErrorLog /var/log/httpd/fod_error.log
	    LogLevel debug
	    CustomLog /var/log/httpd/fod_access.log combined
	    RewriteEngine On
	    RewriteRule ^/(.*) https://fod.example.com/$1 [L,R]
	</VirtualHost>


	<VirtualHost *:443>
	    SSLEngine on
	    SSLProtocol TLSv1

	    SSLCertificateFile /home/local/GEANT/dante.spatharas/filename.crt
	    SSLCertificateKeyFile /home/local/GEANT/dante.spatharas/filename.key
	    SSLCACertificateFile /home/local/GEANT/dante.spatharas/filename.crt


	    Alias                   /static         /srv/flowspy/static

	    AddDefaultCharset   UTF-8
	    IndexOptions        +Charset=UTF-8

	    #SSLProxyEngine        off
	    ProxyErrorOverride    off
	    ProxyTimeout    28800
	    ProxyPass       /static !
	    ProxyPass        / http://localhost:8080/ retry=0
	    ProxyPassReverse / http://localhost:8080/

	</VirtualHost>

`Important!` You have to comment out/disable the default `Virtualhost` defined on line 74 until the end of this block at `/etc/httpd/conf.d/ssl.conf `.


### Gunicorn
FoD is served via gunicorn and is then proxied by Apache. If the above
directory conventions have been followed so far, then your configuration
should be:

    CONFIG = {
          'mode': 'django',
          'working_dir': '/srv/flowspy',
          'args': (
               '--bind=127.0.0.1:8081',
               '--workers=1',
               '--worker-class=egg:gunicorn#gevent',
               '--timeout=30',
               '--debug',
               '--log-level=debug',
               '--log-file=/var/log/gunicorn/fod.log',
          ),
    }

