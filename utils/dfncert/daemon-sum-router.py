#!/usr/bin/env python3

import os
import time
import sys
import datetime
import socket
import re
import argparse
import logging
import json
import base64
import multiprocessing
import configparser
from pysros.management import connect  # Netconf
from google.protobuf.json_format import MessageToDict  # For subscribe once of Telemetry (I miss my .get instead!)
from pygnmi.client import gNMIclient  # Telemetry

ROUTER_QUERY_SLEEP = 5
CLI_COMMAND = 'show filter ip "fSpec-0" detail'
CLI_COMMAND_V6 = 'show filter ipv6 "fSpec-0" detail'
TELEMETRY_PATH = '/state/filter/ip-filter/entry'
TELEMETRY_PATH_V6 = '/state/filter/ipv6-filter/entry'


def handle_client_connections(server_connection, router_configs, data_queues):
    """
    Handles incoming client connections and sums data from routers for output.

    Args:
    server_connection (tuple): IP address and port number tuple where the
        server will listen.
    router_configs (list): List of dictionaries containing router
        configurations.
    data_queues (dict): Dictionary mapping router names to their respective
        multiprocessing queues.

    """
    # Initialize server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(server_connection)
    server_socket.listen()
    logging.info(f"Server listening on {server_connection}")

    # Initialize router data storage
    router_data = {router['name']: {} for router in router_configs}
    update_timestamps = {router['name']: 0 for router in router_configs}

    try:
        # Accept and handle client connections indefinitely
        while True:
            client_socket, address = server_socket.accept()
            with client_socket:  # Ensure the socket is later properly closed
                logging.info(f"Connected to from {address}")
                formatted_data = make_nokia_output(
                    router_configs, data_queues, router_data, update_timestamps)
                client_socket.sendall(formatted_data.encode('utf-8'))
                client_socket.shutdown(socket.SHUT_WR)
                client_socket.close()
    finally:
        server_socket.close()


def make_nokia_output(router_configs, data_queues, router_data=None,
                      update_timestamps=None, dont_update=False):
    """
    Sums up data from routers for output and returns a Nokia Output formatted
    string

    Args:
    router_configs (list): List of dictionaries containing router
        configurations.
    data_queues (dict): Dictionary mapping router names to their respective
        multiprocessing queues.
    Optional router_data (dict): Dictionary storing current data for each
        router.
    Optional update_timestamps (dict): Dictionary storing last update
        timestamp for each router.
    Optional dont_update (bool): If True will use router_data and
        update_timestamps as provided. Otherwise will update from data_queues.

    """
    # Initialize router data storage
    if router_data is None:
        router_data = {router['name']: {} for router in router_configs}
    if update_timestamps is None:
        update_timestamps = {router['name']: 0 for router in router_configs}

    # Process data from each router's queue and update the router data dict
    if not dont_update:
        update_router_data(router_data, update_timestamps, data_queues)

    # Aggregate data from routers into a single dictionary
    aggregated_data = aggregate_data(router_data)

    formatted_data = ""
    if not option_oneshot and not option_raw:
        formatted_data = f"Last Updates: (Timestamp: {time.time()})\n"
        for rname, ts in update_timestamps.items():
            formatted_data += f"    {rname}: {ts}\n"

    # Convert data to the desired output format and send it to the client
    formatted_data += dicts_to_nokia_output(aggregated_data.values())

    return formatted_data


def update_router_data(router_data, update_timestamps, data_queues):
    """
    Updates router data from the provided queues.

    Args:
    router_data (dict): Dictionary storing current data for each router.
    update_timestamps (dict): Dictionary storing last update timestamp for each
        router.
    data_queues (dict): Queues containing new data for each router.
    """
    for router_name, queue in data_queues.items():
        latest_data = None

        # Retrieve only the latest data from the queue
        while not queue.empty():
            latest_data = queue.get()
        if latest_data is not None:
            router_data[router_name] = latest_data
            update_timestamps[router_name] = time.time()


def aggregate_data(router_data):
    """
    Aggregates router data into a single dictionary.

    Args:
    router_data (dict): Data from each router to be aggregated.

    Returns:
    dict: Aggregated data indexed by a key such as 'cisco-flow'.
    """
    data = {}
    for router_name, entries in router_data.items():
        for entry in entries:
            flow_key = entry['cisco-flow']
            if flow_key in data:
                data[flow_key]['matched_packets'] += entry['matched_packets']
                data[flow_key]['matched_bytes'] += entry['matched_bytes']
                data[flow_key]['dropped_packets'] += entry['dropped_packets']
                data[flow_key]['dropped_bytes'] += entry['dropped_bytes']
            else:
                data[flow_key] = entry
    return data


def query_router(router_info, data_queue):
    """
    Continuously queries data from a specified router's CLI and telemetry
    systems and sends the data to a processing queue.

    Args:
    router_info (dict): Information about the router, such as IP address and
        authentication details.
    data_queue (multiprocessing.Queue): Queue where the retrieved data will be
        placed.
    """
    while True:
        try:
            filter_data = query_router_once(router_info)
            data_queue.put(filter_data)
        except Exception as e:
            logging.warning(f"WARNING: Skipping router query due to exception")
            logging.exception(e)
        finally:
            time.sleep(ROUTER_QUERY_SLEEP)  # Wait some time


