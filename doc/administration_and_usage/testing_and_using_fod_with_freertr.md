# Testing and Using {{ product_name_short }} (exabgp version) with Freertr 

Freertr ([http://www.freertr.org](http://www.freertr.org/), [http://docs.freertr.org/](http://docs.freertr.org/)): a Open Source Network Operating System with support of a huge list of routing prototocols, data plan protocols (including P4)

## Docker containers for use of {{ product_name_short }} (exabgp version) with Freertr:

1. using 2 containers ({{ product_name_short }}+exabgp container and freertr container) manually:
./inst/testing/fodexabgp/README.txt
./inst/testing/fodexabgp/install_fodexabgp__docker.sh

2. using only freertr container (for use with OS-installed {{ product_name_short }})
./inst/testing/fodexabgp/install_freertronly__docker.sh.new

3. using containerlab for coordinated run of {{ product_name_short }}+exabgp container, freertr container, and attacker/victim host containers
./inst/testing/fodexabgp-containerlab1/README.md info
./inst/testing/fodexabgp-containerlab1/Dockerfile

4. using docker-compose for coordinated run of {{ product_name_short }}+exabgp container, freertr container, and attacker/victim host containers
./docker-compose/README.txt info
./docker-compose.yml default docker compose specification using bind-mounted {{ product_name_short }} dir (mainly for developers)
./docker-compose-novol.yml docker compose specification without bind-mounted {{ product_name_short }} dir (for testing or demo-ing)


