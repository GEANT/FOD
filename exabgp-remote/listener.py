import os
import requests

from flask import Flask
from flask import render_template

app = Flask(__name__)

@app.route("/")
def trigger_config_update():
    FOD_API_URL = os.getenv('FOD_API_URL')
    FOD_API_TOKEN = os.getenv('FOD_API_TOKEN')

    url = f'{FOD_API_URL}/conf/exabgp/'
    headers = {'Authorization': f'Token {FOD_API_TOKEN}'}

    r = requests.get(url, headers=headers)
    r.raise_for_status

    output = render_template('exabgp_conf.j2',
                             flow_conf=r.text,
                             local_asn=os.getenv('LOCAL_ASN'),
                             local_ip=os.getenv('LOCAL_IP'),
                             local_nodeid=os.getenv('LOCAL_NODEID'),
                             remote_asn=os.getenv('REMOTE_ASN'),
                             remote_ip=os.getenv('REMOTE_IP'),
                             remote_nodeid=os.getenv('REMOTE_NODEID'),
                             )

    with open('/opt/exabgp/live/exabgp.conf', 'w') as file:
        file.write(output)

    # Kill the exabgp process, let supervisord restart it
    # I'd like to use SIGUSR1 to reload the config
    # but it doesn't seem to reliably withdraw removed announcements
    
    os.system("pkill -f '/usr/local/bin/exabgp /opt/exabgp/live/exabgp.conf'")

    return output
