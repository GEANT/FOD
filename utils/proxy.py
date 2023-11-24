# -*- coding: utf-8 -*- vim:fileencoding=utf-8:
# vim: tabstop=4:shiftwidth=4:softtabstop=4:expandtab

from django.conf import settings

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "celery_exabpg.log", False)

logger.info(f"proxy::proxy class is {settings.PROXY_CLASS}")

if not hasattr(settings, "PROXY_CLASS") or settings.PROXY_CLASS == "proxy_netconf_junos":
  logger.info("proxy::invoking netconf junos")
  from utils import proxy_netconf_junos as PR0
elif settings.PROXY_CLASS == "proxy_exabgp":
  logger.info("proxy::invoking exabgp")
  from utils import proxy_exabgp as PR0
elif settings.PROXY_CLASS == "proxy_exabgp_remote":
  logger.info("proxy::invoking exabgp remote")
  from utils import proxy_exabgp_remote as PR0

