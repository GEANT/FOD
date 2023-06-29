
from django.conf import settings

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "flowspec_utils.log", False)

#

def map__ip_proto__for__ip_version__to_flowspec(ip_version, protocol_str):
    logger.info("map__ip_proto__for__ip_version__to_flowspec(): called ip_version="+str(ip_version)+" protocol_str="+str(protocol_str))
    if ip_version==6 and protocol_str=='icmp': 
        # default for missing NETCONF_FLOWSPEC_MAP_ICMP_TO_ICMPV6 now is True
        if not hasattr(settings, 'NETCONF_FLOWSPEC_MAP_ICMP_TO_ICMPV6') or settings.NETCONF_FLOWSPEC_MAP_ICMP_TO_ICMPV6:
              protocol_str='icmp6'
    logger.info("map__ip_proto__for__ip_version__to_flowspec(): returning protocol_str="+str(protocol_str))
    return protocol_str

def map__ip_proto__for__ip_version__from_flowspec(ip_version, protocol_str):
    logger.info("map__ip_proto__for__ip_version__from_flowspec(): called ip_version="+str(ip_version)+" protocol_str="+str(protocol_str))
    if ip_version==6 and protocol_str=='icmp6': 
        # default for missing NETCONF_FLOWSPEC_MAP_ICMP_TO_ICMPV6 now is True
        if hasattr(settings, 'NETCONF_FLOWSPEC_MAP_ICMP_TO_ICMPV6') or settings.NETCONF_FLOWSPEC_MAP_ICMP_TO_ICMPV6:
              protocol_str='icmp'
    logger.info("map__ip_proto__for__ip_version__from_flowspec(): returning protocol_str="+str(protocol_str))
    return protocol_str

