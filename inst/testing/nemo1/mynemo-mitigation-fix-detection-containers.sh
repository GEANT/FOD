#!/bin/bash

##############################################################################

# to be fixed in outer docker container: /nemo-all/etc/*:
#[fishtank]
#deactivate_replisync: 1

# to be executed in out nemo docker container: in inside docker container mitigated or eventd :
#nemo-dbadmin add_authframeinformation INFRA "Infrastructure Protection" 0.0.0.0/0,::/0 alwaystrue

##############################################################################

DIDCLFS="_"
[ ! -f ./nemo1.env ] || . ./nemo1.env

#

set -x

docker exec -ti "nemo${DIDCLFS}mitigated${DIDCLFS}1" /services/inst/nemo-erkennung/bin/nemo-dbadmin add_authframeinformation INFRA "Infrastructure Protection" 0.0.0.0/0,::/0 alwaystrue
echo

##

sed -i -e 's#^.*deactivate_replisync.*$#deactivate_replisync: 1#' /nemo-all/etc/nemo-analyse/fishtank/nemo.conf
docker restart "nemo${DIDCLFS}fishtank${DIDCLFS}1"
echo

cp -f /nemo-all/create_vsmd1.py /nemo-all/etc/nemo-erkennung/mitigated/ # TODO: currently misuse of shared fs
docker exec -ti "nemo${DIDCLFS}mitigated${DIDCLFS}1" python3 /services/etc/nemo/create_vsmd1.py

##

#docker exec -ti nemo${DIDCLFS}mitigated${DIDCLFS}1 /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "attacker network" 10.1.10.0/24 
#docker exec -ti nemo${DIDCLFS}mitigated${DIDCLFS}1 /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "victim network" 10.2.10.0/24 
#docker exec -ti nemo${DIDCLFS}mitigated${DIDCLFS}1 /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "customer2 network" 10.3.10.0/24 
#
#docker exec -ti nemo${DIDCLFS}nemodb${DIDCLFS}1 psql -U nemo -c "INSERT INTO router_nets (router_id, net_id) VALUES (1, 1), (1, 2), (1, 3)"


