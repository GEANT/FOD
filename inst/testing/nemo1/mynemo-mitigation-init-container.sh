#!/bin/bash
#

# to be called within /nemo-all/ as cwd in outer nemo-all container

##

reuse_container=0
vsmd_inbg=0

docker_network_vsmd="host"
docker_network_vsmd_ip=""
docker_network_vsmd2=""
docker_network_vsmd2_ip=""
docker_network_vsmd3=""
docker_network_vsmd3_ip=""

if [ "$1" = "--docker_network_vsmd" ]; then #for user_docker_outer = false
  shift 1
  docker_network_vsmd="$1"
  shift 1
  docker_network_vsmd_ip="$1"
  shift 1
fi
if [ "$1" = "--docker_network_vsmd2" ]; then #for user_docker_outer = false
  shift 1
  docker_network_vsmd2="$1"
  shift 1
  docker_network_vsmd2_ip="$1"
  shift 1
fi
if [ "$1" = "--docker_network_vsmd3" ]; then #for user_docker_outer = false
  shift 1
  docker_network_vsmd3="$1"
  shift 1
  docker_network_vsmd3_ip="$1"
  shift 1
fi

echo "$0: docker_network_vsmd=$docker_network_vsmd ($docker_network_vsmd_ip) docker_network_vsmd2=$docker_network_vsmd2 ($docker_network_vsmd2_ip) docker_network_vsmd3=$docker_network_vsmd3 ($docker_network_vsmd3_ip)" 1>&2

if [ "$1" = "--reuse_container" ]; then 
  shift 1
  reuse_container=1
fi

if [ "$1" = "--vsmd_inbg" -o "$1" = "--bg" ]; then 
  shift 1
  vsmd_inbg=1
fi

#

container_name="$1"
shift 1

[ -n "$container_name" ] || container_name="vsmd1"

####

if [ "$reuse_container" = 0 ]; then

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

  [ -n "$MYNEMO_DOCKER_INNER_INST_DIR" ] || MYNEMO_DOCKER_INNER_INST_DIR="/nemo-all"

  add_ip_args=()
  if [ -n "$docker_network_vsmd_ip" ]; then
    add_ip_args=(--ip "$docker_network_vsmd_ip")
  fi
  
  echo "$0: starting new running vsmd inner docker container (MYNEMO_DOCKER_INNER_INST_DIR=$MYNEMO_DOCKER_INNER_INST_DIR)" 1>&2
  docker run -d \
  	--privileged \
	--network "$docker_network_vsmd" "${add_ip_args[@]}"\
  	--name "$container_name" \
  	--mount type=bind,source="$MYNEMO_DOCKER_INNER_INST_DIR/etc/,target=/nemo-all/etc/" \
  	--mount type=bind,source="$MYNEMO_DOCKER_INNER_INST_DIR/secrets/,target=/nemo-all/secrets/" \
  	--restart unless-stopped \
  	"$container_name"
 
  if [ -n "$docker_network_vsmd2" ]; then
    add_ip_args=()
    if [ -n "$docker_network_vsmd2_ip" ]; then
      add_ip_args=(--ip "$docker_network_vsmd2_ip")
    fi
    docker network connect "${add_ip_args[@]}" "$docker_network_vsmd2" "$container_name"
  fi
  if [ -n "$docker_network_vsmd3" ]; then
    add_ip_args=()
    if [ -n "$docker_network_vsmd3_ip" ]; then
      add_ip_args=(--ip "$docker_network_vsmd3_ip")
    fi
    docker network connect "${add_ip_args[@]}" "$docker_network_vsmd3" "$container_name"
  fi
  
  echo "$0: setting hostname of vsmd inner docker container to 'vsmd1'" 1>&2
  docker exec -ti "$container_name" hostname vsmd1

fi

##

if [ "$vsmd_inbg" = 1 ]; then

  echo "$0: running ./mynemo-mitigation-vsmd-install-and-run --install_only inside vsmd inner container:" 1>&2
  docker exec -ti "$container_name" ./mynemo-mitigation-vsmd-install-and-run --install_only

  echo "$0: starting vsmd (in background) inside vsmd innner container:" 1>&2
  #docker exec -d "$container_name" ./mynemo-mitigation-vsmd-install-and-run --run_only
  docker exec -d "$container_name" systemctl restart vsmd

  echo "$0: restarting inner nemo-detection mitigated container to start/resume its trials to (re)connect to vsmd:" 1>&2
  ./mynemo-detection-restart-mitigated # make sure mitigated now tries again to connect to configured vsmd1 (before if might have given up to do so after some threshold time because of vsmd1 not being setup and ready yet)

  #while ! docker exec -ti "$container_name" grep "Nemo instance .NeMoMitigationInstanceVSMD1" /nemo-all/vsmd.log; do
  while ! docker exec -ti "$container_name" grep -a "Nemo instance .NeMoMitigationInstanceVSMD1" /nemo-all/vsmd.log; do
    echo "$0: nemo detection (fishtank) not yet connected to vsmd, waiting" 1>&2
    sleep 3
  done

else

  echo "$0: running ./mynemo-mitigation-vsmd-install-and-run inside vsmd inner container (will keep running in foreground endlessly):" 1>&2
  exec docker exec -ti "$container_name" ./mynemo-mitigation-vsmd-install-and-run

fi

