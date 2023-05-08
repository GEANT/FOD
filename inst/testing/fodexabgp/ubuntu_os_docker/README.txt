
./mybuildrun_ubuntu0 : script to build and start an UBUNTU container runnning systemd (labelled ubuntu0), especially for installing FoD by ../fodexabgp-install/prep_fod_exabgp2_on_ubuntu.sh

1.
the login prompt appearing in the created ubuntu0 container in itself is not useful,
instead exec into the container by "docker exec -ti ubuntu0 bash" or wrapper "./myenter_ubuntu0" .

2.
all the contents of the directory where ./mybuildrun_ubuntu0 is resides and is run from will be copied to the ubuntu0 container to /root
./mybuildrun_ubuntu0 will especially copy ../fodexabgp-install/ contents to this directory before

for fodexabgp-installation,
in container cd to /root/fodexabgp-install
and run ./prep_fod_exabgp2_on_ubuntu.sh (check ./README.txt)

3.
port 8000 inside the container (gunicorn port) will be mapped to port 8000 outside the container

4.
If needed for some other purpose, feel free to adapt ./Dockerfile.ubuntu0.dockerfile and/or ./mybuildrun_ubuntu0 accordingly