def query_router_once(router_info):
    """
    Query data from a specified router's CLI and telemetry systems and sends
    the data to a processing queue.

    Args:
    router_info (dict): Information about the router, such as IP address and
        authentication details.

    Returns:
    list or None: List of dicts with filter_data (Flowspec statistics)
    """
    logging.info(f"Querying router {router_info['name']}...")
    # querying CLI
    filter_data4, filter_data6 = get_router_data_from_cli(router_info)

    # querying telemetry
    telemetry_data4, telemetry_data6 = telemetry_query_data_from_router(
        router_info)  # ['update']  # [0]['val']['entry']
    telemetry_data4 = telemetry_data4['update']
    telemetry_data6 = telemetry_data6['update']
    logging.debug(f"Received IPv4 Telemetry from "
                  f"{router_info['name']}: {telemetry_data4}")
    logging.debug(f"Received IPv6 Telemetry from "
                  f"{router_info['name']}: {telemetry_data6}")

    # Update statistics with Telemetry data
    telemetry_updated_filter_data4 = []
    for d in filter_data4:
        telemetry_updated_filter_data4.append(
            telemetry_dict_updated_stats(d, telemetry_data4))

    telemetry_updated_filter_data6 = []
    for d in filter_data6:
        telemetry_updated_filter_data6.append(
            telemetry_dict_updated_stats(d, telemetry_data6))

    return telemetry_updated_filter_data4 + telemetry_updated_filter_data6


def telemetry_query_data_from_router(router):
    """
    Query data from a specified router's telemetry.

    Args:
    router_info (dict): Information about the router, such as IP address and
        authentication details.

    Returns:
    Tuple of dicts or None: Telemetry data. First entry of tuple is IPv4,
        second is IPv6.
    """

    with gNMIclient(
        target=(router['ip_address'], 57400),
        username=router['username'],
        password=router['password'],
        path_cert=router['telemetry_path_cert'],
        path_key=router['telemetry_path_key'],
        path_root=router['telemetry_path_root'],
        skip_verify=router['telemetry_skip_verify'],
        insecure=router['telemetry_insecure']
    ) as conn:
        # 4MB Limit: res = conn.get(encoding='json', path=[TELEMETRY_PATH, TELEMETRY_PATH_V6])
        # 4MB Limit: return res['notification'][0], res['notification'][1]

        sub = {
            "mode": "once",
            "encoding": "json",
            "updates_only": False,
            "subscription": [
                {"path": TELEMETRY_PATH},
                {"path": TELEMETRY_PATH_V6},
            ],
        }

        def _elems_to_xpath(elems):
            parts = []
            for e in elems:
                name = e.get("name")
                key = e.get("key", {})
                if key:
                    name += "".join(f"[{k}={key[k]}]" for k in sorted(key))
                parts.append(name)
            return "/".join(parts)

        def _full_path(prefix, path):
            pre = _elems_to_xpath(prefix.get("elem", [])) if prefix else ""
            pth = _elems_to_xpath(path.get("elem", [])) if path else ""
            return "/".join([s for s in (pre, pth) if s])

        def _entry_root_and_rel(full):
            # returns ("state/.../entry[entry-id=NNN]", ...)
            i = full.find("/entry[")
            if i == -1:
                return None, None
            j = full.find("]", i)
            if j == -1:
                return None, None
            root = full[: j + 1]
            rel = full[j + 1 :].lstrip("/")
            return root, rel

        def _decode_val(val_dict):
            # gNMI json encoding: base64 JSON in json_val :-D
            if not isinstance(val_dict, dict):
                return val_dict
            if "json_val" in val_dict:
                try:
                    return json.loads(base64.b64decode(val_dict["json_val"]))
                except Exception:
                    return val_dict["json_val"]
            # handle occasional direct string/int vals if present
            for k in ("string_val", "int_val", "uint_val", "bool_val", "float_val", "double_val"):
                if k in val_dict:
                    return val_dict[k]
            return val_dict

        # Aggregators: per-family (v4/v6) map: entry-root -> {"path": root, "val": {...}}
        v4_map, v6_map = {}, {}
        # For building 'statistics/card' lists, keep a transient "current card" per entry
        pending_card = {}  # entry-root -> dict being filled

        logging.debug("Subscribe ONCE: %s, %s", TELEMETRY_PATH, TELEMETRY_PATH_V6)

        for raw in conn.subscribe(subscribe=sub):
            msg = raw if isinstance(raw, dict) else MessageToDict(raw, preserving_proto_field_name=True)
            if msg.get("sync_response"):
                logging.debug("DEBUG: sync_response=True (snapshot complete)")
                break

            upd = msg.get("update")
            if not upd:
                continue

            prefix = upd.get("prefix", {})
            leaves = upd.get("update", [])
            pre_xpath = _elems_to_xpath(prefix.get("elem", []))

            for u in leaves:
                full = _full_path(prefix, u.get("path"))
                root, rel = _entry_root_and_rel(full)
                if not root:
                    # nothing to aggregate
                    continue

                # Classify family by path rule
                is_v6 = ("ipv6-filter" in full) or ("ipv6-filter" in pre_xpath)
                bucket = v6_map if is_v6 else v4_map

                entry = bucket.get(root)
                if not entry:
                    entry = {"path": root, "val": {}}
                    bucket[root] = entry

                val = _decode_val(u.get("val", {}))

                # Assign into the aggregated dict at the relative path
                if not rel:
                    # Path equals the entry root and value is a full object
                    if isinstance(val, dict):
                        entry["val"].update(val)
                    continue

                parts = rel.split("/")

                # Special handling: statistics/card -> list of dicts grouped by slot-number
                if len(parts) >= 2 and parts[0] == "statistics" and parts[1] == "card":
                    card = pending_card.get(root)
                    if card is None:
                        card = {}
                        pending_card[root] = card
                    leaf = parts[-1]
                    if leaf == "slot-number":
                        card["slot-number"] = val
                        # append to list
                        stats = entry["val"].setdefault("statistics", {})
                        cards = stats.setdefault("card", [])
                        # copy to avoid aliasing then reset pending
                        cards.append(dict(card))
                        pending_card[root] = {}
                    else:
                        card[leaf] = val
                    continue

                # Normal nested assignment
                d = entry["val"]
                for p in parts[:-1]:
                    d = d.setdefault(p, {})
                d[parts[-1]] = val

        notif_v4 = {"update": list(v4_map.values())}
        notif_v6 = {"update": list(v6_map.values())}
        logging.debug("Telemetry received v4 entries: %s, v6 entries: %s",
                      len(notif_v4["update"]),
                      len(notif_v6["update"]))
        return notif_v4, notif_v6


