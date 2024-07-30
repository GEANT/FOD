#!/bin/bash
#

##

./fix_nemo_detection_containers

##

if [ -e /.dockerenv ]; then # sanity check!
  systemctl disable ssh
  systemctl stop ssh
fi

##

if [ ! -f /nemo-all/secrets/vmsd1.site.crt.pem ]; then
  /nemo-all/install_vsmd_certs
fi

##

container_name="$1"
shift 1

[ -n "$container_name" ] || container_name="vsmd1"

##

docker build -f Dockerfile-vsmd1 -t "$container_name" . 

docker stop "$container_name"
docker rm "$container_name"

docker run -d \
	--privileged --network host \
	--name "$container_name" \
	--mount type=bind,source=/nemo-all/etc/,target=/nemo-all/etc/ \
	--mount type=bind,source=/nemo-all/secrets/,target=/nemo-all/secrets/ \
	"$container_name"

docker exec -ti "$container_name" ./install_and_run_vsmd

