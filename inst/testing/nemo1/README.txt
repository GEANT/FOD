
= build+run nemo docker-in-docker container together with freertr+attack/victim-hosts docker-compose

0)
General pre-requisites: nemo-* dirs checked-out in this sub dir


1) Freertr+attack/victim-hosts docker-compose:

in this sub directory of git checkout run:

docker network prune # to be sure old network definitions are not conflicting (stop dependent containers as necessary before)

# + make sure no old, conflicting nat iptable rules are in POSTROUTING Table (iptables -t nat -L POSTROUTING)

docker-compose -f docker-compose-freertr-ddos.yml build

docker-compose -f docker-compose-freertr-ddos.yml down

docker-compose -f docker-compose-freertr-ddos.yml up 

./docker-compose/freertr_disable_offload.sh


2) (outer) nemo docker-in-docker container:
(pre-requisites: nemo-* dirs checked-out in this sub dir)

in this sub dir of git checkout run:
./mynemo-docker-dind --all1 

nemo setup will be run inside the (outer) nemo docker-in-docker container. Answers:
host = localhost
...
email address = test@localhost
user name = test
...

# freertr is reachable via IP address 10.197.36.3 (via 10.197.36.2 on corresponding interface in (outer) nemo docker-in-docker container),,
especially from (inside) nemo container nemo_nfcapd_1 (which sharing network namespace of its "host" = (outer) nemo docker-in-docker container)

alternatively install flow generating software inside (outer) nemo docker-in-docker container directly,
and, e.g., connect from (inside) nemo container nemo_nfcapd_1 to it using 10.197.36.2 as target address



= for testing etc.

# test attack traffic from host1 to host2
docker exec -ti host2 ping 10.1.10.11
docker exec -ti host1 ping 10.2.10.12

# test connectivity between (outer) nemo docker-in-docker container to freertr container
docker exec -ti nemo-all1 ping 10.197.36.2

# investigate status on freertr
docker exec -ti freertr telnet 127.1 2323

# run show command
docker exec -ti freertr sh -c '{ echo "show ipv4 bgp 1 flowspec database"; echo "show policy-map flowspec CORE ipv4"; echo exit; } | netcat 127.1 2323'


= docker compose definitions and dependencyies:

./docker-compose-freertr-ddos.yml :

        - ./docker-compose/.env_freertr
        - ./docker-compose/Dockerfile_FREERTR
        - ./docker-compose/freertr.cfg : template for freertr config in freertr container

        - ./docker-compose/.env_host1
        - ./docker-compose/Dockerfile_HOST1

        - ./docker-compose/.env_host2
        - ./docker-compose/Dockerfile_HOST2


= freertr docu general

http://www.freertr.org/

http://docs.freertr.org/


= freertr container details

template for freertr config in freetrt container: ./docker-compose/freertr.cfg
FoD-relevant config sections: 
  - interface ethernet3
  - router bgp[46] 1

./freertr/run docker volume to access/store freertr /run/rtr/ dir


= nemo docker-in-docker container details

connected by IP address 10.197.36.2 to freertr (IP address 10.197.36.3), used for BGP peering via exabgp to Freertr

= attacker/victim host container details

host1: interface IP address 10.1.10.11 (connected to freertr interface IP address 10.1.10.3)
host2: interface IP address 10.2.10.12 (connected to freertr interface IP address 10.1.10.3)



