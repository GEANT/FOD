# -*- coding: utf-8 -*- vim:fileencoding=utf-8:
# vim: tabstop=4:shiftwidth=4:softtabstop=4:expandtab

# /srv/venv/lib/python3.11/site-packages/exabgp/application/cli.py
#from exabgp.application.cli import main as exabgp_cli_main

# utils/exabgpcli.py

from django.conf import settings
from utils.exabgpcli import exabgp_interaction
import utils.route_spec_utils as route_spec_utils

from . import jncdevice as np
from ncclient import manager
from ncclient.transport.errors import AuthenticationError, SSHError
from ncclient.operations.rpc import RPCError
from lxml import etree as ET
from django.conf import settings
import logging, os
from django.core.cache import cache
import redis
from celery.exceptions import TimeLimitExceeded, SoftTimeLimitExceeded
from .portrange import parse_portrange
import traceback
from ipaddress import ip_network
from .flowspec_utils import map__ip_proto__for__ip_version__to_flowspec
#import xml.etree.ElementTree as ET
import re
import sys
import requests

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "celery_exabpg.log", False)

#print("loading proxy_exabgp", file=sys.stderr)

cwd = os.getcwd()

class Applier(object):
  def __init__(self, route_objects=[], route_object=None, route_object_original=None, route_objects_all=[]):
    logger.info("proxy_exabgp_remote::Applier::__init__")
    self.route_object = route_object
    self.route_objects = route_objects
    self.route_object_original = route_object_original
    self.route_objects_all = route_objects_all

  def apply(self, configuration=None, operation=None):
    logger.info("proxy_exabgp_remote::apply(): called operation="+str(operation))
    
    exapeers = os.getenv('FOD_EXABGP_NOTIFY', '').split(',')

    logger.info(f"proxy_exabgp_remote::apply(): notifying {len(exapeers)} exabgp instances")
 
    try:
      route = self.route_object
      route_objects_all = self.route_objects_all
      route_original = self.route_object_original

      status = True

      for exa in exapeers:
        logger.info(f"proxy_exabgp_remote::apply(): notifying peer {exa}")

        r = requests.get(exa)
        if r.status_code == requests.codes.ok:
          status = ( status and True )
        else:
          status = False

      msg = 'hi'

      if status:
        return status, "successfully committed", msg
      else:
        return status, msg, msg

    except Exception as e:
        logger.error("proxy_exabgp_remote::apply(): got exception="+str(e), exc_info=True)
