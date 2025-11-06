import sys
import re

def parse_nokia_port_lists(text):
    """ Parses port list sections and returns a dictionary mapping list names to ports """
    port_list_pattern = re.compile(r'Port list "([^"]+)"\s*(.*?)\s*NUM ports/ranges', re.DOTALL)
    port_lists = port_list_pattern.findall(text)
    port_dict = {}
    for name, ports in port_lists:
        port_dict[name] = ', '.join(re.findall(r'(\d+[-\d+]*)', ports))
    return port_dict

def parse_cli_filter_output(text):
    port_lists = parse_nokia_port_lists(text)
    if debug:
        print(port_lists)
    entries = re.split(r'\n(?=Entry\s+:)', text)  # Split text on each 'Entry' line
    result = []
    
    for entry in entries:
        if "Entry" in entry:
            entry_data = {}
            entry_data['entryid'] = int(re.search(r'Entry\s+:\s+(\d+)', entry).group(1))
            entry_data['srcip'] = value_or_none(re.search(r'Src\. IP\s+:\s+([\d./]+)', entry).group(1))
            entry_data['dstip'] = value_or_none(re.search(r'Dest\. IP\s+:\s+([\d./]+)', entry).group(1))

            # Extract and resolve ports, handling both direct expressions and port-list references
            src_port_match = re.search(r'Src\. Port\s+:\s+(.+)', entry)
            if src_port_match:
                src_port = src_port_match.group(1).strip()
                # If 'port-list' is found, remove it and use the name to lookup in the dictionary
                if 'port-list' in src_port:
                    src_port = src_port.replace('port-list', '').strip().strip('"')
                    src_port = port_lists.get(src_port, None)
                    if src_port and ", " in src_port:
                        src_port = src_port.split(", ")
                entry_data['srcport'] = value_or_none(src_port)

            dest_port_match = re.search(r'Dest\. Port\s+:\s+(.+)', entry)
            if dest_port_match:
                dest_port = dest_port_match.group(1).strip()
                # If 'port-list' is found, remove it and use the name to lookup in the dictionary
                if 'port-list' in dest_port:
                    dest_port = dest_port.replace('port-list', '').strip().strip('"')
                    dest_port = port_lists.get(dest_port, None)
                    if dest_port and ", " in dest_port:
                        dest_port = dest_port.split(", ")
                entry_data['dstport'] = value_or_none(dest_port)

            entry_data['protocol'] = value_or_none(re.search(r'Protocol\s+:\s+(\w+)', entry).group(1))
            
            action_match = re.search(r'Primary Action\s+:\s+(.+)', entry)
            if action_match:
                entry_data['action'] = action_match.group(1).strip()

            entry_data['cisco-flow'] = dict_to_cisco_flow(entry_data)

            # Ing. Matches        : 0 pkts
            # Egr. Matches        : 0 pkts
            entry_data['matched_packets'] = 0  # TODO
            entry_data['matched_bytes'] = 0  # TODO
            entry_data['dropped_packets'] = 0  # TODO
            entry_data['dropped_bytes'] = 0  # TODO
            
            result.append(entry_data)
            
    return result

def in_dict_and_not_none(k, d):
    """
    Returns True if k is in dict d and is not None
    """
    return k in d and d[k] is not None

def port_val_or_list_to_cisco_liststr(v):
    if type(v) == list:
        newv = [port_val_to_cisco_val(e) for e in v]
        return "|".join(newv)
    return port_val_to_cisco_val(v)

def port_val_to_cisco_val(v):
    # 100-1000  -> >99&<1001
    # eq 100 -> =100
    # lt 100 -> <100
    range_pattern = re.compile(r'(\d+)-(\d+)')
    def range_replacement(match):
        lower_bound = int(match.group(1))
        upper_bound = int(match.group(2))
        return f'>{lower_bound - 1}&<{upper_bound + 1}'
    ports = range_pattern.sub(range_replacement, v)

    # Next, transform expressions like 'gt 100', 'lt 100', etc.
    # Map the abbreviated forms to their respective symbols
    equality_map = {
        'gt': '>',   # greater than
        'lt': '<',   # less than
        'ge': '>=',  # greater than or equal to
        'le': '<=',  # less than or equal to
        'eq': "=",   # equal
    }
    def equality_replacement(match):
        symbol = equality_map[match.group(1)]
        value = match.group(2)
        return f'{symbol}{value}'

    equality_pattern = re.compile(r'\b(gt|lt|ge|le|eq)\s+(\d+)\b')
    ports = equality_pattern.sub(equality_replacement, ports)

    # plain number, add "="
    try:
        if ports[0] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            return "=" + ports
    except:
        pass
    return ports

