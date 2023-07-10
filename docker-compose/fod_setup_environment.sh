#!/bin/bash
set -e
if [ -e /opt/setup_ok ]; then
	exit 0
else
	cd /opt/FOD
	#./install-debian.sh --here --supervisord --setup_admin_user --setup_admin_user5 admin ${ADMIN_PASS} ${ADMIN_EMAIL} ${FOD_ORG} ${FOD_ORG_NET} --exabgp ${FOD_EXABGP_LOCAL_ID} ${FOD_EXABGP_LOCAL_IP} ${FOD_EXABGP_LOCAL_AS} ${FOD_EXABGP_REMOTE_ID} ${FOD_EXABGP_REMOTE_IP} ${FOD_EXABGP_REMOTE_AS}
	#./install-debian.sh --here__with_venv_relative --supervisord --setup_admin_user --setup_admin_user5 admin ${ADMIN_PASS} ${ADMIN_EMAIL} ${FOD_ORG} ${FOD_ORG_NET} --exabgp ${FOD_EXABGP_LOCAL_ID} ${FOD_EXABGP_LOCAL_IP} ${FOD_EXABGP_LOCAL_AS} ${FOD_EXABGP_REMOTE_ID} ${FOD_EXABGP_REMOTE_IP} ${FOD_EXABGP_REMOTE_AS}
	./install-debian.sh \
		--here__with_venv_relative --supervisord \
		--setup_admin_user --setup_admin_user5 admin ${ADMIN_PASS} ${ADMIN_EMAIL} ${FOD_ORG} ${FOD_ORG_NET} \
		--setup_test_rule --setup_test_rule5 testrtr1 10.1.10.11/32 10.2.10.12/32 1 admin \
		--exabgp ${FOD_EXABGP_LOCAL_ID} ${FOD_EXABGP_LOCAL_IP} ${FOD_EXABGP_LOCAL_AS} ${FOD_EXABGP_REMOTE_ID} ${FOD_EXABGP_REMOTE_IP} ${FOD_EXABGP_REMOTE_AS}
	/opt/FOD/venv/bin/python -m pip install exabgp
	touch /opt/setup_ok
fi
