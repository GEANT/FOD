#!/bin/bash

# to be run from FoD main dir

# ./docker-compose/README.txt

use_novol=1

if [ "$use_novol" = 1 ]; then
  #docker_compose_spec__file="./docker-compose-novol.yml"
  docker_compose_spec__file="./docker-compose-singlefodctr-novol.yml"
  fod_container_name="fodnovol"
else
  #docker_compose_spec__file="./docker-compose.yml"
  #fod_container_name="fod"
  docker_compose_spec__file="./docker-compose-singlefodctr-vol.yml"
  fod_container_name="fodvol"
fi

##

set -e

##

count_up="$(docker-compose -f "$docker_compose_spec__file" ps | grep Up | wc -l)"

if [ "$1" = "rebuild" -o "$count_up" != 4 ]; then
  echo "$0: 0.a. docker-compose set not fully setup, trying to do so" 1>&2

  echo "$0: 0.a.1. tearing down docker-compse set completly" 1>&2
  docker-compose -f "$docker_compose_spec__file" down

  echo "$0: 0.a.2. (re-)building docker-compose set" 1>&2
  docker-compose -f "$docker_compose_spec__file" build

  echo "$0: 0.a.3. bringing docker-compose set up" 1>&2
  docker-compose -f "$docker_compose_spec__file" up -d

  reinit_done=1

else
  echo "$0: 0.a. docker-compose seems to be ready" 1>&2
  reinit_done=0
fi

#

echo "$0: 0.b. running freertr_disable_offload hack" 1>&2
./docker-compose/freertr_disable_offload.sh || true

if [ "$use_novol" != 1 ]; then # compare ./docker-compose/fod_setup_environment-step3.sh used by ./docker-compose/Dockerfile_FOD (in case $novol == 0)
  echo "$0: 0.c. making sure bind-mounted FoD dir is setup from within container" 1>&2
  while ! docker exec -ti "$fod_container_name" ls /opt/setup_ok &>/dev/null; do
    echo "$0: 0.c. docker container has not yet fully completed setup of FoD dir from inside container, so waiting 1 sec" 1>&2
    sleep 1  
  done
fi

#

clear
echo 1>&2
echo "$0: beginning with demo proper." 1>&2
echo 1>&2
echo "$0: 1. part1: initial ping between host1 and host2" 1>&2
echo 1>&2

echo "$0: 1.a. disabling any left-over rules in FoD:" 1>&2
docker exec -ti "$fod_container_name" ./inst/helpers/enable_rule.sh 10.1.10.11/32 10.2.10.12/32 1 -1

#

clear
echo 1>&2
echo "$0: 1.b. initial ping between host1 and host2" 1>&2

echo "$0: 1.b.1. show exabgp current exported rules/routes:" 1>&2
docker exec -ti "$fod_container_name" sh -c '. /opt/venv/bin/activate && exabgpcli show adj-rib out extensive'

echo "$0: 1.b.2. freertr policy-map and block counters:" 1>&2
docker exec -ti freertr sh -c '{ echo "show ipv4 bgp 1 flowspec summary"; echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | netcat 127.1 2323'

sleep 2

echo "$0: 1.b.3. ping not to be blocked:" 1>&2
docker exec -d -ti host1 ping -c 1 10.2.10.12
docker exec -ti host1 ping -c 7 10.2.10.12

echo "$0: 1.b.4. freertr policy-map and block counters:" 1>&2
docker exec -ti freertr sh -c '{ echo "show ipv4 bgp 1 flowspec summary"; echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | netcat 127.1 2323'

###

wait1=10
echo 1>&2
echo "waiting $wait1 seconds" 1>&2
sleep "$wait1"

#

clear
echo 1>&2
echo "$0: beginning with demo proper." 1>&2
echo 1>&2
echo "$0: 2. part2: blocked ping between host1 and host2" 1>&2
echo 1>&2

echo "$0: 2.a. adding of blocking rule:" 1>&2
echo 1>&2

echo "$0: 2.a.1.a. show exabgp current exported rules/routes (before adding the blocking rule):" 1>&2
docker exec -ti "$fod_container_name" sh -c '. /opt/venv/bin/activate && exabgpcli show adj-rib out extensive'

echo "$0: 2.a.1.b. show freertr flowspec status/stistics (before adding the blocking rule):" 1>&2
docker exec -ti freertr sh -c '{ echo "show ipv4 bgp 1 flowspec summary"; echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | netcat 127.1 2323'

echo "$0: 2.a.2. proper adding of blocking rule:" 1>&2
#docker exec -ti "$fod_container_name" ./inst/helpers/add_rule.sh 10.1.10.11 10.2.10.12 1
docker exec -ti "$fod_container_name" ./inst/helpers/enable_rule.sh 10.1.10.11/32 10.2.10.12/32 1
#docker exec -ti "$fod_container_name" ./inst/helpers/list_rules_db.sh

echo "$0: 2.a.3.a. show exabgp current exported rules/routes (after adding the blocking rule):" 1>&2
docker exec -ti "$fod_container_name" sh -c '. /opt/venv/bin/activate && exabgpcli show adj-rib out extensive'

echo "$0: 2.a.3.b. show freertr flowspec status/stistics (after adding the blocking rule):" 1>&2
docker exec -ti freertr sh -c '{ echo "show ipv4 bgp 1 flowspec summary"; echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | netcat 127.1 2323'

#

wait1=10
echo 1>&2
echo "waiting $wait1 seconds" 1>&2
sleep "$wait1"

#

clear
echo 1>&2
echo "$0: 2.b. blocked ping between host1 and host2:" 1>&2
echo 1>&2

sleep 2

echo "$0: 2.b.1. show exabgp current exported rules/routes:" 1>&2
docker exec -ti "$fod_container_name" sh -c '. /opt/venv/bin/activate && exabgpcli show adj-rib out extensive'

echo "$0: 2.b.2. show freertr flowpec status/statistics (before ping to be blocked):" 1>&2
docker exec -ti freertr sh -c '{ echo "show ipv4 bgp 1 flowspec summary"; echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | netcat 127.1 2323'

echo "$0: 2.b.3. ping to block:" 1>&2
docker exec -ti host1 ping -c 7 10.2.10.12 || true

echo "$0: 2.b.4. show freertr flowspec status/statistics (after ping to be blocked):" 1>&2
docker exec -ti freertr sh -c '{ echo "show ipv4 bgp 1 flowspec summary"; echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | netcat 127.1 2323'


