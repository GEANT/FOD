
= Build+Run FoD+Freertr+Attack/VictimHosts docker-compose

in FoD main dir of git checkout:

docker network prune # to be sure old network definitions are not conflicting
docker-compose build
docker-compose up 

./docker-compose/freertr_disable_offload.sh

= Test Blocking of Attack traffic in running docker containers started by docker-compose

# test attack traffic from host1 to host2
docker exec -ti host1 ping 10.2.10.12

add rule to block icmp traffic from 10.1.10.11 to 10.2.10.12

# investigate status on freertr
docker exec -ti freertr telnet 127.1 2323

# run show command
docker exec -ti freertr sh -c '{ echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | netcat 127.1 2323'



