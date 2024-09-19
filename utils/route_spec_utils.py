
#

import os
import re

from django.conf import settings
from ipaddress import *

#

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "celery_flow_spec_utils.log", False)

##

PROTOCOL_NUMBERS = {
    'HOPOPT': '0',
    'ICMP': '1',
    'IGMP': '2',
    'GGP': '3',
    'IPv4': '4',
    'ST': '5',
    'TCP': '6',
    'CBT': '7',
    'EGP': '8',
    'IGP': '9',
    'BBN-RCC-MON': '10',
    'NVP-II': '11',
    'PUP': '12',
    'ARGUS': '13',
    'EMCON': '14',
    'XNET': '15',
    'CHAOS': '16',
    'UDP': '17',
    'MUX': '18',
    'DCN-MEAS': '19',
    'HMP': '20',
    'PRM': '21',
    'XNS-IDP': '22',
    'TRUNK-1': '23',
    'TRUNK-2': '24',
    'LEAF-1': '25',
    'LEAF-2': '26',
    'RDP': '27',
    'IRTP': '28',
    'ISO-TP4': '29',
    'NETBLT': '30',
    'MFE-NSP': '31',
    'MERIT-INP': '32',
    'DCCP': '33',
    '3PC': '34',
    'IDPR': '35',
    'XTP': '36',
    'DDP': '37',
    'IDPR-CMTP': '38',
    'TP++': '39',
    'IL': '40',
    'IPv6': '41',
    'SDRP': '42',
    'IPv6-Route': '43',
    'IPv6-Frag ': '44',
    'IDRP': '45',
    'RSVP': '46',
    'GRE': '47',
    'DSR': '48',
    'BNA': '49',
    'ESP': '50',
    'AH': '51',
    'I-NLSP': '52',
    'SWIPE': '53',
    'NARP': '54',
    'MOBILE': '55',
    'TLSP': '56',
    'SKIP': '57',
    'IPv6-ICMP': '58',
    'IPv6-NoNxt': '59',
    'IPv6-Opts': '60',
    'CFTP': '62',
    'SAT-EXPAK': '64',
    'KRYPTOLAN': '65',
    'RVD': '66',
    'IPPC': '67',
    'SAT-MON': '69',
    'VISA': '70',
    'IPCV': '71',
    'CPNX': '72',
    'CPHB': '73',
    'WSN': '74',
    'PVP': '75',
    'BR-SAT-MON': '76',
    'SUN-ND': '77',
    'WB-MON': '78',
    'WB-EXPAK': '79',
    'ISO-IP': '80',
    'VMTP': '81',
    'SECURE-VMTP': '82',
    'VINES': '83',
    'TTP': '84',
    'IPTM': '84',
    'NSFNET-IGP': '85',
    'DGP': '86',
    'TCF': '87',
    'EIGRP': '88',
    'OSPFIGP': '89',
    'Sprite-RPC': '90',
    'LARP': '91',
    'MTP': '92',
    'AX.25': '93',
    'IPIP': '94',
    'MICP': '95',
    'SCC-SP': '96',
    'ETHERIP': '97',
    'ENCAP': '98',
    'GMTP': '100',
    'IFMP': '101',
    'PNNI': '102',
    'PIM': '103',
    'ARIS': '104',
    'SCPS': '105',
    'QNX': '106',
    'A/N': '107',
    'IPComp': '108',
    'SNP': '109',
    'Compaq-Peer': '110',
    'IPX-in-IP': '111',
    'VRRP': '112',
    'PGM': '113',
    'L2TP': '115',
    'DDX': '116',
    'IATP': '117',
    'STP': '118',
    'SRP': '119',
    'UTI': '120',
    'SMP': '121',
    'SM': '122',
    'PTP ': '123',
    'ISIS': '124',
    'FIRE': '125',
    'CRTP': '126',
    'CRUDP': '127',
    'SSCOPMCE': '128',
    'IPLT': '129',
    'SPS': '130',
    'PIPE': '131',
    'SCTP': '132',
    'FC': '133',
    'RSVP-E2E-IGNORE': '134',
    'Mobility Header': '135',
    'UDPLite': '136',
    'MPLS-in-IP': '137',
    'manet': '138',
    'HIP': '139',
    'Shim6': '140',
    'WESP': '141',
    'ROHC': '142'
}