def telemetry_dict_updated_stats(filter_data, telemetry_data):
    """
    Creates a copy of filter_data with updated statistics from Telemetry data
        telemetry_data

    Args:
    filter_data (dict): Dict representing a Flowspec entries filter_data
    telemetry_data (list): List of router filter entries queried via Telemetry
    """
    newd = filter_data.copy()
    for tel in telemetry_data:
        if ('embedding' in tel['val'] and
                filter_data['entryid'] == tel['val']['embedding']['entry-id']):

            newd['stat_sources'].append(tel['path'])

            if newd['action'] == "Drop":
                # matched: ingress
                # dropped: ingress - egress
                newd['matched_packets'] += int(
                    tel['val']['statistics']['ingress-hit-pkt'])
                newd['matched_bytes'] += int(
                    tel['val']['statistics']['ingress-hit-byte'])
                newd['dropped_packets'] += int(
                    tel['val']['statistics']['ingress-hit-pkt']) - int(
                    tel['val']['statistics']['egress-hit-pkt'])
                newd['dropped_bytes'] += int(
                    tel['val']['statistics']['ingress-hit-byte']) - int(
                    tel['val']['statistics']['egress-hit-byte'])
            elif newd['action'].startswith("Rate"):
                # matched: ingress
                # dropped: ingress-rate-limiter -> dropped
                newd['matched_packets'] += int(
                    tel['val']['statistics']['ingress-hit-pkt'])
                newd['matched_bytes'] += int(
                    tel['val']['statistics']['ingress-hit-byte'])
                newd['dropped_packets'] += int(
                    tel['val']['statistics']['ingress-rate-limiter']['dropped-pkt'])
                newd['dropped_bytes'] += int(
                    tel['val']['statistics']['ingress-rate-limiter']['dropped-byte'])
            elif newd['action'].startswith("Forward"):
                # TODO VERIFY CORRECTNESS
                # Currently handles PASS (Forward) and REDIRECT (Forward (VRF))
                # matched: ingress
                # dropped: ingress - egress
                newd['matched_packets'] += int(
                    tel['val']['statistics']['ingress-hit-pkt'])
                newd['matched_bytes'] += int(
                    tel['val']['statistics']['ingress-hit-byte'])
                newd['dropped_packets'] += int(
                    tel['val']['statistics']['ingress-hit-pkt']) - int(
                    tel['val']['statistics']['egress-hit-pkt'])
                newd['dropped_bytes'] += int(
                    tel['val']['statistics']['ingress-hit-byte']) - int(
                    tel['val']['statistics']['egress-hit-byte'])

            else:
                # TODO: Same as DROP atm
                # matched: ingress
                # dropped: ingress - egress
                newd['matched_packets'] += int(
                    tel['val']['statistics']['ingress-hit-pkt'])
                newd['matched_bytes'] += int(
                    tel['val']['statistics']['ingress-hit-byte'])
                newd['dropped_packets'] += int(
                    tel['val']['statistics']['ingress-hit-pkt']) - int(
                    tel['val']['statistics']['egress-hit-pkt'])
                newd['dropped_bytes'] += int(
                    tel['val']['statistics']['ingress-hit-byte']) - int(
                    tel['val']['statistics']['egress-hit-byte'])
    return newd


