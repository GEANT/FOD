
from django.conf import settings

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "celery_flow_spec_utils.log", False)

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

import os
def get_ports(rule):
    #os.write(2, "rule.port="+str(rule.port))
    #os.write(2, str(type(rule.port)))
    if rule.port:
        #result = 'port'+translate_ports(rule.port.all())
        result = 'port'+translate_ports(rule.port)
    else:
        result = ''
        if rule.destinationport:
            result += 'dstport' + translate_ports(rule.destinationport)
        if rule.sourceport:
            if result != '':
              result += ','
            result += 'srcport' + translate_ports(rule.sourceport)
    if result != '':
       result += ','
    return result

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
    result=''
    if rule.fragmenttype:
      tmp = translate_frag_list(rule.fragmenttype.all())
      if tmp != "":
        result = 'frag'+tmp+','
    return result


def get_rulename_by_ruleparams__generic(rule):
    # for now, keep junossnmp style ruleparams strings
    return get_rulename_by_ruleparams__junossnmp(rule)

#def create_junos_name(rule):
def get_rulename_by_ruleparams__junossnmp(rule):

    ip_version = rule.ip_version()

    name = ''

    # destination
    name += get_range(rule.destination)

    # source
    name += get_range(rule.source)

    # protocols
    protocol_spec = rule.protocol.all()
    protocol_num = get_protocols_numbers(protocol_spec, ip_version)
    logger.debug("get_rulename_by_ruleparams__junossnmp(): protocol_spec="+str(protocol_spec)+" protocol_num="+str(protocol_num))

    name += protocol_num

    # ports
    name += get_ports(rule)

    #frag = ''
    name += get_frag(rule)

    if name[-1] == ',':
        name = name[:-1]

    return name