def get_protocols_numbers(protocols_set, ip_version, output_separator=",", output_prefix='proto'):
    if protocols_set:

        protocols = output_prefix

        for protocol in protocols_set:
            if hasattr(protocol, 'protocol'):
                protocol_str = protocol.protocol
            else:
                protocol_str = protocol

            protoNo = PROTOCOL_NUMBERS.get(protocol_str.upper())

            if ip_version==6 and (protoNo==1 or protocol_str=="icmp"):
                protocols += ('=%s'+output_separator) % PROTOCOL_NUMBERS.get("IPv6-ICMP")
            elif protoNo:
                protocols += ('=%s'+output_separator) % protoNo
            else:
                protocols += ('=%s'+output_separator) % protocol_str

        return protocols
    else:
        return ''

##

def get_range(addr_range):
    if '/32' in addr_range:
        addr_range = addr_range.replace('/32', '')
    if len(addr_range.split('/')) > 1:
        mask = addr_range.split('/')[1]
    else:
        mask = False
    elements = addr_range.split('/')[0].split('.')
    if '0' in elements:
        if elements == ['0', '0', '0', '0']:
            addr_range = '0'
            if mask is not False:
                if mask != "0":
                  addr_range = '0.0.0.0'
                addr_range += '/%s' % mask
            else:
                addr_range = '0'
        elif elements[1:] == ['0', '0', '0']:
            addr_range = '.'.join(elements[:2])
            if mask is not False:
                addr_range += '/%s' % mask
        elif elements[2:] == ['0', '0']:
            addr_range = '.'.join(elements[:3])
            if mask is not False:
                addr_range += '/%s' % mask
    return addr_range + ','

##

def translate_ports(portstr, output_separator=","):
    res = []
    if portstr:
        for p in portstr.split(","):
            if "-" in p:
                # port range:
                boundary = p.split("-")
                res.append(">=" + boundary[0] + "&<=" + boundary[1])
            else:
                res.append("=" + p)
        return output_separator.join(res)
    else:
        return ""

def get_ports(rule):
    ##os.write(2, "rule.port="+str(rule.port))
    ##os.write(2, str(type(rule.port)))
    #if rule.port:
    #    #result = 'port'+translate_ports(rule.port.all())
    #    result = 'port'+translate_ports(rule.port)
    #else:
    #    result = ''
    #    if rule.destinationport:
    #        result += 'dstport' + translate_ports(rule.destinationport)
    #    if rule.sourceport:
    #        if result != '':
    #          result += ','
    #        result += 'srcport' + translate_ports(rule.sourceport)
    #if result != '':
    #   result += ','
    #return result
    return get_ports__by_attribs(rule.port, rule.destinationport, rule,sourceport)

def get_ports__by_attribs(port, destinationport, sourceport, transform_portspecs=True):
    #os.write(2, "rule.port="+str(rule.port))
    #os.write(2, str(type(rule.port)))
    #if rule.port:
    if port:
        if transform_portspecs:
          #result = 'port' + translate_ports(rule.port.all())
          #result = 'port' + translate_ports(rule.port)
          result = 'port' + translate_ports(port)
        else:
          result = 'port' + port
    else:
        result = ''
        #if rule.destinationport:
        if destinationport:
            if transform_portspecs:
              #result += 'dstport' + translate_ports(rule.destinationport)
              result += 'dstport' + translate_ports(destinationport)
            else:
              result += 'dstport' + destinationport
        #if rule.sourceport:
        if sourceport:
            if result != '':
              result += ','
            if transform_portspecs:
              #result += 'srcport' + translate_ports(rule.sourceport)
              result += 'srcport' + translate_ports(sourceport)
            else:
              result += 'srcport' + sourceport
    if result != '':
       result += ','
    return result

##

def translate_frag(fragment_string): #TODO get number mapping right, order matters!
    if fragment_string == "dont-fragment":
      result=":01";
    elif fragment_string == "first-fragment":
      result=":04";
    elif fragment_string == "is-fragment":
      result=":02";
    elif fragment_string == "last-fragment":
      result=":08";
    elif fragment_string == "not-a-fragment":
      result="!:02";
    else:
      #result="00" # TODO
      result=str(fragment_string) # TODO
    return result

def translate_frag_list(frag_list):
    result = ",".join([translate_frag(str(frag)) for frag in frag_list]) # needs to be sorted
    return result

