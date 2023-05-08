
./mybuildrun-rtr-flowspec1 : script to setup rtr-flowspec1 docker container
  with no arguments will add config for (exabgp) remote BGP peer 172.17.0.1, AS 1001 -> freertr AS 2001  
  otherwise argument 1 can be used to specify remote BGP peer IP address:
  e.g. "./mybuildrun-rtr-flowspec1 172.17.0.2" # assume FoD exabgp is running as first started docker container (e.g. based on ubuntu0 docker container)
./docker1/ : stuff used by ./mybuildrun-rtr-flowspec1
  

./example-commands-freertrcli.txt : some basic freertr cli commands regarding BGP FlowSpec


./myethtool_disable_offload : run with an network interface name as argument 1, tries to disable all offload features, especially to be used on veth end points being the peer veth endpoint to a veth controlled by a freertr instance

./myethtool_disable_offload__docker_veth_endpoint : run with a dockerid (or docker tag label) as first argument: will try to run ./myethtool_disable_offload on the peer veth endpoint for that docker containers's eth0 (being a veth endpoint in fact); is called by ./mybuildrun-rtr-flowspec1 in background 10 seconds after start of the rtr-flowspec1 docker container

