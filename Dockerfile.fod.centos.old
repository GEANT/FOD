
FROM centos:7

ENV LC_ALL en_US.utf8

RUN yum -y install procps

RUN mkdir -p /var/log/fod /srv
COPY . /srv/flowspy
#COPY supervisord-centos.conf /srv/flowspy/supervisord.conf

RUN rm -rf /srv/flowspy/venv/

RUN (cd /srv/flowspy; ./install-centos.sh;)

#  echo "To set environment to English, run: export LC_ALL=en_US"
#  echo "To activate virualenv: source /srv/venv/bin/activate"
#  echo "To create a user run: cd /srv/flowspy; ./manage.py createsuperuser"
#  echo "To start flowspy server: cd /srv/flowspy; ./manage.py runserver 0.0.0.0:8000"
#  echo "To start celeryd: cd /srv/flowspy; ./manage.py celeryd"

EXPOSE 8000

CMD [ "/srv/flowspy/runfod.sh" ]