def get_frag(rule):
    #result=''
    #if rule.fragmenttype:
    #  tmp = translate_frag_list(rule.fragmenttype.all())
    #  if tmp != "":
    #    result = 'frag'+tmp+','
    #return result
    return get_frag__by_attribs(rule.fragmenttype.all())

def get_frag__by_attribs(fragmenttype_list):
    result=''
    if len(fragmenttype_list)>0:
      tmp = translate_frag_list(fragmenttype_list)
      if tmp != "":
        result = 'frag'+tmp+','
    return result

##

def get_rulename_by_ruleparams__generic(rule):
    # for now, keep junossnmp style ruleparams strings
    return get_rulename_by_ruleparams__junossnmp(rule)

#def create_junos_name(rule):
def get_rulename_by_ruleparams__junossnmp(rule):

    #ip_version = rule.ip_version()

    #name = ''

    ## destination
    #name += get_range(rule.destination)

    ## source
    #name += get_range(rule.source)

    ## protocols
    #protocol_spec = rule.protocol.all()
    #protocol_num = get_protocols_numbers(protocol_spec, ip_version)
    #logger.debug("get_rulename_by_ruleparams__junossnmp(): protocol_spec="+str(protocol_spec)+" protocol_num="+str(protocol_num))

    #name += protocol_num

    ## ports
    #name += get_ports(rule)

    ##frag = ''
    #name += get_frag(rule)

    #if name[-1] == ',':
    #    name = name[:-1]

    #return name
  
    fragmenttype_defined = rule.fragmenttype
    if fragmenttype_defined:
      fragmenttype_list = rule.fragmenttype.all()
    else:
      fragmenttype_list = []

    return get_rulename_by_ruleparams__generic_by_rule_attribs(rule.ip_version(), rule.destination, rule.source, rule.protocol.all(), rule.port, rule.destinationport, rule.sourceport, fragmenttype_list, transform_portspecs=True)


# for now, keep junossnmp style ruleparams string format
def get_rulename_by_ruleparams__generic_by_rule_attribs(ip_version, ip_destination, ip_source, protocols_spec, ports_spec, destinationports_spec, sourceports_spec, fragmenttype_list, transform_portspecs=True):

    name = ''

    # destination
    name += get_range(ip_destination)

    # source
    name += get_range(ip_source)

    # protocols
    protocol_num = get_protocols_numbers(protocols_spec, ip_version)
    logger.debug("get_rulename_by_ruleparams__generic_by_rule_attribs(): [format:junossnmp] protocol_spec="+str(protocols_spec)+" protocol_num="+str(protocol_num))

    name += protocol_num

    # ports
    name += get_ports__by_attribs(ports_spec, destinationports_spec, sourceports_spec, transform_portspecs=transform_portspecs)

    #frag = ''
    name += get_frag__by_attribs(fragmenttype_list)

    if name[-1] == ',':
        name = name[:-1]

    return name

##

