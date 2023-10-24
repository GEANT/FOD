
= Build+Run FoD+Freertr+Attack/VictimHosts docker-compose

defined in ./docker-compose-singlefodctr-vol.yml (or ./docker-compose-singlefodctr-novol.yml)

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


= docker compose definitions and dependencyies:

./docker-compose-singlefodctr-vol.yml (or ./docker-compose-singlefodctr-novol.yml)
        - ./docker-compose/.env_fod_singlectr : various predefined important env variables used for FoD installation
        - ./docker-compose/Dockerfile_FOD (or ./docker-compose/Dockerfile_FOD-novol)
          - ./install-debian.sh : Debian/UBUNTU-specific FoD instalation and setup script
          - ./docker-compose/fod_setup_environment-step3.sh = in container: /opt/setup_environment.sh : on first run of container used for proper setup actions of FoD by ./install-debian.sh; needed because FoD dir is bind-mounted in container, and so these actions cannot be done priorly in container build
            - ./docker-compose/fod_supervisord.conf : docker-compose-specific supervisord config used for run control of FoD (=gunicorn+redis+celeryd) as well as exabgp (note: normal ./supervisord.conf.dist as well as the FoD start wrapper scripts ./runfod*.sh are not used in case of docker-compose)
              - /etc/exabgp/exabgp.conf : exabgp config created by FoD ./install-debian.sh as well as helper script ./exabgp/run-exabgp-generic (for configuring and/or running)
              - ./flowspy/settings.py and ./flowspy/settings_local.py : FoD Django settings (main file and local adaptions if necessary, resp.)


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


= FoD(+exabgp) container details

connected by IP address 10.197.36.2 to freertr (IP address 10.197.36.3), used for BGP peering via exabgp to Freertr
in container: 
  - ./docker-compose/fod_supervisord.conf : docker-compose-specific supervisord config used for run control of FoD (=gunicorn+redis+celeryd) as well as exabgp
  - /etc/exabgp/exabgp.conf : exabgp config created by FoD ./install-debian.sh as well as helper script ./exabgp/run-exabgp-generic (for configuring and/or running)
  - ./flowspy/settings.py and ./flowspy/settings_local.py : FoD Django settings (main file and local adaptions if necessary, resp.)

= attacker/victim host container details

host1: interface IP address 10.1.10.11 (connected to freertr interface IP address 10.1.10.3)
host2: interface IP address 10.2.10.12 (connected to freertr interface IP address 10.1.10.3)



