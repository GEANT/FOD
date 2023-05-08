
# to build + run
# docker build -f Dockerfile.ubuntu0 -t ubuntu0 .  && docker run --privileged -p=8000:8000 -ti ubuntu0

# to enter running one:
# docker exec -ti ubuntu0 bash

FROM ubuntu:latest

RUN apt-get update -y -y 

RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y -y systemd-sysv systemd
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y -y git less man make gcc strace ltrace lsof file vim tshark tcpdump curl wget net-tools sudo psutils procps iptables iputils-ping iputils-tracepath hping3 iproute2

WORKDIR /root
COPY . /root

CMD [ "/sbin/init" ]



