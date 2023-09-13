FROM python:3.10
LABEL maintainer="FOD"
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y && apt-get install -y locales
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=en_US.UTF-8
ENV LANG en_US.UTF-8
RUN apt-get update -y && apt-get -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' --assume-yes -fuy dist-upgrade
RUN apt-get install -y supervisor
# currently needed to check health of db container:
RUN mkdir -p /var/run/supervisor /opt/exabgp
WORKDIR /opt/exabgp
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN mkfifo /opt/exabgp/run/exabgp.{in,out}
RUN chmod 666 /opt/exabgp/run/exabgp.{in,out}

CMD supervisord -c ./fod_exabgp_supervisord.conf
