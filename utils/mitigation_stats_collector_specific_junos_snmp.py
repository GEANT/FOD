# -*- coding: utf-8 -*- vim:fileencoding=utf-8:
# vim: tabstop=4:shiftwidth=4:softtabstop=4:expandtab

from pysnmp.hlapi.asyncore import *
from django.conf import settings
from datetime import datetime, timedelta
import json
import os
import time
import re

from flowspec.models import Route
from utils.route_spec_utils import get_rulename_by_ruleparams__generic, unify_ratelimit_value

from utils.mitigation_stats_collector_specific_base import MitigationStatisticCollectorSpecific_Base

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "celery_snmpstats.log", False)

#

class MitigationStatisticCollectorSpecific_JunosSnmp(MitigationStatisticCollectorSpecific_Base):

  #

  # to be overriden in sub classes
  def get_new_mitigation_statistic_data(self):
     return self.get_snmp_stats()
  
  # to be overriden in sub classes
  def get_statistic_data_rule_key(self, ruleobj):
     return get_rulename_by_ruleparams__generic(ruleobj)
 
  #
  
  identoffset = len(settings.SNMP_CNTPACKETS) + 1
  
  #
  
  last_snmp_var_got__from__transportTarget__hash = {}
  
  # Wait for responses or errors, submit GETNEXT requests for further OIDs
  # noinspection PyUnusedLocal,PyUnusedLocal
  def snmpCallback(self, snmpEngine, sendRequestHandle, errorIndication,
            errorStatus, errorIndex, varBindTable, cbCtx):
    try:
      (authData, transportTarget, results) = cbCtx
      #logger.info('snmpCallback(): called {}'.format(transportTarget))
  
      # debug - which router replies:
      #print('%s via %s' % (authData, transportTarget))
  
      try:
          last_snmp_var_got__from__transportTarget = last_snmp_var_got__from__transportTarget[str(transportTarget)]
      except:
          last_snmp_var_got__from__transportTarget = "null"
  
      # CNTPACKETS and CNTBYTES are of the same length
      if errorIndication:
          logger.error('snmpCallback(): Bad errorIndication: transportTarget={} last_snmp_var_got__from__transportTarget={}'.format(transportTarget, last_snmp_var_got__from__transportTarget))
          return 0
      elif errorStatus:
          logger.error('snmpCallback(): Bad errorStatus: transportTarget={} last_snmp_var_got__from__transportTarget={}'.format(transportTarget, last_snmp_var_got__from__transportTarget))
          return 0
      for varBindRow in varBindTable:
          for name, val in varBindRow:
              name = str(name)
              if name.startswith(settings.SNMP_CNTPACKETS):
                  counter = "packets"
              elif name.startswith(settings.SNMP_CNTBYTES):
                  counter = "bytes"
              else:
                  logger.debug('snmpCallback(): Finished {}.'.format(transportTarget))
                  return 0
  
              self.last_snmp_var_got__from__transportTarget__hash[str(transportTarget)]=name
  
              ident = name[self.identoffset:]
              ordvals = [int(i) for i in ident.split(".")]
              # the first byte is length of table name string
              len1 = ordvals[0] + 1
              tablename = "".join([chr(i) for i in ordvals[1:len1]])
              if tablename in settings.SNMP_RULESFILTER:
                  # if the current route belongs to specified table from SNMP_RULESFILTER list,
                  # take the route identifier
                  len2 = ordvals[len1] + 1
                  routename = "".join([chr(i) for i in ordvals[len1 + 1:len1 + len2]])
  
                  #logger.info("routename="+str(routename))
                  xtype='counter'
                  if re.match(r'^[0-9]+[MmKkGgTtPpEeZzYy]_', routename):
                      ary=re.split(r'_', routename, maxsplit=1)
                      xtype=unify_ratelimit_value(ary[0], base=1)
                      routename=ary[1]
                  #logger.info("=> routename="+str(routename)+" xtype="+str(xtype))
  
                  # add value into dict
                  if routename in results:
                    if xtype in results[routename]:
                      if counter in results[routename][xtype]:
                          results[routename][xtype][counter] = results[routename][xtype][counter] + int(val)
                      else:
                          results[routename][xtype][counter] = int(val)
                    else:
                      logger.debug("snmp stats: initial add2 %s %s %s %s = %s" %(transportTarget, counter, tablename, routename, int(val)))
                      results[routename][xtype] = { counter: int(val) } 
                  else:
                      logger.debug("snmp stats: initial add1 %s %s %s %s = %s" %(transportTarget, counter, tablename, routename, int(val)))
                      results[routename] = { xtype: { counter: int(val) } }
                  logger.debug("%s %s %s %s = %s" %(transportTarget, counter, tablename, routename, int(val)))
                  
    except Exception as e:
      logger.error("snmpCallback(): got exception "+str(e), exc_info=True)
    return 1  # continue table retrieval
  
  
  def get_snmp_stats(self):
    """Return dict() of the sum of counters (bytes, packets) from all selected routes, where
    route identifier is the key in dict.  The sum is counted over all routers.
  
    Example output with one rule: {'77.72.72.1,0/0,proto=1': {'bytes': 13892216, 'packets': 165387}}
  
    This function uses SNMP_IP list, SNMP_COMMUNITY, SNMP_CNTPACKETS and
    SNMP_RULESFILTER list, all defined in settings."""
    try:
      if not isinstance(settings.SNMP_IP, list):
          settings.SNMP_IP = [settings.SNMP_IP]
  
      results = {}
      targets = []
      # prepare cmdlist
      for ip in settings.SNMP_IP:
          # get values of counters using SNMP
          if isinstance(ip, dict):
              if "port" in ip:
                  port = ip["port"]
              else:
                  port = 161
  
              if "community" in ip:
                  community = ip["community"]
              else:
                  community = settings.SNMP_COMMUNITY
              ip = ip["ip"]
          elif isinstance(ip, str):
              port = 161
              community = settings.SNMP_COMMUNITY
          else:
              raise Exception("Bad configuration of SNMP, SNMP_IP should be a list of dict or a list of str.")
  
          targets.append((CommunityData(community), UdpTransportTarget((ip, port), timeout=15, retries=1),
                          (ObjectType(ObjectIdentity(settings.SNMP_CNTPACKETS)),
                           #ObjectType(ObjectIdentity(settings.SNMP_CNTBYTES))
                           )))
  
      snmpEngine = SnmpEngine()
  
      ##
  
      try:
        snmp_bulk_get__non_repeaters = settings.SNMP_BULK_GET__NON_REPEATERS
      except Exception as e:
        snmp_bulk_get__non_repeaters = 0
  
      try:
        snmp_bulk_get__max_repetitions = settings.SNMP_BULK_GET__MAX_REPETITIONS
      except Exception as e:
        snmp_bulk_get__max_repetitions = 10
  
      self.last_snmp_var_got__from__transportTarget__hash = {} # reset history of snmp vars seen from a router
  
      # Submit initial GETNEXT requests and wait for responses
      for authData, transportTarget, varBinds in targets:
          bulkCmd(snmpEngine, authData, transportTarget, ContextData(), snmp_bulk_get__non_repeaters, snmp_bulk_get__max_repetitions,
                  *varBinds, **dict(cbFun=self.snmpCallback, cbCtx=(authData, transportTarget.transportAddr, results)))
  
      snmpEngine.transportDispatcher.runDispatcher()
  
      return results
    except Exception as e:
        logger.error("get_snmp_stats(): got exception "+str(e), exc_info=True)
  
