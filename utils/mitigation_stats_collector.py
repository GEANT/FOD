# -*- coding: utf-8 -*- vim:fileencoding=utf-8:
# vim: tabstop=4:shiftwidth=4:softtabstop=4:expandtab

# ../flowspy/settings.py.dist
# ../flowspy/settings.py
from django.conf import settings

if hasattr(settings, "MITIGATION_STATISTIC_COLLECTOR_SPECIFIC_CLASS") and settings.PROXY_CLASS == "mitigation_stats_collector_specific_junos_snmp":
  from utils import mitigation_stats_collector_specific_junos_snmp as mitigation_stats_collector_specific_class
  mitigation_stats_collector_specific = mitigation_stats_collector_specific_class.MitigationStatisticCollectorSpecific_JunosSnmp()
else: # default is junos_snmp for compatibility
  from utils import mitigation_stats_collector_specific_junos_snmp as mitigation_stats_collector_specific_class
  mitigation_stats_collector_specific = mitigation_stats_collector_specific_class.MitigationStatisticCollectorSpecific_JunosSnmp()


