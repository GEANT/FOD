
# ./dfncert/daemon-sum-router.py
import utils.dfncert.daemon_sum_router
from utils.dfncert.daemon_sum_router import parse_arguments, load_config
from utils.dfncert.daemon_sum_router import handle_client_connections, query_router, query_router_once
from utils.dfncert.daemon_sum_router import aggregate_data, dicts_to_nokia_output

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "celery_nokiastats_dfncert.log", False)

logger.info("test1")

# adapted from utils.dfncert.daemon-sum-router:

import os
import time
import sys
import datetime
import socket
import re
import argparse
import logging
import json
import multiprocessing
import configparser
from pysros.management import connect  # Netconf
from pygnmi.client import gNMIclient  # Telemetry

#

def get_nokia_stats():
    """
    adapted from dfncert/daemon-sum-router.py :main

    //

    Return dict() of the sum of counters (bytes, packets) from all selected routes, where
    route identifier is the key in dict.  The sum is counted over all routers.
  
    Example output with one rule: {'77.72.72.1,0/0,proto=1': {'bytes': 13892216, 'packets': 165387}}
    """
    global logger
    logger.info("get_nokia_stats(): started")
    logger.info("get_nokia_stats(): started0")

    global option_debug, option_oneshot, option_raw, option_silent
    option_debug, \
        option_oneshot, \
        option_raw, \
        option_silent, \
        listen_host, \
        config_file_path = parse_arguments()
    
    logger.info("get_nokia_stats(): started1")

    
    logger.info("get_nokia_stats(): started2")

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
        #sys.exit()
        return False
    
    logger.info("get_nokia_stats(): test1")

    if not option_silent:
        print(f"Debug Mode: {option_debug}, "
              f"One-shot Mode: {option_oneshot}, "
              f"Raw Mode: {option_raw}")
    
    logger.info("get_nokia_stats(): test2")

    logging.basicConfig(level=logging.DEBUG if option_debug else logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler()
                                  if not option_silent
                                  else logging.NullHandler()])
    
    logger.info("get_nokia_stats(): test3")

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

    logger.info("get_nokia_stats(): before creating manager")
    manager = multiprocessing.Manager()

    # Create a dictionary of queues for inter-process communication
    message_queues = {router['name']: manager.Queue() for router in ROUTERS}
        
    #result = {}

    if option_oneshot:

        logger.info("get_nokia_stats(): option_oneshot")

        router_data = {router['name']: query_router_once(router) for router in ROUTERS}
        update_timestamps = {router['name']: time.time() for router in ROUTERS}
        result = make_nokia_output2(ROUTERS,
                                None,
                                router_data=router_data,
                                update_timestamps=update_timestamps,
                                dont_update=True)
    else:
    
        logger.info("get_nokia_stats(): !option_oneshot")

        # Initialize and start the server process
        server_process = multiprocessing.Process(
            target=handle_client_connections,
            args=(listen_host, ROUTERS, message_queues, result))
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

        return result

def make_nokia_output2(router_configs, data_queues, router_data=None,
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


