#!/bin/bash

# to be called within /nemo-all/ as cwd in outer nemo-all container

#if false; then

if docker info >/dev/null; then # make sure docker is running

  (
    cd /nemo-all/secrets/ || exit 1
    rm vmsd1.*
    CERT_HOSTNAME_FULL=vmsd1 make -f /nemo-all/nemo-outer/Makefile.vsmdcert vmsd1.site.crt.pem
  )
  
  chmod ugo+r /nemo-all/secrets/vmsd1.*
  cp -v /nemo-all/secrets/vmsd1.* /nemo-all/etc/nemo-erkennung/mitigated/
  
  #
  
  dockerid="$(docker ps | awk '/nemo\/mitigated:latest/ { print $1; exit; }')"
  echo "$0: nemo mitigated inner dockerid=$dockerid" 1>&2
  
  dockerpid="$(docker inspect "$dockerid" | awk '/"Pid"/ { sub(/,$/, ""); print $(NF); exit; }')"
  echo "$0: nemo mitigated inner dockerpid=$dockerpid" 1>&2
  
  set -xv
  cat /nemo-all/secrets/vmsd1.ca.crt.pem >> "/proc/$dockerpid/root/etc/ssl/certs/ca-certificates.crt"

  echo "172.18.0.1 vmsd1" >> "/proc/$dockerpid/root/etc/hosts"
  
  #
  
  cert_fingerprint="$(openssl x509 -in /nemo-all/secrets/vmsd1.site.crt.pem -fingerprint -noout | sed -e 's/^.*=//' -e 's/://g')"
  echo "$0: vsmd cert_fingerprint=$cert_fingerprint" 1>&2
  
  # ./nemo.conf.vsmd
  sed -i "s/\(^__FINGERPRINT__\)\(.*$\)/\\1\\2\\n$cert_fingerprint\\2/" /services/etc/nemo/nemo.conf
  
  cp /nemo-all/nemo-outer/nemo-mitigation/nemo.conf.vsmd /nemo-all/nemo-outer/nemo-mitigation/nemo.conf.vsmd.use
  sed -i "s/\(^__FINGERPRINT__\)\(.*$\)/\\1\\2\\n$cert_fingerprint\\2/" /nemo-all/nemo-outer/nemo-mitigation/nemo.conf.vsmd.use

else

  echo "$0: no (inner) docker running, init of certs towards mitigated container not possible, aborting" 1>&2

fi