def dict_to_cisco_flow(d):
    """
    # CISCO Flow: Dest:10.2.2.2/32,Source:10.3.3.3/32,Proto:=6,DPort:=80|=81,SPort:>442&<445
    """
    s = ""
    comma = ""
    if in_dict_and_not_none('dstip', d):
        s += comma + "Dest:" +  d['dstip']
        comma = ","
    if in_dict_and_not_none('srcip', d):
        s += comma + "Source:" + d['srcip']
        comma = ","
    if in_dict_and_not_none('protocol', d):
        s += comma + "Proto:=" + d['protocol']
        comma = ","
    if in_dict_and_not_none('dstport', d):
        s += comma + "DPort:" + port_val_or_list_to_cisco_liststr(d['dstport'])
        comma = ","
    if in_dict_and_not_none('srcport', d):
        s += comma + "SPort:" + port_val_or_list_to_cisco_liststr(d['srcport'])
        comma = ","

    return s

def nokia_action_to_dict_action(val):
    # drop
    if val == 'Drop':
        return 'discard'

    # rate-limit
    elif val.startswith("Rate"):
        return re.sub(r'(\d+)\s*(kbps|mbps)', r'\1\2', val.lower())

    # TODO: redirect
    return val
    # TODO: redirect, rate-limit-and-redirect (unavailable on nokia)

def value_or_none(val, nones=['n/a', 'Undefined']):
    if val in nones:
        return None
    return val

def dict_to_nokia_output(d):
    for route in d:
        # Expect keys
        #   juniper-flow
        #   cisco-flow
        #   action (discard or rate-limit)
        #   rate -- if action is rate-limit
        if 'cisco-flow' not in route:
            continue
        if ipv4:  # TODO
            print("AFI: IPv4")  # TODO
        else:  # TODO
            print("AFI: IPv6")  # TODO
        print("Flow                     :" + route['cisco-flow'])

        # Cisco would output something like 
        #        Actions      :Redirect: VRF offramp Route-target: ASN2-65023:172  (bgp.1)
        # For us it's either discard or rate-limit
        print("  Actions                : " + nokia_action_to_dict_action(route['action']))
        print("  Synced:                 TRUE") # Always synced
        print("  Last Error:             0:No error")  # Do we need it? TODO?
        print("  Match Unsupported:      None")  # ?
        # Calculate depending on the action
        #   for pass, counters show 'matched', meaning passed. so matched: counters, dropped: 0
        #   for drop, counters show 'matched', meaning dropped. so matched: counters, dropped: counters
        #   for rate-limit, counters show 'matched', meaning passed. policers show the distribution btw created 'policers'
        #     so matched: counters, dropped: counter for the correct policer (several might exist for a given rule-string though, here "192.168.151.1,*").
        #     total counter is the sum of both counters (better: sum of first counter and all matching policer counters)

        # TODO
        # matched_packets = 0
        # matched_bytes = 0
        # dropped_packets = 0
        # dropped_bytes = 0
        # if route['cisco-flow'] in counter_dict_by_keys:
        #     matched_packets = counter_dict_by_keys[route['cisco-flow']]['matched_packets']
        #     matched_bytes = counter_dict_by_keys[route['cisco-flow']]['matched_bytes']            
        # if route['action'] == 'discard' and route['cisco-flow'] in counter_dict_by_keys:
        #     dropped_packets = counter_dict_by_keys[route['cisco-flow']]['matched_packets']
        #     dropped_bytes = counter_dict_by_keys[route['cisco-flow']]['matched_bytes']
        # if route['action'] in ['rate-limit', 'rate-limit-and-redirect'] and route['rate'] + "_" + route['cisco-flow'] in policer_dict_by_keys:
        #     k = route['rate'] + "_" + route['cisco-flow']
        #     dropped_packets = policer_dict_by_keys[k]['matched_packets']
        #     dropped_bytes = policer_dict_by_keys[k]['matched_bytes']
        print("  Statistics                     (packets/bytes)")
        print("    Matched           :      " + str(route['matched_packets']) + '/' + str(route['matched_bytes']))
        print("    Dropped           :      " + str(route['dropped_packets']) + "/" + str(route['dropped_bytes']))

