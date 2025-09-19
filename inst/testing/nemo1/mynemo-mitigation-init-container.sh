#!/bin/bash
#

# to be called within /nemo-all/ as cwd in outer nemo-all container

##

vsmd_inbg=0
if [ "$1" = "--vsmd_inbg" -o "$1" = "--bg" ]; then 
  shift 1
  vsmd_inbg=1
fi

#

container_name="$1"
shift 1

[ -n "$container_name" ] || container_name="vsmd1"

####

# do some preparatory steps before building and starting vsmd inner container

echo "$0: running ./mynemo-mitigation-fix-detection-containers.sh" 1>&2
./mynemo-mitigation-fix-detection-containers.sh

##

# disable ssh in outer container in order to avoid conflict with ssh in vsmd container which shares the network namespace with outer container
if [ -e /.dockerenv ]; then # sanity check to really perfom following only in a container and not on the main host!
  echo "$0: disabling ssh in outer nemo-all docker container" 1>&2
  systemctl disable ssh
  systemctl stop ssh
fi

##

if [ ! -f /nemo-all/secrets/vmsd1.site.crt.pem ]; then
  echo "$0: running ./mynemo-mitigation-init-vsmd-certs.sh, as /nemo-all/secrets/vmsd1.site.crt.pem is missing" 1>&2
  ./mynemo-mitigation-init-vsmd-certs.sh
fi

####

echo "$0: creating vsmd inner docker container" 1>&2
docker build -f ./Dockerfile-vsmd1 -t "$container_name" . 

echo "$0: stopping and removing potentially leftover previously running vsmd inner docker container" 1>&2
docker stop "$container_name"
docker rm "$container_name"

echo "$0: starting new running vsmd inner docker container" 1>&2
docker run -d \
	--privileged --network host \
	--name "$container_name" \
	--mount type=bind,source=/nemo-all/etc/,target=/nemo-all/etc/ \
	--mount type=bind,source=/nemo-all/secrets/,target=/nemo-all/secrets/ \
	"$container_name"

echo "$0: setting hostname of vsmd inner docker container to 'vsmd1'" 1>&2
docker exec -ti "$container_name" hostname vsmd1

##

if [ "$vsmd_inbg" = 1 ]; then

  echo "$0: running ./mynemo-mitigation-vsmd-install-and-run --install_only inside vsmd inner container:" 1>&2
  docker exec -ti "$container_name" ./mynemo-mitigation-vsmd-install-and-run --install_only

  echo "$0: starting vsmd (in background) inside vsmd innner container:" 1>&2
  docker exec -d "$container_name" ./mynemo-mitigation-vsmd-install-and-run --run_only

  while ! docker exec -ti "$container_name" grep "Nemo instance .NemoTestinstanzVsmd1" /nemo-all/vsmd.log; do
    echo "$0: nemo detection (fishtank) not yet connected to vsmd, waiting" 1>&2
    sleep 3
  done

else

  echo "$0: running ./mynemo-mitigation-vsmd-install-and-run inside vsmd inner container (will keep running in foreground endlessly):" 1>&2
  exec docker exec -ti "$container_name" ./mynemo-mitigation-vsmd-install-and-run

fi

