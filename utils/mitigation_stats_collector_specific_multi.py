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
from utils.mitigation_stats_collector_specific_junos_snmp import MitigationStatisticCollectorSpecific_JunosSnmp
from utils.mitigation_stats_collector_specific_nokia import MitigationStatisticCollectorSpecific_Nokia

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "celery_multistats.log", False)

#

class MitigationStatisticCollectorSpecific_Multi(MitigationStatisticCollectorSpecific_Base):

  #

  # to be overriden in sub classes
  def get_new_mitigation_statistic_data(self):
     return self.get_statistic_data__from_multiple_sources()
  
  # to be overriden in sub classes
  def get_statistic_data_rule_key(self, ruleobj):
     return get_rulename_by_ruleparams__generic(ruleobj)


  def get_statistic_data__from_multiple_sources(self):

    # TODO: run all parallel:

    try:
      mitigation_stats_collector_specific1 = MitigationStatisticCollectorSpecific_Nokia()
      stats_data1 = mitigation_stats_collector_specific1.get_new_mitigation_statistic_data()
    except Exception as e:
      logger.info("get_new_mitigation_statistic_data(): fetching stats_data1: got exception e="+str(e), exc_info=True)
    logger.info("stats_data1="+str(stats_data1))


    try:
      mitigation_stats_collector_specific2 = MitigationStatisticCollectorSpecific_JunosSnmp()
      stats_data2 = mitigation_stats_collector_specific2.get_new_mitigation_statistic_data()
    except Exception as e:
      logger.info("get_new_mitigation_statistic_data(): fetching stats_data2: got exception e="+str(e), exc_info=True)
    logger.info("stats_data2="+str(stats_data2))

    ##

    merged_stats = {}

    seen_ruleids={}
    for ruleid in stats_data1:
      stat1 = stats_data1[ruleid]
      if not (ruleid in stats_data2):
        merged = stat1 
      else:
        merged = stat1
        stat2 = stats_data2[ruleid]

        merged = {}
        for statkey in stat1:
          if statkey in stat2:

            stat1counter = stat1[statkey]
            stat2counter = stat2[statkey]
            if 'packets' in stat1counter and 'packets' in stat2counter and 'bytes' in stat1counter and 'bytes' in stat2counter:
              merged[statkey] = { 'packets' : stat1counter['packets'] + stat2counter['packets'], 'bytes' : stat1counter['bytes'] + stat2counter['bytes']  }

      merged_stats[ruleid] = merged

    for ruleid in stats_data2:
      if not (ruleid in merged_stats):
        merged_stats[ruleid] = stats_data2[ruleid]

    # TODO: only non ratelimit rules for now supported
    logger.info("=> merged_stats="+str(merged_stats))

    return merged_stats

