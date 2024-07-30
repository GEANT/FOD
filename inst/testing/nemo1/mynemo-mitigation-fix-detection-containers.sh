#!/bin/bash

##############################################################################

# to be fixed in outer docker container: /nemo-all/etc/*:
#[fishtank]
#deactivate_replisync: 1

# to be executed in out nemo docker container: in inside docker container mitigated or eventd :
#nemo-dbadmin add_authframeinformation INFRA "Infrastructure Protection" 0.0.0.0/0,::/0 alwaystrue

##############################################################################

set -x
docker exec -ti nemo_mitigated_1 /services/inst/nemo-erkennung/bin/nemo-dbadmin add_authframeinformation INFRA "Infrastructure Protection" 0.0.0.0/0,::/0 alwaystrue

sed -i -e 's#^.*deactivate_replisync.*$#deactivate_replisync: 1#' /nemo-all/etc/nemo-analyse/fishtank/nemo.conf
docker restart nemo_fishtank_1


