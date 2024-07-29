#!/bin/sh
#

##

./fix_nemo_detection_containers

##

if [ ! -f /nemo-all/secrets/vmsd1.site.crt.pem ]; then
  /nemo-all/install_vsmd_certs
fi

##

docker build -f Dockerfile-vsmd1 -t vsmd1 . 

docker stop vsmd1
docker rm vsmd1

docker run -d \
	--privileged --network host \
	--name vsmd1 \
	--mount type=bind,source=/nemo-all/etc/,target=/nemo-all/etc/ \
	--mount type=bind,source=/nemo-all/secrets/,target=/nemo-all/secrets/ \
	vsmd1

docker exec -ti vsmd1 ./install_and_run_vsmd

