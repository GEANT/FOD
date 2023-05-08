#!/bin/bash
#!/bin/sh

export LC_ALL="C"

if grep -q '^CentOS' /etc/redhat-release 2> /dev/null; then
cat > /etc/yum.repos.d/shibboleth.repo <<END
[shibboleth]
name=Shibboleth (CentOS_7)
# Please report any problems to https://issues.shibboleth.net
type=rpm-md
mirrorlist=https://shibboleth.net/cgi-bin/mirrorlist.cgi/CentOS_7
gpgcheck=1
gpgkey=https://shibboleth.net/downloads/service-provider/RPMS/repomd.xml.key
enabled=1
END
yum -y -q install httpd shibboleth perl perl-CGI mod_ssl
DISTRO=centos
else
[ -z "$NOAPT" ] && apt-get -y install apache2 libapache2-mod-shib2 perl libcgi-pm-perl

[ -z "$NOMOD" ] && a2enmod proxy
[ -z "$NOMOD" ] && a2enmod proxy_http
[ -z "$NOMOD" ] && a2enmod cgi
fi
# 

basedir="/srv/flowspy"
basedir2="$basedir/inst/apache_shib"

#cd /srv/flowspy/ || exit 3
cd "$basedir" || exit 3

#cp -uva shibboleth_inst/inst/etc/apache2/ shibboleth_inst/inst/etc/shibboleth/ /etc/

echo 1>&2
#cp -uva shibboleth_inst/inst/etc/apache2/ /etc/
#cd ./shibboleth_inst/inst/etc/apache2/ && cp -uva --parents -t /etc/apache2/ .
#cd "$basedir/shibboleth_inst/inst/etc/apache2/" && cp -uva --parents -t /etc/apache2/ $(cat "$basedir/shibboleth_inst/etc-apache-diff.list.filtered2")

if [ "$DISTRO" = centos ]; then
	dsthttpd=/etc/httpd/
        cp "$basedir2/files.inst/centos/httpd-fod.conf" "$dsthttpd/conf.d/"
else
	dsthttpd=/etc/apache2/
	(cd "$basedir2/files.inst/etc/apache2/" && cp -fva --parents -t "$dsthttpd" $(cat "$basedir2/files.inst/etc-apache-diff.list.filtered2"))
fi


echo 1>&2
#cp -uva shibboleth_inst/inst/etc/shibboleth/ /etc/
(cd "$basedir2/files.inst/etc/shibboleth/" && cp -fva --parents -t /etc/shibboleth/ $(cat "$basedir2/files.inst/etc-shibboleth-diff.list.filtered2"))

##

echo 1>&2
(cd flowspy; patch settings.py < 02-settings.py-shibboleth.patch;)

echo 1>&2
(cd /etc/shibboleth/ && ./keygen.sh)

echo 1>&2
# -subj "/C=AU/ST=Some-State/O=Internet Widgits Pty Ltd/"
(cd "$dsthttpd" && openssl req -x509 -batch -nodes -days 365 -newkey rsa:2048 -keyout mysitename.key -out mysitename.crt)

##

echo 1>&2
hostname test-fod.geant.net

##

if [ "$DISTRO" = centos ]; then
	chown -R apache: /etc/shibboleth/
	systemctl enable httpd
	systemctl enable shibd
	service httpd restart
	service shibd restart
else
	/etc/init.d/apache2 restart
	/etc/init.d/shibd restart
fi

