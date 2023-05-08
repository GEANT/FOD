
./ubuntu_os_docker/ : UBUNTU docker container which runs systemd inside to provide a small UBUNUTU OS, can be used to install FoD with ./fodexabgp-install/prep_fod_exabgp2_on_ubuntu.sh; not needed incase host OS is DEBIAN or UBUNUTU running systemd

./fodexabgp-install/ : contains script to install FoD exabgp version on an DEBIAN or UBUNTU OS running systemd, ./ubuntu_os_docker can be used as a base for this, if host OS is not DEBIAN or UBUNTU running systemd

./freertr-flowspec1_docker/ : freertr docker container which speaks BGP FlowSpec, which can be used for testing of FoD exabgp version

