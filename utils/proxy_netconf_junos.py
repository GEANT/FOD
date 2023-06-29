# -*- coding: utf-8 -*- vim:fileencoding=utf-8:
# vim: tabstop=4:shiftwidth=4:softtabstop=4:expandtab

# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from . import jncdevice as np
from ncclient import manager
from ncclient.transport.errors import AuthenticationError, SSHError
from ncclient.operations.rpc import RPCError
from lxml import etree as ET
from django.conf import settings
import logging, os
from django.core.cache import cache
import redis
from celery.exceptions import TimeLimitExceeded, SoftTimeLimitExceeded
from .portrange import parse_portrange
import traceback
from ipaddress import ip_network
from .flowspec_utils import map__ip_proto__for__ip_version__to_flowspec
#import xml.etree.ElementTree as ET

import sys

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "celery_netconf.log", False)

print("loading proxy_netconf_junos", file=sys.stderr)

cwd = os.getcwd()

def fod_unknown_host_cb(host, fingerprint):
    return True


class Retriever(object):
    def __init__(self, device=settings.NETCONF_DEVICE, username=settings.NETCONF_USER, password=settings.NETCONF_PASS, filter=settings.ROUTES_FILTER, port=settings.NETCONF_PORT, route_name=None, xml=None):
        self.device = device
        self.username = username
        self.password = password
        self.port = port
        self.filter = filter
        self.xml = xml
        if route_name:
            #self.filter = settings.ROUTE_FILTER%route_name
            self.filter = settings.ROUTE_FILTER.replace("%s", route_name) # allow for varying number-of, multiple instances of %s

    def supports__named_routes(self):
        return True

    # specific method for fetching raw NETCONF XML data
    def fetch_xml(self):
        with manager.connect(host=self.device, port=self.port, username=self.username, password=self.password, hostkey_verify=False) as m:
            xmlconfig = m.get_config(source='running', filter=('subtree',self.filter)).data_xml
        return xmlconfig
   
    # specific method for returning raw NETCONF XML data with cache
    def get_xml(self):
        if self.xml:
            xmlconfig = self.xml
        else:
            xmlconfig = self.fetch_xml()
        return xmlconfig

    # generic method for returning raw data string (here NETCONF XML)
    def fetch_raw(self):
        return self.get_xml()

    # specific method for parsing the NETCONF XML to route objects
    def proccess_xml(self):
        xmlconfig = self.get_xml();
        parser = np.Parser()
        parser.confile = xmlconfig
        device = parser.export()
        return device
    
    # specific method for parsing the NETCONF XML to DOM object tree
    def proccess_xml_generic(self):
        xmlconfig = self.get_xml();
        root = ET.fromstring(xmlconfig)
        return root

    # generic method for parsing the raw data (here NETCONF XML) to routes
    def retrieve_current_routes(self):
        device = self.proccess_xml()
        routes_lists = [flow.routes for flow in device.routing_options]
        routes = [item for routes_sublist in routes_lists for item in routes_sublist]
        return routes

    def fetch_device(self):
        device = cache.get("device")
        logger.info("[CACHE] hit! got device")
        if device:
            return device
        else:
            device = self.proccess_xml()
            if device.routing_options:
                cache.set("device", device, 3600)
                logger.info("[CACHE] miss, setting device")
                return device
            else:
                return False

    def retrieve_current_routes__globally_cached(self):
        device = self.fetch_device()
        #routes = device.routing_options[0].routes
        routes_lists = [flow.routes for flow in device.routing_options]
        routes = [item for routes_sublist in routes_lists for item in routes_sublist]
        return routes
 
