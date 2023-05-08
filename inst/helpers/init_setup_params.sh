#!/bin/bash

admin_user="$1"
shift 1

[ -n "$admin_user" ] || admin_user="admin"

#

admin_pwd="$1"
shift 1

[ -n "$admin_pwd" ] || admin_pwd="admin" # use with great care!

#

admin_peer_ip_prefix="$1"
shift 1

[ -n "$admin_peer_ip_prefix" ] || admin_peer_ip_prefix="0.0.0.0/0"

#

set -e

## run from FoD main dir:
#source ./venv/bin/activate
#echo "from django.contrib.auth.models import User; User.objects.create_superuser('$admin_user', '$admin_user@localhost', '$admin_pwd')" | ./manage.py shell

#

#peerid=10000 # needs to be unique in DB # on a new, empty DB, can be set to '1'
#userid=1 # set depending on values in auth_user
#
#source ./venv/bin/activate
#./manage.py dbshell
## add peer object:
#echo "insert into peer (peer_name, peer_id, peer_as, peer_tag, domain_name) values ('test1', '$peerid', '$peerid', 'test1', 'test1');" | ./manage.py dbshell
## add perr range object, there could be multiple ones as well:
#echo "insert into peer_range values (1000, '0.0.0.0/0');" ./manage.py dbshell # replace 1000 by unique id in peer_range_values" # associate peer and perr object:
#echo "insert into peer_networks (peer_id, peerrange_id) values (1, 1000);" | ./manage.py dbshell # same value (1000) as in line above # add user profile object for the
#user:
#echo "insert into accounts_userprofile values ('$userid', '$userid');" | ./manage.py dbshell # if there is already an entry in accounts_userprofile for the $userid,
#skip this line
## associate user profile and user with peer object:
#echo "insert into accounts_userprofile_peers values ('$userid', '$userid', '$peerid');"  | ./manage.py dbshell # if there is already an entry in
#accounts_userprofile_peers for the user replace the first "$userid" with the value of the "id" field in the existsing row of accounts_userprofile

source ./venv/bin/activate
export DJANGO_SETTINGS_MODULE="flowspy.settings" 
echo "from flowspec.init_setup import init_admin_user; init_admin_user('$admin_user', '$admin_pwd', '$admin_user@localhost', 'test_peer', '$admin_peer_ip_prefix')" | ./manage.py shell


