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
from utils.route_spec_utils import get_rulename_by_ruleparams__generic

from utils.mitigation_stats_collector_specific_base import MitigationStatisticCollectorSpecific_Base

# ./utils/dfncert/daemon-sum-router.py
#import utils.dfncert.daemon-sum-router
# ./utils/dfncert/fodadapter.py
from utils.dfncert.fodadapter import get_nokia_stats

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "celery_nokiastats.log", False)

#

class MitigationStatisticCollectorSpecific_Nokia(MitigationStatisticCollectorSpecific_Base):

  #

  # to be overriden in sub classes
  def get_new_mitigation_statistic_data(self):
    try:
      logger.info("MitigationStatisticCollectorSpecific_Nokia::get_new_mitigation_statistic_data(): before calling get_nokia_stats()")
      ret1 = get_nokia_stats()
      logger.info("MitigationStatisticCollectorSpecific_Nokia::get_new_mitigation_statistic_data(): after calling get_nokia_stats(): => ret1="+str(ret1))
      return ret1
    except Exception as e:
      logger.error("MitigationStatisticCollectorSpecific_Nokia::get_new_mitigation_statistic_data(): got exception e="+str(e))
    return {}
  
  # to be overriden in sub classes
  def get_statistic_data_rule_key(self, ruleobj):
     logger.info("MitigationStatisticCollectorSpecific_Nokia::get_statistic_data_rule_key(): called ruleobj="+str(ruleobj))
     return get_rulename_by_ruleparams__generic(ruleobj)
 