if __name__ == '__main__':
    ipv4 = True
    debug = False
    if len(sys.argv) > 1 and sys.argv[1] in ['-6', '--ipv6']:
        ipv4 = False
    if len(sys.argv) > 1 and sys.argv[1] in ['-d', '--debug']:
        debug = True


    # Sample text block to parse
    nokia_cli_output = """
===============================================================================
IP Filter
===============================================================================
Filter Id           : fSpec-0                      
Scope               : Embedded                     
Type                : Normal                       
Shared Policer      : Off                          
Entries             : 3 (insert By Bgp)
Sub-Entries         : 4 (insert By Bgp)
Description         : IPv4 BGP FlowSpec filter for the Base router
-------------------------------------------------------------------------------
Filter Match Criteria : IP
-------------------------------------------------------------------------------
Entry               : 128
Origin              : Inserted by BGP FlowSpec
Description         : (Not Specified)
Log Id              : n/a                          
Src. IP             : 31.31.31.31/32
Src. Port           : gt 1024
Dest. IP            : 32.32.32.0/24
Dest. Port          : port-list "_tmnx_fSpec_ipv4_10_dst"
Protocol            : 6
Dscp                : Undefined                    
ICMP Type           : Undefined                    ICMP Code      : Undefined
Fragment            : Off                          Src Route Opt  : Off
Sampling            : Off                          Int. Sampling  : On
IP-Option           : 0/0                          Multiple Option: Off
Tcp-flag            : (Not Specified)
Option-pres         : Off                          
Egress PBR          : Disabled                     
Primary Action      : Rate-limit 800 kbps          
Ing. Matches        : 0 pkts
Egr. Matches        : 0 pkts
Ing. Rate-limiter
  Offered           : 0 pkts
  Forwarded         : 0 pkts
  Dropped           : 0 pkts
Egr. Rate-limiter
  Offered           : 0 pkts
  Forwarded         : 0 pkts
  Dropped           : 0 pkts
 
Entry               : 170
Origin              : Inserted by BGP FlowSpec
Description         : (Not Specified)
Log Id              : n/a                          
Src. IP             : 31.31.31.31/32
Src. Port           : gt 1024
Dest. IP            : 32.32.32.0/24
Dest. Port          : eq 3128
Protocol            : 6
Dscp                : Undefined                    
ICMP Type           : Undefined                    ICMP Code      : Undefined
Fragment            : Off                          Src Route Opt  : Off
Sampling            : Off                          Int. Sampling  : On
IP-Option           : 0/0                          Multiple Option: Off
Tcp-flag            : (Not Specified)
Option-pres         : Off                          
Egress PBR          : Disabled                     
Primary Action      : Drop                         
Ing. Matches        : 0 pkts
Egr. Matches        : 0 pkts
 
Entry               : 256
Origin              : Inserted by BGP FlowSpec
Description         : (Not Specified)
Log Id              : n/a                          
Src. IP             : 32.32.32.32/32
Src. Port           : n/a
Dest. IP            : 0.0.0.0/0
Dest. Port          : n/a
Protocol            : Undefined
Dscp                : Undefined                    
ICMP Type           : Undefined                    ICMP Code      : Undefined
Fragment            : Off                          Src Route Opt  : Off
Sampling            : Off                          Int. Sampling  : On
IP-Option           : 0/0                          Multiple Option: Off
Tcp-flag            : (Not Specified)
Option-pres         : Off                          
Egress PBR          : Disabled                     
Primary Action      : Drop                         
Ing. Matches        : 0 pkts
Egr. Matches        : 0 pkts
 
-------------------------------------------------------------------------------
Filter Match IP Prefix Lists
-------------------------------------------------------------------------------
No IP Prefix Lists
-------------------------------------------------------------------------------
Filter Match Port Lists
-------------------------------------------------------------------------------
Port list "_tmnx_fSpec_ipv4_10_dst"
    3128  8081-8087
    NUM ports/ranges: 2

    References:
        IP-filter 900 entry 228 (Dst-Port)
        IP-filter 904 entry 128 (Dst-Port)
        IP-filter fSpec-0 entry 128 (Dst-Port)
        NUM references: 3

NUM Port Lists: 1
-------------------------------------------------------------------------------
Filter Match Protocol Lists
-------------------------------------------------------------------------------
No Protocol Lists
===============================================================================
    """
    nokia_dicts = parse_cli_filter_output(nokia_cli_output)
    if debug:
        print(nokia_dicts)
    dict_to_nokia_output(nokia_dicts)