def get_router_data_from_cli(router):
    """
    Fetches data from a router's CLI using the Nokia SR OS Python SDK (pysros).

    Args:
    router (dict): Information about the router, such as IP address, username,
        and password.

    Returns:
    Tuple of lists or None: List of dicts: Parsed data from the CLI output or
        None if an error occurs.  First element is IPv4 set, second element is
        IPv6 set.
    """
    try:
        # Establish a connection to the router
        connection = connect(host=router['ip_address'],
                             username=router['username'],
                             password=router['password'],
                             hostkey_verify=False)
        # Execute the CLI command
        cli4_output = connection.cli(CLI_COMMAND)
        # Optionally print the CLI command output if debugging is enabled
        logging.debug(f"Received data from '{CLI_COMMAND}' CLI call:")
        logging.debug(cli4_output)

        cli6_output = connection.cli(CLI_COMMAND_V6)
        # Optionally print the CLI command output if debugging is enabled
        logging.debug(f"Received data from '{CLI_COMMAND_V6}' CLI call:")
        logging.debug(cli6_output)

        connection.disconnect()

        # Parse the CLI output to a structured format
        return (parse_cli_filter_output(cli4_output),
                parse_cli_filter_output(cli6_output))

    except Exception as e:
        # Handle possible errors during the connection or command execution
        logging.warning(f"Failed to fetch or parse data from {router['name']} "
                     f"due to: {e}")
        if option_debug:
            raise
        else:
            pass
        return None


def parse_nokia_port_lists(cli_text):
    """
    Parses port list sections from Nokia router CLI output and returns a
    dictionary mapping list names to ports.

    The function searches for port list entries formatted in a specific way
    within the given text and extracts the port list name and the port numbers,
    which are then formatted and stored in a dictionary.

    Args:
    cli_text (str): Text output from a Nokia router's CLI.

    Returns:
    dict: A dictionary where each key is a port list name and the value is a
        string of ports associated with that name.
    """
    # Regex pattern to find port list entries
    port_list_pattern = re.compile(
        r'Port list "([^"]+)"\s*(.*?)\s*NUM ports/ranges', re.DOTALL)

    # Find all matches of the pattern in the CLI output
    port_lists = port_list_pattern.findall(cli_text)

    # Dictionary to hold the parsed port lists
    port_dict = {}

    # Process each found port list
    for name, ports in port_lists:
        # Extract numerical ranges or individual numbers and join them into a
        # single string
        port_numbers = re.findall(r'(\d+[-\d+]*)', ports)
        port_dict[name] = ', '.join(port_numbers)

    return port_dict


def value_or_none(value, nones=['n/a', 'Undefined', '0.0.0.0/0', '::/0', 'Off']):
    """
    Returns None if the given value is among the specified invalid values;
    otherwise, returns the value.

    Args:
    value (str): The value to check.
    nones (list, optional): A list of values considered invalid or None.
        Defaults to ['n/a', 'Undefined', '0.0.0.0/0', '::/0'].

    Returns:
    str or None: The original value if it is not in the invalid_values list,
        otherwise None.
    """
    return None if value in nones else value


def port_val_or_list_to_cisco_liststr(values):
    """
    Converts a single port value or a list of port values into a
    Cisco-compatible list string.

    Args:
    values (str or list): Port values to be converted (either a single string
    or a list of strings).

    Returns:
    str: A string representing the Cisco-compatible port values.
    """
    logging.debug(f"port_val_or_list_to_cisco_liststr({values})")

    if isinstance(values, list):
        converted_values = [port_val_to_cisco_val(value) for value in values]
        return "|".join(converted_values)
    return port_val_to_cisco_val(values)


def port_val_to_cisco_val(port):
    """
    Converts a single port value into Cisco format. Supports ranges and
    specific qualifiers.

    Args:
    port (str): A string representing the port value, which could be a range or
        a qualifier.

    Returns:
    str: A string representing the port value in Cisco format.
    """
    # Pattern for range of ports, converts '100-1000' to '>99&<1001'
    range_pattern = re.compile(r'(\d+)-(\d+)')

    def range_replacement(match):
        return f'>{int(match.group(1)) - 1}&<{int(match.group(2)) + 1}'
    port = range_pattern.sub(range_replacement, port)

    # Pattern for qualifiers like 'gt', 'lt', etc., converts them to their
    # respective symbols >=<
    equality_map = {'gt': '>', 'lt': '<', 'ge': '>=', 'le': '<=', 'eq': '='}
    equality_pattern = re.compile(r'\b(gt|lt|ge|le|eq)\s+(\d+)\b')

    def equality_replacement(match):
        return f'{equality_map[match.group(1)]}{match.group(2)}'
    port = equality_pattern.sub(equality_replacement, port)

    # Ensure that a plain number is prefixed with '='
    if port[0].isdigit():
        port = "=" + port

    return port