# Example : Dest:192.168.0.1/32,Source:192.168.50.2/32,Proto:=1 
#
# AFI: {{ afi }}
# Flow :Dest:{{ dest_net }}/{{ dest_mask }},Source:{{ source_net }}/{{ source_mask }},Proto:={{ proto }},DPort:={{ dport }},SPort:={{ sport }}
#  Actions                : discard
#
# currently generic_rulespec_by_params is still same as junos snmp rule specs for junos firewall mib
def translate_cisco_flow_id__to__generic_rulespec_by_params(cisco_rule_spec):
    logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): called cisco_rule_spec="+str(cisco_rule_spec))

    ret=""

    try:   

      destination_prefix=""
      source_prefix=""
      ip_proto_spec=""
      destination_port_spec=""
      source_port_spec=""
      frag_spec=""

      spec_parts = cisco_rule_spec.split(",")
      for spec_part in spec_parts:
        logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): loop spec_part="+str(spec_part))

        if spec_part.startswith("Dest:"):
          logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): case1")
          rest_spec = spec_part[len("Dest:"):]
          logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): cisco_rule_spec="+str(cisco_rule_spec)+" => dest rest_spec="+str(rest_spec))
          destination_prefix = rest_spec
        elif spec_part.startswith("Source:"):
          logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): case2")
          rest_spec = spec_part[len("Source:"):]
          logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): cisco_rule_spec="+str(cisco_rule_spec)+" => source rest_spec="+str(rest_spec))
          source_prefix = rest_spec
        elif spec_part.startswith("Proto:="):
          logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): case3")
          rest_spec = spec_part[len("Proto:="):]
          logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): cisco_rule_spec="+str(cisco_rule_spec)+" => proto rest_spec="+str(rest_spec))
          ip_proto_spec=rest_spec
        elif spec_part.startswith("DPort:"):
          logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): case4")
          rest_spec = spec_part[len("DPort:"):]
          logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): cisco_rule_spec="+str(cisco_rule_spec)+" => dport rest_spec="+str(rest_spec))
          rest_spec = translate_cisco_flow_id_portspec__to__generic_rulespec_by_params_portspec(rest_spec)
          logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): => rest_spec="+str(rest_spec))

          destination_port_spec = rest_spec
        elif spec_part.startswith("SPort:"):
          logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): case5")
          rest_spec = spec_part[len("SPort:"):]
          logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): cisco_rule_spec="+str(cisco_rule_spec)+" => sport rest_spec="+str(rest_spec))
          rest_spec = translate_cisco_flow_id_portspec__to__generic_rulespec_by_params_portspec(rest_spec)
          logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): => rest_spec="+str(rest_spec))

          source_port_spec = rest_spec

      ##

      logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): => destination_prefix="+str(destination_prefix))
      logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): => source_prefix="+str(source_prefix))

      destination_prefix_obj = ip_network(destination_prefix, strict=False)
      source_prefix_obj = ip_network(source_prefix, strict=False)

      #destination_prefix2 = str(destination_prefix_obj)
      #source_prefix2 = str(source_prefix_obj)
      #logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): => destination_prefix_obj="+str(destination_prefix_obj))
      #logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): => source_prefix_obj="+str(source_prefix_obj))
      #logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): => destination_prefix2="+str(destination_prefix2))
      #logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): => source_prefix2="+str(source_prefix2))

      if destination_prefix!="":
        ip_version = destination_prefix_obj.version 
      elif source_prefix!="":
        ip_version = source_prefix_obj.version 
      else:
        ip_version = 4; # default
      
      logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): => ip_version="+str(ip_version))

      ret = get_rulename_by_ruleparams__generic_by_rule_attribs(ip_version, destination_prefix, source_prefix, ip_proto_spec, "", destination_port_spec, source_port_spec, frag_spec, transform_portspecs=False) # TODO
   
    except Exception as e:
      logger.error("translate_cisco_flow_id__to__generic_rulespec_by_params(): got exception: "+str(e))

    logger.info("translate_cisco_flow_id__to__generic_rulespec_by_params(): => ret="+str(ret))

    return ret

    #regexp = re.compile(r"^(Dest:(:*)/([0-9]+))?,Source:(.*)/([0-9]+),Proto:=(.*),DPort:=(.*),SPort:=(.*)$")
    #r = re.match(regexp, s)
    #if r:
    ##    res = []
    ##    pranges = s.split(",")
    ##    for pr in pranges:
    ##        ports = pr.split("-")
    ##        if len(ports) == 1:
    ##            res.append(ports[0])
    ##        elif len(ports) == 2:
    ##            res += [ str(i) for i in range(int(ports[0]), int(ports[1]) + 1) ]
    ##    return res
    #else:
    #    return None

def translate_cisco_flow_id_portspec__to__generic_rulespec_by_params_portspec(rest_spec):
          rest_spec = rest_spec.replace("|", ",")

          result1 = re.match(r'^(.*)([\<\>])([0-9]+)(.*$)', rest_spec)
          while result1:
            pre_str1 = result1.group(1)
            cmp_type1 = result1.group(2)
            number_part = result1.group(3)
            post_str1 = result1.group(4)
            if cmp_type1=="<":
              rest_spec = pre_str1 + "<=" + str(int(number_part)-1) + post_str1
            else:
              rest_spec = pre_str1 + ">=" + str(int(number_part)+1) + post_str1

            result1 = re.match(r'^(.*)([\<\>])([0-9]+)(.*$)', rest_spec)

          return rest_spec


##

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
  
def unify_ratelimit_value(rate_limit_value, base=1):
  
     result1 = re.match(r'^([0-9]+)([MmKkGgTtPpEeZzYy])', rate_limit_value)
     if result1:
        #print(dir(result1), file=sys.stderr)
        number_part = result1.group(1)
        unit_part = result1.group(2)
  
        num = (int(number_part) / base) * unify_ratelimit_value__unit_map[unit_part.lower()]
  
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
  

