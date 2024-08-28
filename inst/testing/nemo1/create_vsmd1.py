
#echo "vsmd params to configure (in https://localhost:8000/admin/mitigate/vsmd/):"
#echo "name:     vsmd1"
#echo "url:      https://vmsd1:3236/RPC2"
#echo "cafile:   /services/etc/nemo/vmsd1.ca.crt.pem"
#echo "keyfile:  /services/etc/nemo/vmsd1.site.key.pem"
#echo "certfile: /services/etc/nemo/vmsd1.site.crt.pem"

#from nemolib.mitigate import models
#from nemoerkennung.mitigated import main

#import json
#import logging
#import argparse
import os
#import sys

#from ipaddress import ip_network
import django
import nemolib
#from nemolib import PGName
#from psycopg2.extras import DictCursor

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nemoerkennung.settings")
django.setup()

from nemolib.mitigate import models
#from nemoerkennung.mitigated import main

certfile1="/services/etc/nemo/vmsd1.site.crt.pem"
keyfile1="/services/etc/nemo/vmsd1.site.key.pem"
cafile1="/services/etc/nemo/vmsd1.ca.crt.pem"

vsmd1 = models.VSMD.objects.create(
            name="vsmd1",
            url="https://vmsd1:3236/RPC2",
            certfile=certfile1,
            keyfile=keyfile1,
            cafile=cafile1
        )

vsmd1.active_certfile = certfile1
vsmd1.active_keyfile = keyfile1
vsmd1.cafile = cafile1
vsmd1.passive_certfile = certfile1
vsmd1.passive_keyfile = keyfile1
vsmd1.use_active = True
vsmd1.save()



