#!/bin/bash

# to be run inside nemo-all1 outer container

set -x

#

# defaults
attacker_network1="10.1.10.0/24"
victim_network1="10.2.10.0/24"

DIDCLFS="_"

[ ! -f /nemo-all/nemo1.env ] || . /nemo-all/nemo1.env

#

#docker exec -ti "nemo${DIDCLFS}mitigated${DIDCLFS}1" /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "attacker network" 10.1.10.0/24 
#docker exec -ti "nemo${DIDCLFS}mitigated${DIDCLFS}1" /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "victim network" 10.2.10.0/24 
docker exec -ti "nemo${DIDCLFS}mitigated${DIDCLFS}1" /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "attacker network" "$attacker_network1" 
docker exec -ti "nemo${DIDCLFS}mitigated${DIDCLFS}1" /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "victim network" "$victim_network1"
#docker exec -ti "nemo${DIDCLFS}mitigated${DIDCLFS}1" /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "victim host" 10.2.10.12/32
#docker exec -ti "nemo${DIDCLFS}mitigated${DIDCLFS}1" /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "attacker host" 10.1.10.11/32

idx=2
#for add_net in $(docker exec -i freertr ip a | grep -o "veth[3-9]@"); do
for add_net in $(grep -- "ipv4 address 10.[3-9].10.3" frnet/docker-compose/freertr.cfg); do
  idx=$(( $idx + 1 ))
  echo "$0: idx=$idx" 1>&2
  docker exec -ti "nemo${DIDCLFS}mitigated${DIDCLFS}1" /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "customer$idx network" "10.$idx.10.0/24"
done

#

#docker exec -ti "nemo${DIDCLFS}nemodb${DIDCLFS}1" psql -U nemo -c "INSERT INTO router_nets (router_id, net_id) VALUES (1, 1), (1, 2), (2, 2), (3, 1)"
set -x
num=1
echo "select id, name from router;" | docker exec -i "nemo${DIDCLFS}nemodb${DIDCLFS}1" psql -U nemo -t | while read id sep1 name; do
  echo "loop id=$id <-> name=$name" 1>&2
 
  case "$name" in
	  freertr1*|$main_router_name*) 
            docker exec "nemo${DIDCLFS}nemodb${DIDCLFS}1" psql -U nemo -c "INSERT INTO router_nets (router_id, net_id) VALUES ($id, 1), ($id, 2)"
          ;;
          host1*) 
            docker exec "nemo${DIDCLFS}nemodb${DIDCLFS}1" psql -U nemo -c "INSERT INTO router_nets (router_id, net_id) VALUES ($id, 1)"
	  ;;
	  host2*) 
            docker exec "nemo${DIDCLFS}nemodb${DIDCLFS}1" psql -U nemo -c "INSERT INTO router_nets (router_id, net_id) VALUES ($id, 2)"
	  ;;
  esac

  num=$(( $num + 1 ))
done

#


#cat /nemo-all/nemo-initial-detectors1.sql | docker exec -i "nemo${DIDCLFS}nemodb${DIDCLFS}1" psql -U nemo nemo
cat /nemo-all/nemo-initial-*.sql | docker exec -i "nemo${DIDCLFS}nemodb${DIDCLFS}1" psql -U nemo nemo

#

docker restart "nemo${DIDCLFS}eventd${DIDCLFS}1"


