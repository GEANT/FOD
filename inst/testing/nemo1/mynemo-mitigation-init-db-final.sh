#!/bin/bash

set -x

#

docker exec -ti nemo_mitigated_1 /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "attacker network" 10.1.10.0/24 
docker exec -ti nemo_mitigated_1 /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "victim network" 10.2.10.0/24 
#docker exec -ti nemo_mitigated_1 /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "victim host" 10.2.10.12/32
#docker exec -ti nemo_mitigated_1 /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "attacker host" 10.1.10.11/32

idx=2
#for add_net in $(docker exec -i freertr ip a | grep -o "veth[3-9]@"); do
for add_net in $(grep -- "ipv4 address 10.[3-9].10.3" frnet/docker-compose/freertr.cfg); do
  idx=$(( $idx + 1 ))
  echo "$0: idx=$idx" 1>&2
  docker exec -ti nemo_mitigated_1 /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "customer$idx network" "10.$idx.10.0/24"
done

#

#docker exec -ti nemo_nemodb_1 psql -U nemo -c "INSERT INTO router_nets (router_id, net_id) VALUES (1, 1), (1, 2), (2, 2), (3, 1)"
set -x
num=1
echo "select id, name from router;" | docker exec -i nemo_nemodb_1 psql -U nemo -t | while read id sep1 name; do
  echo "loop id=$id <-> name=$name" 1>&2
 
  case "$name" in
	  freertr1*) 
            docker exec nemo_nemodb_1 psql -U nemo -c "INSERT INTO router_nets (router_id, net_id) VALUES ($id, 1), ($id, 2)"
          ;;
          host1*) 
            docker exec nemo_nemodb_1 psql -U nemo -c "INSERT INTO router_nets (router_id, net_id) VALUES ($id, 1)"
	  ;;
	  host2*) 
            docker exec nemo_nemodb_1 psql -U nemo -c "INSERT INTO router_nets (router_id, net_id) VALUES ($id, 2)"
	  ;;
  esac

  num=$(( $num + 1 ))
done

#


cat /nemo-all/nemo-initial-detectors1.sql | docker exec -i nemo_nemodb_1 psql -U nemo nemo

#

docker restart nemo_eventd_1


