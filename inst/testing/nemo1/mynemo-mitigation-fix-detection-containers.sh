#!/bin/bash

# to be called within /nemo-all/ as cwd in outer nemo-all container

##############################################################################

# to be fixed in outer docker container: /nemo-all/etc/*:
#[fishtank]
#deactivate_replisync: 1

# to be executed in out nemo docker container: in inside docker container mitigated or eventd :
#nemo-dbadmin add_authframeinformation INFRA "Infrastructure Protection" 0.0.0.0/0,::/0 alwaystrue

##############################################################################

DIDCLFS="_"
[ ! -f ./nemo1.env ] || . ./nemo1.env

#
  
[ -n "$MYNEMO_DOCKER_INNER_INST_DIR" ] || MYNEMO_DOCKER_INNER_INST_DIR="/nemo-all"

#

set -x

# add default authorization object:
echo "$0: adding default nemo authorization:" 1>&2
docker exec -ti "nemo${DIDCLFS}mitigated${DIDCLFS}1" /services/inst/nemo-erkennung/bin/nemo-dbadmin add_authframeinformation INFRA "Infrastructure Protection" 0.0.0.0/0,::/0 alwaystrue
echo

##

# needed fix:
echo "$0: performing replisync fix:" 1>&2
#sed -i -e 's#^.*deactivate_replisync.*$#deactivate_replisync: 1#' /nemo-all/etc/nemo-analyse/fishtank/nemo.conf
sed -i -e 's#^.*deactivate_replisync.*$#deactivate_replisync: 1#' "$MYNEMO_DOCKER_INNER_INST_DIR/etc/nemo-analyse/fishtank/nemo.conf"
docker restart "nemo${DIDCLFS}fishtank${DIDCLFS}1"
echo

# add vsmd instance entry for 'vsmd1' in nemo db within inner nemo detection mitigated container (corresponds with stuff done by ./mynemo-mitigation-init-vsmd-certs.sh)
echo "$0: in nemo-detection inner mitigated container: adding 'vsmd1' entry in nemo db" 1>&2
#cp -f /nemo-all/create_vsmd1.py /nemo-all/etc/nemo-erkennung/mitigated/ # TODO: currently misuse of shared fs
cp -f "$MYNEMO_DOCKER_INNER_INST_DIR/create_vsmd1.py" "$MYNEMO_DOCKER_INNER_INST_DIR/etc/nemo-erkennung/mitigated/" # TODO: currently misuse of shared fs
docker exec -ti "nemo${DIDCLFS}mitigated${DIDCLFS}1" python3 /services/etc/nemo/create_vsmd1.py

##