def dict_to_cisco_flow(flow_data):
    """
    Converts a dictionary of network flow data into a Cisco-compatible flow
    string format.

    Args:
    flow_data (dict): Dictionary containing keys like 'dstip', 'srcip',
    'protocol', 'dstport', and 'srcport'.

    Returns:
    str: Formatted string representing the network flow in Cisco configuration
    style.
    """
    flow_parts = []
    logging.debug(f"dict_to_cisco_flow({flow_data}):")

    # Helper function to append formatted flow data
    def append_flow_part(key, prefix, format_func=lambda x: x):
        if key in flow_data and flow_data[key] is not None:
            flow_parts.append(f"{prefix}:{format_func(flow_data[key])}")

    # Append flow parts using the helper function
    append_flow_part('dstip', 'Dest')
    append_flow_part('srcip', 'Source')
    if "ip_version" in flow_data and flow_data["ip_version"] == 6:
        # Keep Next Header instead of Protocol for IPv6
        append_flow_part('protocol', 'NH', lambda x: f"={x}")
    else:
        append_flow_part('protocol', 'Proto', lambda x: f"={x}")
    append_flow_part('dstport', 'DPort', port_val_or_list_to_cisco_liststr)
    append_flow_part('srcport', 'SPort', port_val_or_list_to_cisco_liststr)

    # Pass Fragment as-is;
    # TODO: Change to correct Nokia and Cisco identifiers for "Fragment"
    append_flow_part('fragment', 'Fragment', lambda x: f"={x}")

    # Join all parts into a single string separated by commas
    formatted_flow = ",".join(flow_parts)
    logging.debug(f"Return {formatted_flow}")
    return formatted_flow


def parse_cli_filter_output(text):
    """
    Parses the output from a CLI command that provides detailed filter
    configurations and structures it into a list of dictionaries.

    Args:
    text (str): The raw text output from the CLI command.

    Returns:
    list: A list of dictionaries, each representing an entry in the filter
        output.
    """
    # Parse port lists first to use them later in port resolution
    port_lists = parse_nokia_port_lists(text)
    logging.debug(f"Parsed port lists: {port_lists}")

    # Split the input text on each 'Entry' line to process individual entries
    entries = re.split(r'\n(?=Entry\s+:)', text)
    result = []

    for entry in entries:
        if "Entry" in entry and "Src. IP" in entry:
            entry_data = parse_entry_details(entry, port_lists)

            # Append the parsed data to the result list
            result.append(entry_data)

    return result


def dicts_to_nokia_output(routes):
    """
    Formats a list of network flow dictionaries into a string representation
    suitable for Nokia devices.

    Args:
    routes (list of dicts): Each dictionary represents a network flow with keys
        like 'cisco-flow', 'action', etc.

    Returns:
    str: A formatted string representing the network flows.
    """
    if option_raw:
        return json.dumps(list(routes))

    output = ""
    for route in routes:
        logging.debug(route)
        if 'cisco-flow' not in route:
            continue

        # TODO: ipv4
        output += f"AFI: {'IPv4' if route['ip_version'] == 4 else 'IPv6'}\n"
        output += f"Flow                     : {route['cisco-flow']}\n"
        output += f"Actions                : {nokia_action_to_dict_action(route['action'])}\n"
        output += "Synced:                 TRUE\n"  # always synced
        output += "Last Error:             0:No error\n"
        output += "Match Unsupported:      None\n"

        output += "  Statistics                     (packets/bytes)\n"
        output += f"    Matched           :      {route.get('matched_packets', 0)}/{route.get('matched_bytes', 0)}\n"
        output += f"    Dropped           :      {route.get('dropped_packets', 0)}/{route.get('dropped_bytes', 0)}\n"

    return output


def nokia_action_to_dict_action(action):
    """
    Converts Nokia action descriptions into a more generic or standardized
    format.

    Args:
    action (str): The action description from Nokia.

    Returns:
    str: A standardized action description.
    """
    if action == 'Drop':
        return 'discard'
    elif action.startswith("Rate"):
        # Converts rate limit actions to a standardized format without spaces
        # between numbers and units
        return re.sub(r'(\d+)\s*(kbps|mbps)', r'\1\2', action.lower())
    elif action == "Forward":
        return 'pass'
    elif action == "Forward (VRF)":
        return 'redirect'
    return action