class Applier(object):
    def __init__(self, route_objects=[], route_object=None, route_object_original=None, route_objects_all=[], device=settings.NETCONF_DEVICE, username=settings.NETCONF_USER, password=settings.NETCONF_PASS, port=settings.NETCONF_PORT):
        self.route_object = route_object
        self.route_objects = route_objects
        self.route_objects_all = route_objects_all
        self.device = device
        self.username = username
        self.password = password
        self.port = port

    def helper_fill_source_and_destination_to_xml(self, route_obj, route, is_ipv4):

       if route_obj.source:
           if is_ipv4:
             logger.info("source ipv4")
             route.match['source'].append(route_obj.source)
           else:
             logger.info("source ipv6")
             route.match['source-v6'].append(route_obj.source)

       if route_obj.destination:
           if is_ipv4:
             logger.info("destination ipv4")
             route.match['destination'].append(route_obj.destination)
           else:
             logger.info("destination ipv6")
             route.match['destination-v6'].append(route_obj.destination)

    def to_xml(self, operation=None):
        logger.info("proxy::Applier::to_xml(): Operation: %s"%operation)

        if self.route_object:

            try:
                settings.PORTRANGE_LIMIT
            except:
                settings.PORTRANGE_LIMIT = 100
            logger.info("proxy::Applier::to_xml:(): Generating XML config")

            route_obj = self.route_object

            ip_version = self.route_object.ip_version()
            is_ipv4 = self.route_object.is_ipv4()
            logger.info("proxy::Applier::to_xml(): is_ipv4="+str(is_ipv4))

            device = np.Device()
            flow = np.Flow(is_ipv4)
            route = np.Route()
            flow.routes.append(route)
            device.routing_options.append(flow)
            route.name = route_obj.name

            if operation == "delete":
                logger.info("proxy::Applier::to_xml(): Requesting a delete operation")
                route.operation = operation
                device = device.export(netconf_config=True)
                return ET.tostring(device)

            self.helper_fill_source_and_destination_to_xml(route_obj, route, is_ipv4)

            try:
                if route_obj.protocol:
                    for protocol in route_obj.protocol.all():
                        try:
                          protocol_id = map__ip_proto__for__ip_version__to_flowspec(ip_version, protocol.protocol)
                        except Exception as e:
                          logger.error("proxy::Applier::to_xml(): got exception in map__ip_proto__for__ip_version__to_flowspec: "+str(e))
                        route.match['protocol'].append(protocol_id)
            except:
                pass
            try:
                ports = []
                if route_obj.port:
                    portrange = str(route_obj.port)
                    for port in portrange.split(","):
                        route.match['port'].append(port)
            except:
                pass
            try:
                ports = []
                if route_obj.destinationport:
                    portrange = str(route_obj.destinationport)
                    for port in portrange.split(","):
                        route.match['destination-port'].append(port)
            except:
                pass
            try:
                if route_obj.sourceport:
                    portrange = str(route_obj.sourceport)
                    for port in portrange.split(","):
                        route.match['source-port'].append(port)
            except:
                pass
            if route_obj.icmpcode:
                route.match['icmp-code'].append(route_obj.icmpcode)
            if route_obj.icmptype:
                route.match['icmp-type'].append(route_obj.icmptype)
            if route_obj.tcpflag:
                route.match['tcp-flags'].append(route_obj.tcpflag)
            try:
                if route_obj.dscp:
                    for dscp in route_obj.dscp.all():
                        route.match['dscp'].append(dscp.dscp)
            except:
                pass

            try:
                if route_obj.fragmenttype:
                    for frag in route_obj.fragmenttype.all():
                        route.match['fragment'].append(frag.fragmenttype)
            except:
                pass

            for thenaction in route_obj.then.all():
                if thenaction.action_value:
                    route.then[thenaction.action] = thenaction.action_value
                else:
                    route.then[thenaction.action] = True
            if operation == "replace":
                logger.info("proxy::Applier::to_xml(): Requesting a replace operation")
                route.operation = operation
            device = device.export(netconf_config=True)
            result = ET.tostring(device)
            logger.info("result="+str(result))
            return result
        else:
            return False

    def delete_routes(self):
        if self.route_objects:
            logger.info("Generating XML config")
            device = np.Device()
            flow = np.Flow()
            for route_object in self.route_objects:
                route_obj = route_object
                route = np.Route()
                flow.routes.append(route)
                route.name = route_obj.name
                route.operation = 'delete'
            device.routing_options.append(flow)
            device = device.export(netconf_config=True)
            return ET.tostring(device)
        else:
            return False

    def get_route_name(self): 
        route_name=None
        if self.route_object:
            # support for dummy route_object as dicts 
            if isinstance(self.route_object, dict):
              route_name = self.route_object["name"] 
            else:
              route_name = self.route_object.name

        return route_name

    def get_existing_config_xml(self):
        route_name = self.get_route_name()
        logger.info("get_existing_config_xml(): route_name="+str(route_name))
        retriever0 = Retriever(xml=None, route_name=route_name)
        config_xml_running = retriever0.fetch_xml()
        #logger.info("proxy::get_existing_config(): config_xml_running="+str(config_xml_running))
        return config_xml_running

    def get_existing_config_xml_generic(self):
        route_name = self.get_route_name()
        logger.info("get_existing_config_xml_generic(): route_name="+str(route_name))
        retriever0 = Retriever(xml=None, route_name=route_name)
        config_xml_running = retriever0.proccess_xml_generic()
        #logger.info("proxy::get_existing_config(): config_xml_running="+str(config_xml_running))
        return config_xml_running

    def get_existing_config(self):
        route_name = self.get_route_name()
        logger.info("get_existing_config_xml(): route_name="+str(route_name))
        retriever0 = Retriever(xml=None)
        config_parsed = retriever0.proccess_xml()
        #logger.info("proxy::get_existing_config(): config_parsed="+str(config_parsed))
        return config_parsed

    def get_existing_routes(self):
        #config_parsed = self.get_existing_config_xml()
        config_parsed = self.get_existing_config_xml_generic()
        if True:
          routes_existing = []
          logger.info("config_parsed="+str(config_parsed))
          #logger.info("config_parsed="+str(ET.dump(config_parsed)))
          #flow = config_parsed.routing_options[0]
          #for route in config_parsed.iter('ns1:route'):
          for route in config_parsed.findall(".//{http://xml.juniper.net/xnm/1.1/xnm}route"):
              logger.info("proxy::get_existing_routes(): found route="+str(route))
              routes_existing.append(route)
          return routes_existing
        else:
          logger.info("proxy::get_existing_routes(): no routing_options or is empty")
          return []

    def get_existing_route_names(self):
      routes_existing = self.get_existing_routes()
      #route_ids_existing = [route.name for route in routes_existing]
      #route_ids_existing = [ET.SubElement(route, './/{http://xml.juniper.net/xnm/1.1/xnm}name') for route in routes_existing]
      route_ids_existing = [route.find('.//{http://xml.juniper.net/xnm/1.1/xnm}name').text for route in routes_existing]
      logger.info("proxy::get_existing_route_names(): config_parsed.flow.routes.ids="+str(route_ids_existing))
      return route_ids_existing


    def apply(self, configuration = None, operation=None):
        reason = None
        if not configuration:
            configuration = self.to_xml(operation=operation)
        edit_is_successful = False
        commit_confirmed_is_successful = False
        commit_is_successful = False
        r = redis.StrictRedis()
        lock = r.lock("netconf_lock")
        lock.acquire(blocking=True)
        try:
          if configuration:
            with manager.connect(host=self.device, port=self.port, username=self.username, password=self.password, hostkey_verify=False) as m:
                assert(":candidate" in m.server_capabilities)
                with m.locked(target='candidate'):
                    m.discard_changes()
                    try:
                        edit_response = m.edit_config(target='candidate', config=configuration.decode("utf-8"), test_option='test-then-set')
                        edit_is_successful, reason = is_successful(edit_response)
                        logger.info("Successfully edited @ %s" % self.device)
                        if not edit_is_successful:
                            raise Exception()
                    except SoftTimeLimitExceeded:
                        cause="Task timeout"
                        logger.error(cause)
                        return False, cause, cause
                    except TimeLimitExceeded:
                        cause="Task timeout"
                        logger.error(cause)
                        return False, cause, cause
                    except RPCError as e:
                        cause="NETCONF RPC Error: "+str(e)
                        logger.error(cause)
                        m.discard_changes()
                        return False, cause, cause
                    except Exception as e:
                        traceback.print_exc()
                        cause = "Caught edit exception: type='%s' str='%s' => reason='%s'" % (type(e), str(e), reason)
                        cause = cause.replace('\n', '')
                        logger.error(cause)
                        m.discard_changes()
                        return False, cause, cause
                    if edit_is_successful:
                        try:
                            if ":confirmed-commit" in m.server_capabilities:
                                commit_confirmed_response = m.commit(confirmed=True, timeout=settings.COMMIT_CONFIRMED_TIMEOUT)
                                commit_confirmed_is_successful, reason = is_successful(commit_confirmed_response)
                                if not commit_confirmed_is_successful:
                                    raise Exception()
                                else:
                                    logger.info("Successfully confirmed committed @ %s" % self.device)
                                    if not settings.COMMIT:
                                        return True, "Successfully confirmed committed", "NETCONF: "+str(reason)
                            else:
                                commit_response = m.commit(confirmed=False, timeout=settings.COMMIT_CONFIRMED_TIMEOUT)
                                if commit_response.ok:
                                    logger.info("Successfully committed @ %s" % self.device)
                                    return True, "Successfully committed", "NETCONF OK"
                                else:
                                    cause = "Failed to commit changes %s" % commit_response.erros
                                    return False, cause, cause

                        except SoftTimeLimitExceeded:
                            cause="Task timeout"
                            logger.error(cause)
                            return False, cause, cause
                        except TimeLimitExceeded:
                            cause="Task timeout"
                            logger.error(cause)
                            return False, cause, cause
                        except RPCError as e:
                            cause="NETCONF RPC Error: "+str(e)
                            logger.error(cause)
                            m.discard_changes()
                            return False, cause, cause
                        except Exception as e:
                            cause="Caught commit confirmed exception: type='%s' str='%s' => reason='%s'" %(type(e), str(e), reason)
                            cause=cause.replace('\n', '')
                            logger.error(cause)
                            return False, cause, cause

                        if settings.COMMIT:
                            if edit_is_successful and commit_confirmed_is_successful:
                                try:
                                    commit_response = m.commit(confirmed=False)
                                    commit_is_successful, reason = is_successful(commit_response)
                                    logger.info("Successfully committed @ %s" % self.device)
                                    newconfig = m.get_config(source='running', filter=('subtree',settings.ROUTES_FILTER)).data_xml
                                    retrieve = Retriever(xml=newconfig)
                                    logger.info("[CACHE] caching device configuration")
                                    cache.set("device", retrieve.proccess_xml(), 3600)

                                    if not commit_is_successful:
                                        raise Exception()
                                    else:
                                        logger.info("Successfully cached device configuration")
                                        return True, "Successfully committed", "NETCONF: OK"
                                except SoftTimeLimitExceeded:
                                    cause="Task timeout"
                                    logger.error(cause)
                                    return False, cause, cause
                                except TimeLimitExceeded:
                                    cause="Task timeout"
                                    logger.error(cause)
                                    return False, cause, cause
                                except RPCError as e:
                                    cause="NETCONF RPC Error: "+str(e)
                                    logger.error(cause)
                                    m.discard_changes()
                                    return False, cause, cause
                                except Exception as e:
                                    cause="Caught commit exception: type='%s' str='%s' => reason='%s'" %(type(e), str(e), reason)
                                    cause=cause.replace('\n', '')
                                    logger.error(cause)
                                    return False, cause, cause
          else:
            return False, "No configuration was supplied"
        except Exception as e:
            cause="NETCONF connection exception: %s %s" %(e,reason)
            cause=cause.replace('\n', '')
            logger.error(cause)
            cause_user="NETCONF connection failed"
            return False, cause_user, cause
        finally:
            lock.release()


def is_successful(response):
    if response.ok:
        return True, None
    elif response.error:
        return False, '%s %s' % (response.error.type, response.error.message)
    else:
        return False, "Unknown error"

