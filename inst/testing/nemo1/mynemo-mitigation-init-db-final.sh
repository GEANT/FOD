#!/bin/bash

set -x

#

docker exec -ti nemo_mitigated_1 /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "attacker network" 10.1.10.0/24 
docker exec -ti nemo_mitigated_1 /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "victim network" 10.2.10.0/24 
docker exec -ti nemo_mitigated_1 /services/inst/nemo-erkennung/bin/nemo-dbadmin add_net --comments "customer2 network" 10.3.10.0/24 

docker exec -ti nemo_nemodb_1 psql -U nemo -c "INSERT INTO router_nets (router_id, net_id) VALUES (1, 1), (1, 2), (1, 3)"

cat /nemo-all/nemo-initial-detectors1.sql | docker exec -i nemo_nemodb_1 psql -U nemo nemo

#

docker restart nemo_eventd_1


