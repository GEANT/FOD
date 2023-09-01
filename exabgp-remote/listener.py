import os
import requests

from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello_world():
    FOD_API_URL = os.getenv('FOD_API_URL')
    FOD_API_TOKEN = os.getenv('FOD_API_TOKEN')

    url = f'{FOD_API_URL}/conf/exabgp/'
    headers = {'Authorization': f'Token {FOD_API_TOKEN}'}

    r = requests.get(url, headers=headers)

    return r.text