def parse_entry_details(entry, port_lists):
    """
    Parses details from a single entry string.

    Args:
    entry (str): Entry string containing various network filter details.
    port_lists (dict): Dictionary of port lists parsed from the CLI output.

    Returns:
    dict: Dictionary containing parsed and formatted details from the entry.
    """
    # Regex patterns for extracting data
    # Pattern to match IP addresses with CIDR
    # ip_pattern = r'(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2})'
    ip_pattern = r'(\S+)'

    port_pattern = r'\b\d+\b'  # Matches whole numbers
    try:
        entry_data = {}
        entry_data['entryid'] = re.search(r'Entry\s+:\s+(\d+)', entry).group(1)
        entry_data['entryid'] = int(entry_data['entryid'])

        srcip_match = re.search(r'Src\. IP\s+:\s+' + ip_pattern, entry)
        entry_data['srcip'] = value_or_none(srcip_match.group(1).strip())
        entry_data['srcip'] = value_or_none(entry_data['srcip'])

        dstip_match = re.search(r'Dest\. IP\s+:\s+' + ip_pattern, entry)
        entry_data['dstip'] = value_or_none(dstip_match.group(1).strip())
        entry_data['dstip'] = value_or_none(entry_data['dstip'])

        entry_data['srcport'] = extract_port(entry,
                                             'Src\. Port\s+:\s+(.+)',
                                             port_lists)
        entry_data['dstport'] = extract_port(entry,
                                             'Dest\. Port\s+:\s+(.+)',
                                             port_lists)
        entry_data['protocol'] = re.search(r'Protocol\s+:\s+(\w+)', entry)
        if entry_data['protocol'] is None:
            # Apparently "Protocol" is "Next Header" for IPv6 for Nokia o_0
            # So if we find nothing for Protocol, let's look for Next Header
            entry_data['ip_version'] = 6
            entry_data['protocol'] = re.search(r'Next Header\s+:\s+(\w+)', entry)
            entry_data['protocol'] = entry_data['protocol'].group(1)
            entry_data['protocol'] = value_or_none(entry_data['protocol'])

            # Adding /0 for IPs
            if entry_data['srcip'] and entry_data['srcip'][-2:] != "/0": 
                entry_data['srcip'] += "/0" 
            if entry_data['dstip'] and entry_data['dstip'][-2:] != "/0": 
                entry_data['dstip'] += "/0" 
        else:
            entry_data['ip_version'] = 4
            entry_data['protocol'] = entry_data['protocol'].group(1)
            entry_data['protocol'] = value_or_none(entry_data['protocol'])

        # Fragment support with Nokia appears limited. According to
        # Unicast Routing Protocols Guide Release 22.7.R1 > BGP >
        # BGP applications > BGP FlowSpec
        # https://infocenter.nokia.com/public/7750SR227R1A/index.jsp?topic=%2Fcom.nokia.Unicast_Guide%2Fbgp_flowspec-ai9exj5yj3.html
        # SR OS limitations are for
        # IPv4: Partial. No support for matching DF bit,
        #                first-fragment or last-fragment.
        # IPv6: Partial. No support for matching Last Fragment.
        # We will pass the value directly, because we don't know
        # how it may encode the values: false, true, "first-only",
        # "non-first-only" in CLI (from nokia-conf-combined.yang)
        # TODO: Change to correct Nokia and Cisco identifiers for "Fragment"
        entry_data['fragment'] = re.search(r'Fragment\s+:\s+(\w+)', entry)
        if entry_data['fragment']:
            entry_data['fragment'] = entry_data['fragment'].group(1)
            entry_data['fragment'] = value_or_none(entry_data['fragment'])

        entry_data['matched_packets'] = 0  # TODO Placeholder
        entry_data['matched_bytes'] = 0    # TODO Placeholder
        entry_data['dropped_packets'] = 0  # TODO Placeholder
        entry_data['dropped_bytes'] = 0    # TODO Placeholder
        entry_data['stat_sources'] = ["CLI"]

        action_match = re.search(r'Primary Action\s+:\s+(.+)', entry)
        if action_match:
            entry_data['action'] = action_match.group(1).strip()

        entry_data['cisco-flow'] = dict_to_cisco_flow(entry_data)
    except Exception as e:
        logging.warning(f"WARNING: Skipping entry due to parsing exception")
        logging.debug(f"Skipping entry: '{entry}'")

        if option_debug:
            raise
        else:
            logging.exception(e)
            pass
        return {}

    logging.debug(f"parse_entry_details({entry}, {port_lists}):")
    logging.debug(f"Returns: {entry_data}")
    return entry_data


def extract_port(entry, pattern, port_lists):
    """
    Extracts port information from an entry string based on a given pattern and
    resolves port list references.

    Args:
    entry (str): Entry string to search in.
    pattern (str): Regex pattern to find the port or port list.
    port_lists (dict): Dictionary containing port list mappings.

    Returns:
    str or None: The extracted port string or None if not found.
    """
    match = re.search(pattern, entry)
    if match:
        port_info = match.group(1).strip()
        # Resolve port list reference if found
        if 'port-list' in port_info:
            port_name = port_info.replace('port-list', '').strip().strip('"')
            port_info = port_lists.get(port_name, None)
            if port_info and ", " in port_info:
                port_info = port_info.split(", ")
        return value_or_none(port_info)
    return None


def parse_arguments():
    """
    Parses command line arguments to set global configuration flags.

    Returns:
    tuple: Contains the ipv4, debug, oneshot, telemetry, raw, and silent flags
            based on the provided command line arguments.
    """
    parser = _make_parser()
    args = parser.parse_args()

    return args.debug, args.one_shot, args.raw, args.silent, \
        (args.host, args.port), args.conf


