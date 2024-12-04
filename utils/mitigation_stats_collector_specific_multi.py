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

    mitigation_stats_collector_specific1 = MitigationStatisticCollectorSpecific_Nokia()
    stats_data1 = mitigation_stats_collector_specific1.get_new_mitigation_statistic_data()


    mitigation_stats_collector_specific2 = MitigationStatisticCollectorSpecific_JunosSnmp()
    stats_data2 = mitigation_stats_collector_specific2.get_new_mitigation_statistic_data()

    # TODO: merge data 

