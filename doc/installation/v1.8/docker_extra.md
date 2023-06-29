# Extra Docker containers for testing FoD without router hardware


### NETCONF test server docker container

When no real NETCONF-enabled router supporting BGP FlowSpec is available, just for testing the NETCONF test server Docker container can be used:

In FoD-cloned installation dir, e.g., residing in /srv/flowspy, go to sub directory `router-container`

```
docker build -t juniper .

docker run -it --name juniper -p 830:830 --rm juniper:latest
```

To manually test NETCONF access to the test server, see `/router-container/run.txt`.

Now, find out IP address of the running test server container, e.g., by
docker inspect "$DOCKERID_NETCONF" | grep IPAddress # find out DOCKERID_NETCONF, e.g. by "docker ps"

In FoD test container (see above) configure this IP address of the NETCONF test server,
with NETCONF port 830, NETCONF_USER "netconf" and NETCONF_PASS "netconf"

Now, FoD can submit FlowSpec rules which are actually only stored inside the NETCONF test server
without an actual effect on any network, but FoD functionality of controlling rules can be tested. 

### NETCONF test server docker container based on netconfd instead of netopeer

similar to router-container/Dockerfile but will use netconfd (DEBIAN package) instead of CESNET's netopeer NETCONF server

- ./Dockerfiles.d/Dockerfile.vnet_router0a : 

### NETCONF test server docker container extended to virtual DDoS test network

Based on an instance of the NETCONF test server docker container

Extending with Mininet/OpenVSwitch, 
a basic a script for syncing NETCONF rules stored in the test NETCONF server
to OpenFlow rules in Mininet simulating BGP FlowSpec rules (not all cases supported),
SNMPd and a Perl SNMPd statistic collector script

Yields a more complete simulation of a router for FoD.

- ./Dockerfiles.d/Dockerfile.vnet_router1 : based on netopeer2
- ./Dockerfiles.d/Dockerfile.vnet_router2 : similar to Dockerfile.vnet_router1, but will use netconfd (DEBIAN package) instead of CESNET's netopeer NETCONF server

- ./Dockerfiles.d/Dockerfile.vnet_router2.ubuntu: like ./Dockerfiles.d/Dockerfile.vnet_router2, but based on UBUNTU
- ./Dockerfiles.d/Dockerfile.vnet_router2.debian.exabgp1: extending ./Dockerfiles.d/Dockerfile.vnet_router2 to install some stuff for bgp testing inside the Mininet: exabgp, quagga, bird1
- ./Dockerfiles.d/Dockerfile.vnet_router2.debian.exabgp2: extending ./Dockerfiles.d/Dockerfile.vnet_router2 to install some stuff for bgp testing inside the Mininet: exabgp, bird2
- ./Dockerfiles.d/Dockerfile.vnet_router2.debian.exabgp2.topo2: extending ./Dockerfiles.d/Dockerfile.vnet_router2 to simple BGP testing vnet based on exabgp and bird2

(find instructions how to build and run inside the Dockerfiles)