def _make_parser():
    """
    Internal function to create the command line parser object.
    """
    parser = argparse.ArgumentParser(
        description="This tool gathers statistics from one or more Nokia "
        "routers for installed Flowspec rules. If more than one router is "
        "provided it will sum the statistics to present as a single router. "
        "It supports both IPv4 and IPv6 configurations, includes a debug mode "
        "for detailed logs, a one-shot mode for a single run through the "
        "process or a daemon-mode with real-time statistics via a provided "
        "socket. It outputs these in a format similar to Cisco routers "
        "appearing as one router.",
        epilog="Copyright (C) 2024 DFN-CERT Services GmbH")

    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enable debugging mode.')
    parser.add_argument('-1', '--one-shot', action='store_true',
                        help='Run in one-shot mode instead of daemonizing and '
                        'providing a socket.')
    parser.add_argument('-r', '--raw', action='store_true',
                        help='Raw mode. Will not simulate Cisco output, but '
                        'instead return raw data.')
    parser.add_argument('-s', '--silent', action='store_true',
                        help='Silent mode. Reduce output.')
    parser.add_argument('--host', type=str, default='localhost',
                        help='Host to listen on, default: localhost')
    parser.add_argument('--port', type=int, default=12345,
                        help='Port to listen on, default: 12345')
    parser.add_argument('--conf', type=str,
                        default='/services/etc/nemo/querystats.conf',
                        help='Configuration file path, default: '
                        '/services/etc/nemo/querystats.conf')

    return parser


def load_config(file_path):
    """
    Load router configuration from a file and return a config dict and a list
    of router dictionaries.

    Example config file:

    ```
    [main]
    debug = false
    one_shot = false
    raw = false
    silent = false
    host = localhost
    port = 12345

    # List of routers
    routers = router.1, router.2

    # Configuration for router.1
    [router.1]
    netconf_port = 830
    ip_address = X
    username = user
    password = pass
    telemetry_path_cert =
    telemetry_path_key =
    telemetry_path_root =
    # insecure = false to use transport encryption tls with certificates above
    telemetry_insecure = true
    # skip_verify = true to skip certificate content verification like CN
    telemetry_skip_verify = false

    # Configuration for router.2
    [router.2]
    netconf_port = 830
    ip_address = Y
    username = user
    password = pass
    telemetry_path_cert = /path/to/certificate.pem
    telemetry_path_key = /path/to/certificate.key
    telemetry_path_root = /path/to/caroot.pem
    telemetry_insecure = false
    telemetry_skip_verify = true

    ```

    Args:
    - file_path (str): Path to the configuration file.

    Returns:
    Tuple of
    - Dict[str, Any]: List of configuration options with sane defaults.
    - List[Dict[str, Any]]: List of dictionaries, each containing router
        configuration.
    """
    config = configparser.ConfigParser()
    config.read(file_path)

    defaults = {
        'debug': config.getboolean('main', 'debug', fallback=False),
        'one_shot': config.getboolean('main', 'one_shot', fallback=False),
        'raw': config.getboolean('main', 'raw', fallback=False),
        'silent': config.getboolean('main', 'silent', fallback=False),
        'host': config.get('main', 'host', fallback='localhost'),
        'port': config.get('main', 'port', fallback='12345'),
    }

    if defaults['port']:
        defaults['port'] = int(defaults['port'])
    else:
        defaults['port'] = 12345

    routers = config.get('main', 'routers').split(', ')
    router_list = []

    for router in routers:
        router_details = {
            'name': router,
            'netconf_port': config.getint(router, 'netconf_port'),
            'ip_address': config.get(router, 'ip_address'),
            'username': config.get(router, 'username'),
            'password': config.get(router, 'password'),
            'telemetry_path_cert': config.get(router,
                                              'telemetry_path_cert',
                                              fallback=''),
            'telemetry_path_key': config.get(router,
                                             'telemetry_path_key',
                                             fallback=''),
            'telemetry_path_root': config.get(router,
                                              'telemetry_path_root',
                                              fallback=''),
            'telemetry_insecure': config.getboolean(router,
                                                    'telemetry_insecure',
                                                    fallback=True),
            'telemetry_skip_verify': config.getboolean(router,
                                                       'telemetry_skip_verify',
                                                       fallback=False),
        }
        router_list.append(router_details)
    return defaults, router_list


def _listloggers():
    rootlogger = logging.getLogger()
    print(rootlogger)
    for h in rootlogger.handlers:
        print('     %s' % h)

    for nm, lgr in logging.Logger.manager.loggerDict.items():
        print('+ [%-20s] %s ' % (nm, lgr))
        if not isinstance(lgr, logging.PlaceHolder):
            for h in lgr.handlers:
                print('     %s' % h)


