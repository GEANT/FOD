# Basic Administration and Usage

Early steps for administration and usage that can be done after FoD has been installed.

## 1: Setup NETCONF + FoD admin user 

### 1 (local): Setup NETCONF + FoD admin user (FoD running locally)

admin user password and NETCONF connection has to be setup, 
either by

A) via the setup page of FoD in container
(needs ENABLE_SETUP_VIEW=True in ./flowspy/settings.py; 
only applicable once, i.e., as long as no admin user has been setup, for security reasons):

http://SERVERNAME:SERVERPORT/setup/

(/setup not only covers NETCONF connectivity and initial admin user/password, 
but also the adding of a single peer range, i.e., an IP address prefix, (via a single peer)
to be assigned to the initial admin user,
in order to allow the creation/changing FlowSpec rules with a destination IP address prefix
falling within that single peer range)

or alternatively

B) manually

edit /srv/flowspy/flowspy/settings.py : settings NETCONF_DEVICE, NETCONF_PORT, NETCONF_USER, NETCONF_PASS

make sure IP connectivity to NETCONF_DEVICE is available

in FoD installation dir (default: /srv/flowspy): ./pythonenv ./manage.py createsuperuser ...
in FoD installation dir (default: /srv/flowspy): ./pythonenv ./manage.py changepassword ...

restart FoD: 'systemctl restart fod-gunicorn; systemctl restart fod-celeryd' (if installed and running with Systemd support)

or alternatively

C) already having been set by install-\*.sh parameters (check [Debian/Ubuntu Installation](../installation/v1.7/debian_ubuntu.md) or [CENTOS 7 Installation](../installation/v1.7/centos.md) )

### 1 (Docker): Setup NETCONF + FoD admin user (FoD running in a Docker container)

admin user password and NETCONF connection has to be setup, 
either by

A) via the setup page of FoD in container
(only applicable once, i.e., as long as no admin user has been setup, for security reasons):

http://127.0.0.1:8001/setup/

(/setup not only covers NETCONF connectivity and initial admin user/password, 
but also the adding of a single peer range, i.e., an IP address prefix, (via a single peer)
to be assigned to the initial admin user,
in order to allow the creation/change of FlowSpec rules with a destination IP address prefix
falling within that single peer range)

or alternatively

B) manually

in by entering the running container and editing
docker exec -ti "$DOCKERID" bash # find out DOCKERID of running container with "docker ps"

in docker: vi /srv/flowspy/flowspy/settings.py : settings NETCONF_DEVICE, NETCONF_PORT, NETCONF_USER, NETCONF_PASS

make sure docker container has IP connectivity to NETCONF_DEVICE

in docker: cd /srv/flowspy; ./pythonenv ./manage.py createsuperuser ...

in docker: cd /srv/flowspy; ./pythonenv ./manage.py changepassword ...

## 2: Accessing the FoD UI running in container after setup of admin user and password

http(s)://SERVERNAME:SERVERPORT/altlogin
(for use with Docker: http(s)://SERVERNAME:8000/altlogin)

(do not try to use the Shibboleth login, i.e., via /login, as it is not working without a set-up Shibboleth SP, see 2.1.2)

### 2.1 administration 

via http(s)://SERVERNAME:SERVERPORT/admin (only accessible by admin users, e.g., the initial admin, see 1.)

#### 2.1.1 administration of peers, peer ranges, and users (via /admin)

Peer ranges and Peers:
(http(s)://SERVERNAME:SERVERPORT/admin/peers/peerrange/ and http(s)://SERVERNAME:SERVERPORT/admin/peers/peer/)

The 'peer' is a concept in FoD to support multi-tenancy.
Each peer has assigned a set of allowed destination IP address prefixes ('peer ranges')
for which the peer is allowed to deploy BGP FlowSpec rules.
It typically corresponds to a customer organization of the network operator organization running FoD
to provided to users of the different customer organizations.

For managing users (beyond the initial setup of the first admin user, under 1.) the /admin web UI interface can be used
as well, specifically http(s)://SERVERNAME:SERVERPORT/admin/auth/user/.
E.g., it allows adding/removing users, changing first/last name of a user, define whether it is an admin or not.

A 'user' in FoD (including every admin user) has assigned a set of peers (typically, often only 1).
Only for destination IP address prefixes of assigned peers the user has the right to
deploy or change BGP FlowSpec rules.

This restriction also applies for the initial admin user created initially (see 1.).
So before that admin user can deploy FlowSpec rules via FoD, a peer has to be created (maybe by this admin user).
and appropriate peer ranges have to assigned to the peer
and this peer has to assigned to the user.

Simple example: a single peer with peer ranges '0.0.0.0/0' and '0::0/0' assigned to an admin user, 
allows to add/edit BGP FlowSpec rules with arbitrary destination IP prefixes.
For production deployments this is not generally recommended, 
in order to avoid severe mitigation mistakes by admin users.

The basic setup via http(s)://SERVERNAME:SERVERPORT/setup (see 1.)
not only covers NETCONF connectivity and initial admin user, but also the adding of a single peer range for a single peer
to be assigned to the initial admin user.

#### 2.1.2 administration of user and their peer mapping (via Shibboleth + enrollment working for users)

TODO: User management via Shibboleth

TODO: enrollment workflow for users 

TODO: auto update of enrolled users on login

### 2.2 usage

#### 2.2.1 usage via web UI

When logged into FoD UI via
http(s)://SERVERNAME:SERVERPORT/altlogin
(or via https://SERVERNAME:SERVERPORT/login for use with Shibboleth enrolled/registered users, see 2.1.2)
with a FoD user account which has assigned 1 or more peers with appropriate peer ranges (see 2.1.1)
the normal usage can start.

##### Rules list/table page

Provides a list/table of of all rule for all peers of the user.
BGP FlowSpec rule can have either status inactive (stored only in FoD database),
or active (stored in FoD database + installed on the router via NETCONF)

##### Rules dashboard

Provides a history of rule changes for all peers of the user.

##### Add New Rule

Allows to add a new rule, i.e., one not yet stored in the FoD database,
to FoD database and transfer it via NETCONF to the router(s).

##### Edit Existing Rule

Reachable from rules list page or dashboard page for all existing (active or inactive) displayed rules
for all peers of the user.
An edited route is changed in the FoD data base as well as updated on the router,
i.e., will be in active status after the edit operation.

##### Overview (for admin users)

TODO

##### Admin (only for admin users, see 2.1)

For admin users only, allows to perform (Django) admin actions (see 2.1)

##### User Profile

overview of the own user account, showing first/last name etc.

create REST API token (see [API v1.7](../api/api-v1.7.md))

#### 2.2.2 usage via REST API

see [API v1.7](../api/api-v1.7.md)

#### 3. Further/Regular Administration

### FoD run-time status 

There is ./systemd/fod-status.sh, a generic script (not limited to Systemd) for determining the process status of FoD along with some further aspects, e.g., Database connection, NETCONF configuration and reachability


