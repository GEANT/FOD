# -*- coding: utf-8 -*- vim:fileencoding=utf-8:
# vim: tabstop=4:shiftwidth=4:softtabstop=4:expandtab

from django.conf import settings
from datetime import datetime, timedelta
import json
import os
import time
import re

from flowspec.models import Route
from utils.route_spec_utils import get_rulename_by_ruleparams__generic

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "celery_mitigation_statistic.log", False)

##

class MitigationStatisticCollectorSpecific_Base():
  
  # to be overriden in sub classes
  def get_new_mitigation_statistic_data(self):
     return {}
  
  # to be overriden in sub classes
  def get_statistic_data_rule_key(self, ruleobj):
     #return ruleobj.name
     return get_rulename_by_ruleparams__generic(ruleobj)
  
  ##
  
  def lock_history_file(self, wait=1, reason=""):
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
  
  def unlock_history_file(self):
      try:
        os.rmdir(settings.SNMP_TEMP_FILE+".lock") # TODO use regular file than dir
        logger.debug("unlock_history_file(): succeeded")
        return 1
      except Exception as e:
        logger.debug("unlock_history_file(): failed "+str(e))
        return 0
  
  def load_history(self):
      history = {}
      try:
          with open(settings.SNMP_TEMP_FILE, "r") as f:
              history = json.load(f)
              f.close()
      except:
          logger.info("load_history(): there is no file with SNMP historical data.")
      return history
  
  def save_history(self, history, nowstr):
      # store updated history
      tf = settings.SNMP_TEMP_FILE + "." + nowstr
      with open(tf, "w") as f:
        json.dump(history, f)
        f.close()
      os.rename(tf, settings.SNMP_TEMP_FILE)
  
  def helper_stats_store_parse_ts(self, ts_string):
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
  
  def helper_rule_ts_parse(self, ts_string):
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
  
  def unify_ratelimit_value(self, rate_limit_value):
  
     result1 = re.match(r'^([0-9]+)([MmKkGgTtPpEeZzYy])', rate_limit_value)
     if result1:
        #print(dir(result1), file=sys.stderr)
        number_part = result1.group(1)
        unit_part = result1.group(2)
  
        num = int(number_part) * self.unify_ratelimit_value__unit_map[unit_part.lower()]
  
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
  
  def helper_get_countertype_of_rule(self, ruleobj):
     xtype = self.xtype_default
     limit_rate = None
     for thenaction in ruleobj.then.all():
         if thenaction.action and thenaction.action=='rate-limit':
             limit_rate=thenaction.action_value
             xtype=str(limit_rate).upper()
     return self.unify_ratelimit_value(xtype)
  
  #
  
  def poll_mitigation_statistics(self):
    try:
      logger.debug("poll_mitigation_statistics(): polling mitigation statistics.")
  
      # first, determine current ts, before calling get_snmp_stats
      now = datetime.now()
      nowstr = now.isoformat()
      
      logger.info("poll_mitigation_statistics(): polling mitigation statistics nowstr="+str(nowstr))
  
      # get new data
      try:
        logger.debug("poll_mitigation_statistics(): before get_new_mitigation_statistic_data: nowstr="+str(nowstr))
        newdata = self.get_new_mitigation_statistic_data()
      except Exception as e:
        logger.error("poll_mitigation_statistics(): get_new_mitigation_statistic_data failed: "+str(e))
        return False
  
      if False:
        for id in newdata:
          logger.info("poll_mitigation_statistics(): newdata id="+str(id))
  
      # lock history file access
      success = self.lock_history_file(wait=1, reason="poll_mitigation_statistics()")
      if not success: 
        logger.error("poll_mitigation_statistics(): locking history file failed, aborting");
        return False
  
      # load history
      history = self.load_history()
  
      zero_measurement = { "bytes" : 0, "packets" : 0 }
      null_measurement = 0 
      null_measurement_missing = 1
  
      try:
        last_poll_no_time = history['_last_poll_no_time']
      except Exception as e:
        logger.error("poll_mitigation_statistics(): got exception while trying to access history[_last_poll_time]: "+str(e))
        last_poll_no_time=None
      logger.debug("poll_mitigation_statistics(): last_poll_no_time="+str(last_poll_no_time))
      history['_last_poll_no_time']=nowstr
  
      try:
        history_per_rule = history['_per_rule']
      except Exception as e:
        history_per_rule = {}
       
      # do actual update 
      try:
          logger.debug("poll_mitigation_statistics(): before store: nowstr="+str(nowstr)+", last_poll_no_time="+str(last_poll_no_time))
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
                  #logger.info("poll_mitigation_statistics(): reused existing rule x xtype entry:"+str(counter))
  
          # check for old rules and remove them
          toremove = []
          for rule in history:
            try:
              #if rule!='_last_poll_no_time' and rule!="_per_rule":
              if rule[:1]!='_':
                #ts = datetime.strptime(history[rule][0]["ts"], '%Y-%m-%dT%H:%M:%S.%f')
                ts = self.helper_stats_store_parse_ts(history[rule][0]["ts"])
                if ts!=None and (now - ts).total_seconds() >= settings.SNMP_REMOVE_RULES_AFTER:
                    toremove.append(rule)
            except Exception as e:
              logger.error("poll_mitigation_statistics(): old rules remove loop: rule="+str(rule)+" got exception "+str(e))
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
              xtype = self.helper_get_countertype_of_rule(ruleobj)
                          
              logger.debug("poll_mitigation_statistics(): STATISTICS_PER_RULE rule_id="+str(rule_id)+" rule_status="+str(rule_status)+" xtype="+str(xtype))
              #rule_last_updated = str(ruleobj.last_updated) # e.g. 2018-06-21 08:03:21+00:00
              #rule_last_updated = datetime.strptime(str(ruleobj.last_updated), '%Y-%m-%d %H:%M:%S+00:00') # TODO TZ offset assumed to be 00:00
              rule_last_updated = self.helper_rule_ts_parse(str(ruleobj.last_updated))
  
              if xtype==self.xtype_default:
                counter_null = {"ts": rule_last_updated.isoformat(), "value": null_measurement }
                counter_zero = {"ts": rule_last_updated.isoformat(), "value": zero_measurement }
              else:
                counter_null = {"ts": rule_last_updated.isoformat(), "value": null_measurement, "value_matched": null_measurement }
                counter_zero = {"ts": rule_last_updated.isoformat(), "value": zero_measurement, "value_matched": zero_measurement }
  
              #logger.info("poll_mitigation_statistics(): STATISTICS_PER_RULE ruleobj="+str(ruleobj))
              #logger.info("poll_mitigation_statistics(): STATISTICS_PER_RULE ruleobj.type="+str(type(ruleobj)))
              #logger.info("poll_mitigation_statistics(): STATISTICS_PER_RULE ruleobj.id="+str(rule_id))
              #logger.info("poll_mitigation_statistics(): STATISTICS_PER_RULE ruleobj.status="+rule_status)
              #flowspec_params_str=get_rulename_by_ruleparams__generic(ruleobj)
              flowspec_params_str=self.get_statistic_data_rule_key(ruleobj)
  
              logger.debug("poll_mitigation_statistics(): STATISTICS_PER_RULE flowspec_params_str="+str(flowspec_params_str))
  
              if rule_status=="ACTIVE":
                try:
                  if xtype==self.xtype_default:
                    logger.info("poll_mitigation_statistics(): 1a STATISTICS_PER_RULE rule_id="+str(rule_id)+" => flowspec_params_str="+str(flowspec_params_str))
                    val_dropped = newdata[flowspec_params_str][self.xtype_default]
                    counter = {"ts": nowstr, "value": val_dropped}
                  else:
                    logger.info("poll_mitigation_statistics(): 1b STATISTICS_PER_RULE rule_id="+str(rule_id))
  
                    try:
                      val_dropped = newdata[flowspec_params_str][self.xtype_default]
                    except Exception:
                      val_dropped = 1
  
                    try:
                      val_matched = newdata[flowspec_params_str][xtype]
  
                      logger.info("poll_mitigation_statistics(): 1b STATISTICS_PER_RULE rule_id="+str(rule_id)+" before last_matched__remember_offset_value fix: val_matched="+str(val_matched))
  
                      ##
  
                      val_matched__pkts = newdata[flowspec_params_str][xtype]["packets"]
                      val_matched__bytes = newdata[flowspec_params_str][xtype]["bytes"]
  
                      key_remember_oldmatched = str(rule_id)+".remember_oldmatched_offset"
                      try:
                        last_matched__remember_offset_value = history_per_rule[key_remember_oldmatched]["value_matched"]
                        logger.info("poll_mitigation_statistics(): 1b STATISTICS_PER_RULE rule_id="+str(rule_id)+" before last_matched__remember_offset_value fix: last_matched__remember_offset_value="+str(last_matched__remember_offset_value))
  
                        last_matched__remember_offset_value__pkts = last_matched__remember_offset_value["packets"]
                        last_matched__remember_offset_value__bytes = last_matched__remember_offset_value["bytes"]
                      except:
                        last_matched__remember_offset_value__pkts = 0
                        last_matched__remember_offset_value__bytes = 0
  
                      val_matched__pkts = val_matched__pkts + last_matched__remember_offset_value__pkts
                      val_matched__bytes = val_matched__bytes + last_matched__remember_offset_value__bytes
  
                      newdata[flowspec_params_str][xtype]["packets"] = val_matched__pkts
                      newdata[flowspec_params_str][xtype]["bytes"] = val_matched__bytes
                    
                      logger.info("poll_mitigation_statistics(): 1b STATISTICS_PER_RULE rule_id="+str(rule_id)+" after last_matched__remember_offset_value fix: val_matched="+str(val_matched))
  
                      ##
  
                    except Exception:
                      val_matched = 1
  
                    ##
  
                    counter = { "ts": nowstr, "value": val_dropped, "value_matched": val_matched }
  
                  counter_is_null = False
                except Exception as e:
                  logger.info("poll_mitigation_statistics(): 1 STATISTICS_PER_RULE: exception: rule_id="+str(rule_id)+" newdata for flowspec_params_str='"+str(flowspec_params_str)+"' missing : "+str(e))
                  counter = {"ts": nowstr, "value": null_measurement_missing }
                  counter_is_null = True
              else:
                counter = {"ts": nowstr, "value": null_measurement }
                counter_is_null = True
  
              try:
                  if not rule_id in history_per_rule:
                    if rule_status!="ACTIVE":
                      logger.debug("poll_mitigation_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" case notexisting inactive")
                      #history_per_rule[rule_id] = [counter]
                    else:
                      logger.debug("poll_mitigation_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" case notexisting active")
                      if counter_is_null:
                        history_per_rule[rule_id] = [counter_zero]
                      else:
                        history_per_rule[rule_id] = [counter, counter_zero]
                  else:
                    rec = history_per_rule[rule_id]
                    if rule_status!="ACTIVE":
                      logger.debug("poll_mitigation_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" case existing inactive")
                      rec.insert(0, counter)
                    else:
                      last_value = rec[0]
                      last_is_null = last_value==None or last_value['value'] == null_measurement
                      if last_value==None:
                        rule_newer_than_last = True
                      else:
                        last_ts = self.helper_stats_store_parse_ts(last_value['ts'])
                        rule_newer_than_last = last_ts==None or rule_last_updated > last_ts
                      logger.debug("poll_mitigation_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" rule_last_updated="+str(rule_last_updated)+", last_value="+str(last_value))
                      if last_is_null and rule_newer_than_last:
                        logger.debug("poll_mitigation_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" case existing active 11")
                        if counter_is_null:
                          rec.insert(0, counter_zero)
                        else:
                          rec.insert(0, counter_zero)
                          rec.insert(0, counter)
                      elif last_is_null and not rule_newer_than_last:
                        logger.debug("poll_mitigation_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" case existing active 10")
                        rec.insert(0, counter_zero)
                        rec.insert(0, counter)
                      elif not last_is_null and rule_newer_than_last:
                        logger.debug("poll_mitigation_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" case existing active 01")
                        if counter_is_null:
                          rec.insert(0, counter_null)
                          rec.insert(0, counter_zero)
                        else:
                          rec.insert(0, counter_null)
                          rec.insert(0, counter_zero)
                          rec.insert(0, counter)
                      elif not last_is_null and not rule_newer_than_last:
                          logger.debug("poll_mitigation_statistics(): STATISTICS_PER_RULE: rule_id="+str(rule_id)+" case existing active 00")
                          rec.insert(0, counter)
                          history_per_rule[str(rule_id)+".last"] = counter
  
                    history_per_rule[rule_id] = rec[:samplecount]
              except Exception as e:
                  logger.error("poll_mitigation_statistics(): 2 STATISTICS_PER_RULE: exception: "+str(e))
  
            history['_per_rule'] = history_per_rule
  
          # store updated history
          self.save_history(history, nowstr)
          logger.debug("poll_mitigation_statistics(): polling finished.")
  
      except Exception as e:
          #logger.error(e)
          logger.error("poll_mitigation_statistics(): polling failed. exception: "+str(e))
          logger.error("poll_mitigation_statistics(): ", exc_info=True)        
          
      self.unlock_history_file()
      logger.info("poll_mitigation_statistics(): polling end: old_nowstr="+str(nowstr)+" last_poll_no_time="+str(last_poll_no_time))
    except Exception as e:
        logger.error("poll_mitigation_statistics(): outside frame: got exception: "+str(e))
        return False
  
  def add_initial_zero_value(self, rule_id, route_obj, zero_or_null=True):
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
      history = self.load_history()
  
      try:
        history_per_rule = history['_per_rule']
      except Exception as e:
        history_per_rule = {}
  
  
      if zero_or_null:
        zero_measurement = { "bytes" : 0, "packets" : 0 }
      else:
        zero_measurement = 0
      
      #
  
      xtype = self.helper_get_countertype_of_rule(self, route_obj)
     
      if xtype==self.xtype_default:
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
          self.save_history(history, nowstr)
  
      except Exception as e:
          logger.error("add_initial_zero_value(): failure: exception: "+str(e))
  
      self.unlock_history_file()
  
  ##
  
  # workaround for rate limiting rules whose rate limit is changed while the rule is active -> old (absoluet) matched statistics value would be lost afterwards and not be counted as part of the future (absolute) matched statistics value; because the oid keys for the matched value (depending on the rate limit) in the SNMP table have changed
  #
  # to be called before the rule's rate-limit is changed on the router
  #
  # TODO; call this function on change of an active rate limit rule whose rate limit is changed: remember_oldmatched__for_changed_ratelimitrules_whileactive()
  # TODO: on decativation of the rule the remembered matched value offset set in this function has to be cleared (add new function for this and call it appropriately): clean_oldmatched__for_changed_ratelimitrules_whileactive()
  # TODO: use the remembered matched value offset in get_snmp_stats (add to matched value gathered from SNMP)
  #
  
  def remember_oldmatched__for_changed_ratelimitrules_whileactive(self, rule_id, route_obj):
      rule_id=str(rule_id)
      logger.debug("remember_oldmatched__for_changed_ratelimitrules_whileactive(): rule_id="+str(rule_id))
  
      # get new data
      now = datetime.now()
      nowstr = now.isoformat()
  
      key_last_measurement = str(rule_id)+".last"
      key_remember_oldmatched = str(rule_id)+".remember_oldmatched_offset"
  
      # lock history file access
      success = self.lock_history_file(wait=1, reason="remember_oldmatched__for_changed_ratelimitrules_whileactive("+str(rule_id)+")")
      if not success: 
        logger.error("remember_oldmatched__for_changed_ratelimitrules_whileactive(): locking history file failed, aborting");
        return False
  
      # load history
      history = self.load_history()
  
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
          self.save_history(history, nowstr)
  
      except Exception as e:
          logger.error("remember_oldmatched__for_changed_ratelimitrules_whileactive(): failure: exception: "+str(e))
  
      self.unlock_history_file()
  
  
  def clean_oldmatched__for_changed_ratelimitrules_whileactive(self, rule_id, route_obj):
      rule_id=str(rule_id)
      logger.debug("clean_oldmatched__for_changed_ratelimitrules_whileactive(): rule_id="+str(rule_id))
  
      key_remember_oldmatched = str(rule_id)+".remember_oldmatched_offset"
  
      # lock history file access
      success = self.lock_history_file(wait=1, reason="clean_oldmatched__for_changed_ratelimitrules_whileactive("+str(rule_id)+","+str(zero_or_null)+")")
      if not success: 
        logger.error("clean_oldmatched__for_changed_ratelimitrules_whileactive(): locking history file failed, aborting");
        return False
  
      # load history
      history = self.load_history()
  
      try:
        history_per_rule = history['_per_rule']
      except Exception as e:
        history_per_rule = {}
  
      try:
          history_per_rule[key_remember_oldmatched] = {}
  
          history['_per_rule'] = history_per_rule
  
          # store updated history
          self.save_history(history, nowstr)
  
      except Exception as e:
          logger.error("clean_oldmatched__for_changed_ratelimitrules_whileactive(): failure: exception: "+str(e))
  
      self.unlock_history_file()
  