def main():
    """
    Main function to configure and start processes for handling router data.
    """
    global option_debug, option_oneshot, option_raw, option_silent
    option_debug, \
        option_oneshot, \
        option_raw, \
        option_silent, \
        listen_host, \
        config_file_path = parse_arguments()

    # Load configuration from the specified file
    if os.path.exists(config_file_path):
        config_read, ROUTERS = load_config(config_file_path)
        option_debug = option_debug or config_read.get('debug', False)
        option_oneshot = option_oneshot or config_read.get('one_shot',
                                                               False)
        option_raw = option_raw or config_read.get('raw', False)
        option_silent = option_silent or config_read.get('silent', False)
        listen_host = listen_host or (config_read.get('host', 'localhost'),
                                      config_read.get('port', 12345))
        config_file_path = parse_arguments()

    else:
        print(f"Error: Cannot read configuration from {config_file_path}. "
              f"Exiting.")
        sys.exit()

    if not option_silent:
        print(f"Debug Mode: {option_debug}, "
              f"One-shot Mode: {option_oneshot}, "
              f"Raw Mode: {option_raw}")

    logging.basicConfig(level=logging.DEBUG if option_debug else logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler()
                                  if not option_silent
                                  else logging.NullHandler()])

    if not option_debug:
        # Relax noisy loggers
        noisy_loggers = ['pygnmi.client',
                         'ncclient',
                         'ncclient.capabilities',
                         'ncclient.transport.session',
                         'ncclient.transport.parser',
                         'ncclient.transport.ssh',
                         'ncclient.transport.tls',
                         'ncclient.operations.rpc',
                         'ncclient.operations.edit',
                         'ncclient.manager',
                         'concurrent.futures',
                         'asyncio',
                         'grpc._cython.cygrpc',
                         'grpc._observability',
                         'grpc._common',
                         'grpc.aio._call',
                         'pygnmi']
        for logger_name in noisy_loggers:
            logger = logging.getLogger(logger_name)
            # Set to WARNING to suppress INFO messages
            logger.setLevel(logging.WARNING)
            logger.handlers.clear()
            # Add a NullHandler to suppress output
            logger.addHandler(logging.NullHandler())
    else:
        if not option_silent:
            _listloggers()

    manager = multiprocessing.Manager()

    # Create a dictionary of queues for inter-process communication
    message_queues = {router['name']: manager.Queue() for router in ROUTERS}

    if option_oneshot:
        router_data = {router['name']: query_router_once(
            router) for router in ROUTERS}
        update_timestamps = {router['name']: time.time() for router in ROUTERS}
        print(make_nokia_output(ROUTERS,
                                None,
                                router_data=router_data,
                                update_timestamps=update_timestamps,
                                dont_update=True))
    else:
        # Initialize and start the server process
        server_process = multiprocessing.Process(
            target=handle_client_connections,
            args=(listen_host, ROUTERS, message_queues))
        server_process.start()

        # Start a data query process for each router
        router_processes = [multiprocessing.Process(
            target=query_router,
            args=(router, message_queues[router['name']]))
            for router in ROUTERS]
        for process in router_processes:
            process.start()

        # Wait for all processes to complete
        server_process.join()
        for process in router_processes:
            process.join()


# def MOCK_get_router_data_from_cli(router):
#     """
#     Fetches data from a router's CLI using the Nokia SR OS Python SDK (pysros).

#     Args:
#     router (dict): Information about the router, such as IP address, username,
#         and password.

#     Returns:
#     Tuple of lists or None: List of dicts: Parsed data from the CLI output or
#         None if an error occurs.  First element is IPv4 set, second element is
#         IPv6 set.
#     """
#     data = """
# ===============================================================================
# IP Filter
# ===============================================================================
# Filter Id           : fSpec-0
# Scope               : Embedded
# Type                : Normal
# Shared Policer      : Off
# Entries             : 3 (insert By Bgp)
# Sub-Entries         : 4 (insert By Bgp)
# Description         : IPv4 BGP FlowSpec filter for the Base router
# -------------------------------------------------------------------------------
# Filter Match Criteria : IP
# -------------------------------------------------------------------------------
# Entry               : 170
# Origin              : Inserted by BGP FlowSpec
# Description         : (Not Specified)
# Log Id              : n/a
# Src. IP             : 31.31.31.31/32
# Src. Port           : gt 1024
# Dest. IP            : 32.32.32.0/24
# Dest. Port          : eq 3128
# Protocol            : 6
# Dscp                : Undefined
# ICMP Type           : Undefined                    ICMP Code      : Undefined
# Fragment            : Off                          Src Route Opt  : Off
# Sampling            : Off                          Int. Sampling  : On
# IP-Option           : 0/0                          Multiple Option: Off
# Tcp-flag            : (Not Specified)
# Option-pres         : Off
# Egress PBR          : Disabled
# Primary Action      : Drop
# Ing. Matches        : 0 pkts
# Egr. Matches        : 0 pkts
# """
#     return (parse_cli_filter_output(data), parse_cli_filter_output(""))


# def MOCK_telemetry_query_data_from_router(router):
#     return {'update': []}, {'update': []}


# get_router_data_from_cli = MOCK_get_router_data_from_cli
# telemetry_query_data_from_router = MOCK_telemetry_query_data_from_router

if __name__ == '__main__':
    main()
