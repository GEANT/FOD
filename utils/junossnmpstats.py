# -*- coding: utf-8 -*- vim:fileencoding=utf-8:
# vim: tabstop=4:shiftwidth=4:softtabstop=4:expandtab

# Copyright (C) 2017 CESNET, a.l.e.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from pysnmp.hlapi.asyncore import *
from django.conf import settings
from datetime import datetime, timedelta
import json
import os
import time
import re

from flowspec.models import Route
from utils.route_spec_utils import create_junos_name

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "celery_snmpstats.log", False)

identoffset = len(settings.SNMP_CNTPACKETS) + 1

#

last_snmp_var_got__from__transportTarget__hash = {}

# Wait for responses or errors, submit GETNEXT requests for further OIDs
# noinspection PyUnusedLocal,PyUnusedLocal
def snmpCallback(snmpEngine, sendRequestHandle, errorIndication,
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

            last_snmp_var_got__from__transportTarget__hash[str(transportTarget)]=name

            ident = name[identoffset:]
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
                    xtype=unify_ratelimit_value(ary[0])
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


def get_snmp_stats():
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

    last_snmp_var_got__from__transportTarget__hash = {} # reset history of snmp vars seen from a router

    # Submit initial GETNEXT requests and wait for responses
    for authData, transportTarget, varBinds in targets:
        bulkCmd(snmpEngine, authData, transportTarget, ContextData(), snmp_bulk_get__non_repeaters, snmp_bulk_get__max_repetitions,
                *varBinds, **dict(cbFun=snmpCallback, cbCtx=(authData, transportTarget.transportAddr, results)))

    snmpEngine.transportDispatcher.runDispatcher()

    return results
  except Exception as e:
      logger.error("get_snmp_stats(): got exception "+str(e), exc_info=True)

def lock_history_file(wait=1, reason=""):
    first=1
    success=0
    while first or wait:
      first=0
      try:
          os.mkdir(settings.SNMP_TEMP_FILE+".lock") # TODO use regular file than dir
          logger.debug("lock_history_file(): creating lock dir succeeded (reason="+str(reason)+")")
          success=1
          return success
      except OSError as e:
          logger.error("lock_history_file(): creating lock dir failed (reason="+str(reason)+"): OSError ("+str(wait)+"): "+str(e))
          success=0
      except Exception as e:
          logger.error("lock_history_file(): lock already exists")
          logger.error("lock_history_file(): creating lock dir failed (reason="+str(reason)+"): ("+str(wait)+"): "+str(e))
          success=0
      if not success and wait:
        time.sleep(1)
    return success;

def unlock_history_file():
    try:
      os.rmdir(settings.SNMP_TEMP_FILE+".lock") # TODO use regular file than dir
      logger.debug("unlock_history_file(): succeeded")
      return 1
    except Exception as e:
      logger.debug("unlock_history_file(): failed "+str(e))
      return 0

def load_history():
    history = {}
    try:
        with open(settings.SNMP_TEMP_FILE, "r") as f:
            history = json.load(f)
            f.close()
    except:
        logger.info("There is no file with SNMP historical data.")
    return history

def save_history(history, nowstr):
    # store updated history
    tf = settings.SNMP_TEMP_FILE + "." + nowstr
    with open(tf, "w") as f:
      json.dump(history, f)
      f.close()
    os.rename(tf, settings.SNMP_TEMP_FILE)

def helper_stats_store_parse_ts(ts_string):
  try:
    ts = datetime.strptime(ts_string, '%Y-%m-%dT%H:%M:%S.%f')
  except ValueError as e:
    logger.error("helper_stats_store_parse_ts(): ts_string="+str(ts_string)+": got ValueError "+str(e))

    try:
      ts = datetime.strptime(ts_string, '%Y-%m-%dT%H:%M:%S')
    except Exception as e:
      logger.error("helper_stats_store_parse_ts(): ts_string="+str(ts_string)+": got exception "+str(e))
      ts = None

  except Exception as e:
    logger.error("helper_stats_store_parse_ts(): ts_string="+str(ts_string)+": got exception "+str(e))
    ts = None

  return ts

def helper_rule_ts_parse(ts_string):
  try:
    ts = datetime.strptime(ts_string, '%Y-%m-%d %H:%M:%S+00:00') # TODO TZ offset assumed to be 00:00
  except ValueError as e:
    #logger.info("helper_rule_ts_parse(): trying with milli seconds fmt")
    try:
      ts = datetime.strptime(ts_string, '%Y-%m-%d %H:%M:%S.%f+00:00') # TODO TZ offset assumed to be 00:00
    except Exception as e:
      logger.error("helper_rule_ts_parse(): ts_string="+str(ts_string)+": got exception "+str(type(e))+": "+str(e))
      ts = None
  except Exception as e:
    logger.error("helper_rule_ts_parse(): ts_string="+str(ts_string)+": got exception "+str(type(e))+": "+str(e))
    ts = None

  #logger.info("helper_rule_ts_parse(): => ts="+str(ts))
  return ts

#

unify_ratelimit_value__unit_map = {
           "k" : 1000,
           "m" : 1000**2,
           "g" : 1000**3,
           "t" : 1000**4,
           "p" : 1000**5,
           "e" : 1000**6,
           "z" : 1000**7,
           "y" : 1000**8,
           }

def unify_ratelimit_value(rate_limit_value):

   result1 = re.match(r'^([0-9]+)([MmKkGgTtPpEeZzYy])', rate_limit_value)
   if result1:
      #print(dir(result1), file=sys.stderr)
      number_part = result1.group(1)
      unit_part = result1.group(2)

      num = int(number_part) * unify_ratelimit_value__unit_map[unit_part.lower()]

      if num >= 1000**8 and num % 1000**8 == 0:
          ret = str(int(num / 1000**8)) + "Y"
      elif num >= 1000**7 and num % 1000**7 == 0:
          ret = str(int(num / 1000**7)) + "Z"
      elif num >= 1000**6 and num % 1000**6 == 0:
          ret = str(int(num / 1000**6)) + "E"
      elif num >= 1000**5 and num % 1000**5 == 0:
          ret = str(int(num / 1000**5)) + "P"
      elif num >= 1000**4 and num % 1000**4 == 0:
          ret = str(int(num / 1000**4)) + "T"
      elif num >= 1000**3 and num % 1000**3 == 0:
          ret = str(int(num / 1000**3)) + "G"
      elif num >= 1000**2 and num % 1000**2 == 0:
          ret = str(int(num / 1000**2)) + "M"
      elif num >= 1000 and num % 1000 == 0:
          ret = str(int(num / 1000)) + "K"

   else: # TODO: maybe warn if unknown format
     ret = rate_limit_value

   return ret


xtype_default='counter'

def helper_get_countertype_of_rule(ruleobj):
   xtype = xtype_default
   limit_rate = None
   for thenaction in ruleobj.then.all():
       if thenaction.action and thenaction.action=='rate-limit':
           limit_rate=thenaction.action_value
           xtype=str(limit_rate).upper()
   return unify_ratelimit_value(xtype)

#

def poll_snmp_statistics():
    logger.debug("poll_snmp_statistics(): polling SNMP statistics.")

    # first, determine current ts, before calling get_snmp_stats
    now = datetime.now()
    nowstr = now.isoformat()
    
    logger.info("poll_snmp_statistics(): polling SNMP statistics nowstr="+str(nowstr))

    # get new data
    try:
      logger.debug("poll_snmp_statistics(): junossnmpstats: nowstr="+str(nowstr))
      newdata = get_snmp_stats()
    except Exception as e:
      logger.error("poll_snmp_statistics(): get_snmp_stats failed: "+str(e))
      return False

    if False:
      for id in newdata:
        logger.info("poll_snmp_statistics(): newdata id="+str(id))

    # lock history file access
    success = lock_history_file(wait=1, reason="poll_snmp_statistics()")
    if not success: 
      logger.error("poll_snmp_statistics(): locking history file failed, aborting");
      return False

    # load history
    history = load_history()

    zero_measurement = { "bytes" : 0, "packets" : 0 }
    null_measurement = 0 
    null_measurement_missing = 1

    try:
      last_poll_no_time = history['_last_poll_no_time']
    except Exception as e:
      logger.error("poll_snmp_statistics(): got exception while trying to access history[_last_poll_time]: "+str(e))
      last_poll_no_time=None
    logger.debug("poll_snmp_statistics(): junossnmpstats: last_poll_no_time="+str(last_poll_no_time))
    history['_last_poll_no_time']=nowstr

    try:
      history_per_rule = history['_per_rule']
    except Exception as e:
      history_per_rule = {}
     
    # do actual update 
    try:
        logger.debug("poll_snmp_statistics(): before store: junossnmpstats: nowstr="+str(nowstr)+", last_poll_no_time="+str(last_poll_no_time))
        #newdata = get_snmp_stats()

        # proper update history
        samplecount = settings.SNMP_MAX_SAMPLECOUNT
        for rule in newdata:
          counter=None
          for xtype in newdata[rule]:
              key = "value"
              if xtype!="counter":
                  key = "value_"+str(xtype)
              if counter==None:
                #counter = {"ts": nowstr, "value": newdata[rule]['counter']}
                counter = {"ts": nowstr, key: newdata[rule][xtype]}
                if rule in history:
                    history[rule].insert(0, counter)
                    history[rule] = history[rule][:samplecount]
                else:
                    history[rule] = [counter]
              else:
                counter[key] = newdata[rule][xtype]
                #logger.info("poll_snmp_statistics(): reused existing rule x xtype entry:"+str(counter))

        # check for old rules and remove them
        toremove = []
        for rule in history:
          try:
            #if rule!='_last_poll_no_time' and rule!="_per_rule":
            if rule[:1]!='_':
              #ts = datetime.strptime(history[rule][0]["ts"], '%Y-%m-%dT%H:%M:%S.%f')
              ts = helper_stats_store_parse_ts(history[rule][0]["ts"])
              if ts!=None and (now - ts).total_seconds() >= settings.SNMP_REMOVE_RULES_AFTER:
                  toremove.append(rule)
          except Exception as e:
            logger.error("poll_snmp_statistics(): old rules remove loop: rule="+str(rule)+" got exception "+str(e))
        for rule in toremove:
            history.pop(rule, None)

        if settings.STATISTICS_PER_MATCHACTION_ADD_FINAL_ZERO == True:
          # for now workaround for low-level rules (by match params, not FoD rule id) no longer have data, typically because of haveing been deactivated
          for rule in history:
            #if rule!='_last_poll_no_time' and rule!="_per_rule":
            if rule[:1]!='_':
              ts = history[rule][0]["ts"]
              if ts!=nowstr and ts==last_poll_no_time:
                counter = {"ts": nowstr, "value": null_measurement }
                history[rule].insert(0, counter)
                history[rule] = history[rule][:samplecount]
    
        if settings.STATISTICS_PER_RULE == True:
          queryset = Route.objects.all()
          for ruleobj in queryset:
            rule_id = str(ruleobj.id)
            rule_status = str(ruleobj.status).upper()

            #xtype_default='counter'
            #xtype = xtype_default
            #limit_rate = None
            #for thenaction in ruleobj.then.all():
            #    if thenaction.action and thenaction.action=='rate-limit':
            #        limit_rate=thenaction.action_value
            #        xtype=str(limit_rate)
            xtype = helper_get_countertype_of_rule(ruleobj)
                        
            logger.debug("poll_snmp_statistics(): STATISTICS_PER_RULE rule_id="+str(rule_id)+" rule_status="+str(rule_status)+" xtype="+str(xtype))
            #rule_last_updated = str(ruleobj.last_updated) # e.g. 2018-06-21 08:03:21+00:00
            #rule_last_updated = datetime.strptime(str(ruleobj.last_updated), '%Y-%m-%d %H:%M:%S+00:00') # TODO TZ offset assumed to be 00:00
            rule_last_updated = helper_rule_ts_parse(str(ruleobj.last_updated))

            if xtype==xtype_default:
              counter_null = {"ts": rule_last_updated.isoformat(), "value": null_measurement }
              counter_zero = {"ts": rule_last_updated.isoformat(), "value": zero_measurement }
            else:
              counter_null = {"ts": rule_last_updated.isoformat(), "value": null_measurement, "value_matched": null_measurement }
              counter_zero = {"ts": rule_last_updated.isoformat(), "value": zero_measurement, "value_matched": zero_measurement }

            #logger.info("poll_snmp_statistics(): STATISTICS_PER_RULE ruleobj="+str(ruleobj))
            #logger.info("poll_snmp_statistics(): STATISTICS_PER_RULE ruleobj.type="+str(type(ruleobj)))
            #logger.info("poll_snmp_statistics(): STATISTICS_PER_RULE ruleobj.id="+str(rule_id))
            #logger.info("poll_snmp_statistics(): STATISTICS_PER_RULE ruleobj.status="+rule_status)
            flowspec_params_str=create_junos_name(ruleobj)
            logger.debug("poll_snmp_statistics(): STATISTICS_PER_RULE flowspec_params_str="+str(flowspec_params_str))

            if rule_status=="ACTIVE":
              try:
                if xtype==xtype_default:
                  logger.info("poll_snmp_statistics(): 1a STATISTICS_PER_RULE rule_id="+str(rule_id))
                  val_dropped = newdata[flowspec_params_str][xtype_default]
                  counter = {"ts": nowstr, "value": val_dropped}
                else:
                  logger.info("poll_snmp_statistics(): 1b STATISTICS_PER_RULE rule_id="+str(rule_id))

                  try:
                    val_dropped = newdata[flowspec_params_str][xtype_default]
                  except Exception:
                    val_dropped = 1

                  try:
                    val_matched = newdata[flowspec_params_str][xtype]

                    logger.info("poll_snmp_statistics(): 1b STATISTICS_PER_RULE rule_id="+str(rule_id)+" before last_matched__remember_offset_value fix: val_matched="+str(val_matched))

                    ##

                    val_matched__pkts = newdata[flowspec_params_str][xtype]["packets"]
                    val_matched__bytes = newdata[flowspec_params_str][xtype]["bytes"]

                    key_remember_oldmatched = str(rule_id)+".remember_oldmatched_offset"
                    try:
                      last_matched__remember_offset_value = history_per_rule[key_remember_oldmatched]["value_matched"]
                      logger.info("poll_snmp_statistics(): 1b STATISTICS_PER_RULE rule_id="+str(rule_id)+" before last_matched__remember_offset_value fix: last_matched__remember_offset_value="+str(last_matched__remember_offset_value))

                      last_matched__remember_offset_value__pkts = last_matched__remember_offset_value["packets"]
                      last_matched__remember_offset_value__bytes = last_matched__remember_offset_value["bytes"]
                    except:
                      last_matched__remember_offset_value__pkts = 0
                      last_matched__remember_offset_value__bytes = 0

                    val_matched__pkts = val_matched__pkts + last_matched__remember_offset_value__pkts
                    val_matched__bytes = val_matched__bytes + last_matched__remember_offset_value__bytes

                    newdata[flowspec_params_str][xtype]["packets"] = val_matched__pkts
                    newdata[flowspec_params_str][xtype]["bytes"] = val_matched__bytes
                  
                    logger.info("poll_snmp_statistics(): 1b STATISTICS_PER_RULE rule_id="+str(rule_id)+" after last_matched__remember_offset_value fix: val_matched="+str(val_matched))

                    ##

                  except Exception:
                    val_matched = 1

                  ##

                  counter = { "ts": nowstr, "value": val_dropped, "value_matched": val_matched }

                counter_is_null = False
              except Exception as e:
                logger.info("poll_snmp_statistics(): 1 STATISTICS_PER_RULE: exception: rule_id="+str(rule_id)+" newdata for flowspec_params_str='"+str(flowspec_params_str)+"' missing : "+str(e))
                counter = {"ts": nowstr, "value": null_measurement_missing }
                counter_is_null = True
            else:
              counter = {"ts": nowstr, "value": null_measurement }
              counter_is_null = True

            try:
                if not rule_id in history_per_rule:
                  if rule_status!="ACTIVE":
                    logger.debug("poll_snmp_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" case notexisting inactive")
                    #history_per_rule[rule_id] = [counter]
                  else:
                    logger.debug("poll_snmp_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" case notexisting active")
                    if counter_is_null:
                      history_per_rule[rule_id] = [counter_zero]
                    else:
                      history_per_rule[rule_id] = [counter, counter_zero]
                else:
                  rec = history_per_rule[rule_id]
                  if rule_status!="ACTIVE":
                    logger.debug("poll_snmp_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" case existing inactive")
                    rec.insert(0, counter)
                  else:
                    last_value = rec[0]
                    last_is_null = last_value==None or last_value['value'] == null_measurement
                    if last_value==None:
                      rule_newer_than_last = True
                    else:
                      last_ts = helper_stats_store_parse_ts(last_value['ts'])
                      rule_newer_than_last = last_ts==None or rule_last_updated > last_ts
                    logger.debug("poll_snmp_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" rule_last_updated="+str(rule_last_updated)+", last_value="+str(last_value))
                    if last_is_null and rule_newer_than_last:
                      logger.debug("poll_snmp_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" case existing active 11")
                      if counter_is_null:
                        rec.insert(0, counter_zero)
                      else:
                        rec.insert(0, counter_zero)
                        rec.insert(0, counter)
                    elif last_is_null and not rule_newer_than_last:
                      logger.debug("poll_snmp_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" case existing active 10")
                      rec.insert(0, counter_zero)
                      rec.insert(0, counter)
                    elif not last_is_null and rule_newer_than_last:
                      logger.debug("poll_snmp_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" case existing active 01")
                      if counter_is_null:
                        rec.insert(0, counter_null)
                        rec.insert(0, counter_zero)
                      else:
                        rec.insert(0, counter_null)
                        rec.insert(0, counter_zero)
                        rec.insert(0, counter)
                    elif not last_is_null and not rule_newer_than_last:
                        logger.debug("poll_snmp_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" case existing active 00")
                        rec.insert(0, counter)
                        history_per_rule[str(rule_id)+".last"] = counter

                  history_per_rule[rule_id] = rec[:samplecount]
            except Exception as e:
                logger.error("poll_snmp_statistics(): 2 STATISTICS_PER_RULE: exception: "+str(e))

          history['_per_rule'] = history_per_rule

        # store updated history
        save_history(history, nowstr)
        logger.debug("poll_snmp_statistics(): polling finished.")

    except Exception as e:
        #logger.error(e)
        logger.error("poll_snmp_statistics(): polling failed. exception: "+str(e))
        logger.error("poll_snmp_statistics(): ", exc_info=True)        
        
    unlock_history_file()
    logger.info("poll_snmp_statistics(): polling end: old_nowstr="+str(nowstr)+" last_poll_no_time="+str(last_poll_no_time))

def add_initial_zero_value(rule_id, route_obj, zero_or_null=True):
    rule_id=str(rule_id)
    logger.debug("add_initial_zero_value(): rule_id="+str(rule_id))

    # get new data
    now = datetime.now()
    nowstr = now.isoformat()

    # lock history file access
    success = lock_history_file(wait=1, reason="add_initial_zero_value("+str(rule_id)+","+str(zero_or_null)+")")
    if not success: 
      logger.error("add_initial_zero_value(): locking history file failed, aborting");
      return False

    # load history
    history = load_history()

    try:
      history_per_rule = history['_per_rule']
    except Exception as e:
      history_per_rule = {}


    if zero_or_null:
      zero_measurement = { "bytes" : 0, "packets" : 0 }
    else:
      zero_measurement = 0
    
    #

    xtype = helper_get_countertype_of_rule(route_obj)
   
    if xtype==xtype_default:
      counter = {"ts": nowstr, "value": zero_measurement }
    else:
      counter = {"ts": nowstr, "value": zero_measurement, "value_matched": zero_measurement }
        
    samplecount = settings.SNMP_MAX_SAMPLECOUNT

    try:
        if rule_id in history_per_rule:
              logger.error("add_initial_zero_value(): rule_id="+str(rule_id)+" : already in hist");
              rec = history_per_rule[rule_id]
              last_rec = rec[0]
              if last_rec==None or (zero_or_null and last_rec['value']==0) or ((not zero_or_null) and last_rec['value']!=0):
                rec.insert(0, counter)
                history_per_rule[rule_id] = rec[:samplecount]
        else:
              logger.error("add_initial_zero_value(): rule_id="+str(rule_id)+" : missing in hist");
              if zero_or_null:
                history_per_rule[rule_id] = [counter]

        history['_per_rule'] = history_per_rule

        # store updated history
        save_history(history, nowstr)

    except Exception as e:
        logger.error("add_initial_zero_value(): failure: exception: "+str(e))

    unlock_history_file()

##

# workaround for rate limiting rules whose rate limit is changed while the rule is active -> old (absoluet) matched statistics value would be lost afterwards and not be counted as part of the future (absolute) matched statistics value; because the oid keys for the matched value (depending on the rate limit) in the SNMP table have changed
#
# to be called before the rule's rate-limit is changed on the router
#
# TODO; call this function on change of an active rate limit rule whose rate limit is changed: remember_oldmatched__for_changed_ratelimitrules_whileactive()
# TODO: on decativation of the rule the remembered matched value offset set in this function has to be cleared (add new function for this and call it appropriately): clean_oldmatched__for_changed_ratelimitrules_whileactive()
# TODO: use the remembered matched value offset in get_snmp_stats (add to matched value gathered from SNMP)
#

def remember_oldmatched__for_changed_ratelimitrules_whileactive(rule_id, route_obj):
    rule_id=str(rule_id)
    logger.debug("remember_oldmatched__for_changed_ratelimitrules_whileactive(): rule_id="+str(rule_id))

    # get new data
    now = datetime.now()
    nowstr = now.isoformat()

    key_last_measurement = str(rule_id)+".last"
    key_remember_oldmatched = str(rule_id)+".remember_oldmatched_offset"

    # lock history file access
    success = lock_history_file(wait=1, reason="remember_oldmatched__for_changed_ratelimitrules_whileactive("+str(rule_id)+")")
    if not success: 
      logger.error("remember_oldmatched__for_changed_ratelimitrules_whileactive(): locking history file failed, aborting");
      return False

    # load history
    history = load_history()

    try:
      history_per_rule = history['_per_rule']
    except Exception as e:
      history_per_rule = {}

    try:
      last_matched__measurement_value = history_per_rule[key_last_measurement]["value_matched"]
      last_matched__measurement_value__pkts = last_matched__measurement_value["packets"]
      last_matched__measurement_value__bytes = last_matched__measurement_value["bytes"]
    except:
      last_matched__measurement_value__pkts = 0
      last_matched__measurement_value__bytes = 0

    try:
      last_matched__remember_offset_value = history_per_rule[key_remember_oldmatched]["value_matched"]
      last_matched__remember_offset_value__pkts = last_matched__remember_offset_value["packets"]
      last_matched__remember_offset_value__bytes = last_matched__remember_offset_value["bytes"]
    except:
      last_matched__remember_offset_value__pkts = 0
      last_matched__remember_offset_value__bytes = 0

    #
      
    #logger.info("remember_oldmatched__for_changed_ratelimitrules_whileactive(): last_matched__measurement_value="+str(last_matched__measurement_value)+" last_matched__remember_offset_value="+str(last_matched__remember_offset_value));

    last_matched__remember_offset_value__pkts = last_matched__remember_offset_value__pkts + last_matched__measurement_value__pkts
    last_matched__remember_offset_value__bytes = last_matched__remember_offset_value__bytes + last_matched__measurement_value__bytes

    counter = { "ts": nowstr, "value_matched": { "packets" : last_matched__remember_offset_value__pkts, "bytes" : last_matched__remember_offset_value__bytes } }
        
    try:
        history_per_rule[key_remember_oldmatched] = counter

        history['_per_rule'] = history_per_rule

        # store updated history
        save_history(history, nowstr)

    except Exception as e:
        logger.error("remember_oldmatched__for_changed_ratelimitrules_whileactive(): failure: exception: "+str(e))

    unlock_history_file()


def clean_oldmatched__for_changed_ratelimitrules_whileactive(rule_id, route_obj):
    rule_id=str(rule_id)
    logger.debug("clean_oldmatched__for_changed_ratelimitrules_whileactive(): rule_id="+str(rule_id))

    key_remember_oldmatched = str(rule_id)+".remember_oldmatched_offset"

    # lock history file access
    success = lock_history_file(wait=1, reason="clean_oldmatched__for_changed_ratelimitrules_whileactive("+str(rule_id)+","+str(zero_or_null)+")")
    if not success: 
      logger.error("clean_oldmatched__for_changed_ratelimitrules_whileactive(): locking history file failed, aborting");
      return False

    # load history
    history = load_history()

    try:
      history_per_rule = history['_per_rule']
    except Exception as e:
      history_per_rule = {}

    try:
        history_per_rule[key_remember_oldmatched] = {}

        history['_per_rule'] = history_per_rule

        # store updated history
        save_history(history, nowstr)

    except Exception as e:
        logger.error("clean_oldmatched__for_changed_ratelimitrules_whileactive(): failure: exception: "+str(e))

    unlock_history_file()


