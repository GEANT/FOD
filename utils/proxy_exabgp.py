# -*- coding: utf-8 -*- vim:fileencoding=utf-8:
# vim: tabstop=4:shiftwidth=4:softtabstop=4:expandtab

# /srv/venv/lib/python3.11/site-packages/exabgp/application/cli.py
#from exabgp.application.cli import main as exabgp_cli_main

# utils/exabgpcli.py

from django.conf import settings
from utils.exabgpcli import exabgp_interaction
import utils.route_spec_utils as route_spec_utils

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
import re
import sys

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "celery_exabpg.log", False)

#print("loading proxy_exabgp", file=sys.stderr)

cwd = os.getcwd()

#def fod_unknown_host_cb(host, fingerprint):
#    return True

#print("loading proxy_exabgp: step1")

from threading import Lock
lock = Lock()

def do_exabgp_interaction(command_list):
    pre1="[pid:"+str(os.getpid())+"] "
    logger.info(pre1+"proxy_exabgp::do_exabgp_interaction(): called")
    lock.acquire()
    logger.info(pre1+"proxy_exabgp::do_exabgp_interaction(): lock acquired")
    ret=""
    msg=""
    try:
      logger.info(pre1+"proxy_exabgp::do_exabgp_interaction(): before exabgp_interaction")
      ret, msg = exabgp_interaction(command_list)
      logger.info(pre1+"proxy_exabgp::do_exabgp_interaction(): done with exabgp_interaction")
    except Exception as e:
      logger.info(pre1+"proxy_exabgp::do_exabgp_interaction(): got exception "+str(e), exc_info=True)
      ret=1
    except Error as e:
      logger.info(pre1+"proxy_exabgp::do_exabgp_interaction(): got error "+str(e), exc_info=True)
      ret=1
    except:
      logger.info(pre1+"proxy_exabgp::do_exabgp_interaction(): got unknown error ", exc_info=True)
      ret=1
    finally:
      lock.release() #release lock
      logger.info(pre1+"proxy_exabgp::do_exabgp_interaction(): lock released")

    logger.info("proxy_exabgp::do_exabgp_interaction(): ret="+str(ret)+" msg="+str(msg))
    return ret, msg

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
        return False

    # specific method for fetching raw NETCONF XML data
    # +
    # generic method for returning raw data string (here NETCONF XML)
    def fetch_raw(self):
      logger.info("proxy_exabgp::Retriever::fetch_raw(): called")
      #ret, msg = do_exabgp_interaction(["show adj-rib out"])
      ret, msg = do_exabgp_interaction(["show adj-rib out extensive"])
      logger.info("proxy_exabgp::Retriever::fetch_raw(): ret="+str(ret))
      #logger.info("proxy_exabgp::Retriever::fetch_raw(): msg="+str(msg))
      return msg

    # specific method for parsing the NETCONF XML to route objects
    # +
    # generic method for parsing the raw data (here NETCONF XML) to routes
    # e.g., neighbor 127.0.0.3 ipv6 flow flow source-ipv6 ::/0/0 protocol [ =tcp =udp ] destination-port [ >=2&<=900 ] source-port [ >=1&<=100 ] fragment [ dont-fragment last-fragment ]
    def parse_exabgp__routes_output(self, msg):
       logger.info("parse_exabgp__routes_output(): called")
       lines = msg.split("\n")
       #logger.info("proxy_exabgp::Retriever::parse_exabgp__routes_output(): => lines="+str(lines))
       #re1 = re.compile('^neighbor +\S+ +ipv([46]) +flow +flow +(.*)$')
       re1 = re.compile('^neighbor +.* +ipv([46]) +flow +flow +(.*)$')
       #logger.info("re="+str(re))
       route_exabgp__str__list = [re1.match(line).group(1)+" "+re1.match(line).group(2) for line in lines if re1.match(line)]
       #logger.info("route_exabgp__str__list="+str(route_exabgp__str__list))
       routes = [self.parse_exabgp_route__str(route_exabgp__str) for route_exabgp__str in route_exabgp__str__list]
       logger.info("=> routes="+str(routes))
       return routes

    # e.g., 4 source-ipv6 ::/0/0 protocol [ =tcp =udp ] destination-port [ >=2&<=900 ] source-port [ >=1&<=100 ] fragment [ dont-fragment last-fragment ]
    def parse_exabgp_route__str(self, route_exabgp__str):
      #re1 = re.compile('^(?P<version>[46]) +((destination-ipv[46]) +(?P<destination>\S+) +)?((source-ipv[46]) +(?P<source>\S+) +)?(protocol +(?P<protocol>(\[[^\[\]]+\])|\S+) +)?(destination-port +(?P<destination_port>(\[[^\[\]]+\])|\S+) +)?(source-port +(?P<source_port>(\[[^\[\]]+\])|\S+) +)?(fragment +(?P<fragment>(\[[^\[\]]+\])|\S+) +)?')
      re1 = re.compile('^(?P<version>[46]) +((destination-ipv[46]) +(?P<destination>\S+) +)?((source-ipv[46]) +(?P<source>\S+) +)?(protocol +(?P<protocol>(\[[^\[\]]+\])|\S+) +)?(destination-port +(?P<destination_port>(\[[^\[\]]+\])|\S+) +)?(source-port +(?P<source_port>(\[[^\[\]]+\])|\S+) +)?(fragment +(?P<fragment>(\[[^\[\]]+\])|\S+) +)?(extended-community +)?(rate-limit:+(?P<ratelimit>(\[[^\[\]]+\])|\S+) +)?')
      key_is_singlevalued = {
        'version': 1,
        #'source': 1,
        #'destination': 1
      }
      m = re1.match(route_exabgp__str+" ")
      if m:
          route = {}
          for groupname in re1.groupindex:
            val = m.group(groupname)
            logger.info("groupname="+str(groupname)+" => val="+str(val))

            # special case
            if groupname=='source' or groupname=='destination' and route['version']=='6':
              if val!=None:
                val = re.sub('(/[0-9]+)/0$', '\\1', val)
            elif groupname=='ratelimit':
                if val!="0":
                    groupname="then"
                    val="rate-limit:"+str(int(int(val)/1000))+"k"
                else:
                    groupname="then"
                    val="discard"

            groupname2 = groupname.translate({ '_' : '-' })
            if groupname in key_is_singlevalued or val==None:
              route[groupname] = self.parse_exabgp_list_elem__str(val)
            else:
              route[groupname] = self.parse_exabgp_list__str(val)
      else:
        route = None

      return route

    def parse_exabgp_list__str(self, list__str):
      m = re.match('\[ *([^\[\]]+) *\]', list__str)
      if m:
        inner__str = m.group(1)
        list = inner__str.split()
      else:
        list = [list__str.strip()]

      list = [self.parse_exabgp_list_elem__str(x) for x in list]

      return list

    def parse_exabgp_list_elem__str(self, s):
       if s!=None:
         if s[0:1]=="=":
           s = s[1:]
       #logger.info("parse_exabgp_list_elem__str() => s:"+str(s))
       return s    

    def retrieve_current_routes(self):
      logger.info("proxy_exabgp::Retriever::retrieve_current_routes(): called")
      msg = self.fetch_raw()
      #logger.info("proxy_exabgp::Retriever::retrieve_current_routes(): => msg="+str(msg))
      routes = self.parse_exabgp__routes_output(msg)
      #logger.info("proxy_exabgp::Retriever::retrieve_current_routes(): routes="+str(routes))
      return routes

    def retrieve_current_routes__globally_cached(self):
        current_routes = cache.get("current_routes")
        if current_routes:
            logger.info("[CACHE] hit! got current_routes")
            return current_routes
        else:
            current_routes = self.retrieve_current_routes()
            if current_routes:
                cache.set("current_routes", current_routes, 3600)
                logger.info("[CACHE] miss, setting current_routes")
                return current_routes
            else:
                # do not cache empty result, might be a failure
                return current_routes

class Applier(object):
  def __init__(self, route_objects=[], route_object=None, route_object_original=None, route_objects_all=[]):
    logger.info("proxy_exabgp::Appplier::__init__")
    self.route_object = route_object
    self.route_objects = route_objects
    self.route_object_original = route_object_original
    self.route_objects_all = route_objects_all

  def get_existing_config_xml(self):
        #route_name = self.get_route_name()
        #logger.info("get_existing_config_xml(): route_name="+str(route_name))
        retriever0 = Retriever()
        config_xml_running = retriever0.fetch_raw()
        #logger.info("proxy::get_existing_config(): config_xml_running="+str(config_xml_running))
        return config_xml_running

  def helper_active_routes_with_same_parameters_exist(self, route, route_objects_all, include_route_self):
     list2 = self.helper_get_active_routes_with_same_parameters(route, route_objects_all, True)
     logger.info("proxy_exabgp::helper_get_active_routes_with_same_parameters(): route="+str(route)+" => list2="+str(list2))
     route_with_same_params__exists = len(list2)>0
     logger.info("proxy_exabgp::helper_get_active_routes_with_same_parameters(): => ret="+str(route_with_same_params__exists))
     return route_with_same_params__exists

  def helper_get_active_routes_with_same_parameters(self, route, route_objects_all, include_route_self):
    ret = []
    route_par_str = self.helper_get_exabgp__route_parameter_string(route)
    #logger.info("helper_get_active_exabgp__route_parameter_string(): route_par_str="+str(route_par_str))
    for route2 in route_objects_all:
      #logger.info("helper_get_active_exabgp__route_parameter_string(): route2="+str(route2))
      if (include_route_self or route2!=route) and route2.status=="ACTIVE":
          if self.helper_get_exabgp__route_parameter_string(route2)==route_par_str:
              ret.append(route2)

    return ret

  # e.g.: neighbor 14.0.0.2 ipv4 flow flow destination-ipv4 20.20.20.1/32 source-ipv4 15.10.10.1/32 protocol =tcp destination-port [ >=200&<=400 ] source-port [ >=123&<=129 ] next-hop 14.0.0.2
  def helper_get_exabgp__route_parameter_string(self, route):
    ret = ""

    if isinstance(route, dict):
        source = route['source']
        destination = route['destination']
        sourceport = route['sourceport']
        destinationport = route['destinationport']
        protocols = route['protocol']
        fragtypes = route['fragmenttype']
        thens = route['then']
    else:
        source = route.source
        destination = route.destination
        sourceport = route.sourceport
        destinationport = route.destinationport
        protocols = route.protocol.all()
        fragtypes = route.fragmenttype.all()
        thens = route.then.all()

    ret = ret + " source-ipv4 " + str(source) + " "
    ret = ret + " destination-ipv4 " + str(destination) + " "

    ip_version = 4
    ip_version1 = ip_network(source).version 
    ip_version2 = ip_network(destination).version 
    if ip_version1==4 or ip_version2==4:
      ip_version = 4
    elif ip_version1==6 or ip_version2==6:
      ip_version = 6

    ##

    ret1 = route_spec_utils.get_protocols_numbers(protocols, ip_version, output_separator=" ", output_prefix="")
    if ret1 != "":
      ret = ret + " protocol [ " + ret1 + " ]" 

    ret1 = route_spec_utils.translate_ports(sourceport, output_separator=" ")
    if ret1 != "":
      ret = ret + " source-port [ " + ret1 + "]"

    ret1 = route_spec_utils.translate_ports(destinationport, output_separator=" ")
    if ret1 != "":
      ret = ret + " destination-port [ " + ret1 + "]"

    ret1 = ""
    for fragtype in fragtypes:
      ret1 = ret1 + str(fragtype) + " "
    if ret1!="":
      ret = ret + " fragment [ " + ret1 + "]"

    ret1 = ""
    for then in thens:
      then_str = str(then)
      logger.info("then='"+then_str+"'")
      #action = then.action
      #action_value = then.action_value
      ret2 = ""
      #re1 = re.compile('^rate-limit:(?P<value>.*)(k?)$'
      re1 = re.compile('^rate-limit:(?P<value>[0-9]+)(k?)$')
      re_match1 = re1.match(then_str)
      if re_match1:
        val_part = str(re_match1.group(1))
        k_part = str(re_match1.group(2))
        if k_part=="k":
          val_part = str(int(val_part)*1000)
        ret2 = "rate-limit "+val_part
      elif str(then)=="discard":
        ret2 = "rate-limit 0"
      else:
        logger.error("currently only rate-limit and discard supported as then action")

      ret1 = ret1 + ret2 + " "
      logger.info("then => ret1="+str(ret1))

    if ret1!="":
      logger.info("then final => ret1="+str(ret1))
      #ret = ret + " fragment [ " + ret1 + "]"
      ret = ret + ret1

    logger.info("helper_get_exabgp__route_parameter_string(): ret="+str(ret))

    return ret

  def announce_route(self, route):
    ret, msg = do_exabgp_interaction("announce flow route "+self.helper_get_exabgp__route_parameter_string(route))
    return ret==0, msg

  def withdraw_route(self, route):
    ret, msg = do_exabgp_interaction("withdraw flow route "+self.helper_get_exabgp__route_parameter_string(route))
    return ret==0, msg

  ###

  def apply(self, configuration=None, operation=None):
    logger.info("proxy_exabgp::apply(): called operation="+str(operation))
 
    try:
      route = self.route_object
      route_objects_all = self.route_objects_all
      route_original = self.route_object_original
      if isinstance(route, dict):
        route_original__status = route['status']
      else:
        route_original__status = route.status
      
      if route==None or route_objects_all==None:
        logger.error("proxy_exabgp::apply(): route and route_objects_all have to be defined")
        return False, "route and route_objects_all have to be defined"
 
      logger.info("proxy_exabgp::apply(): route_object="+str(route))
      str1 = self.helper_get_exabgp__route_parameter_string(route)
      logger.info("proxy_exabgp::apply(): => route_spec_str="+str(str1))
 
      route_with_same_params__exists = self.helper_active_routes_with_same_parameters_exist(route, route_objects_all, False)
      logger.info("proxy_exabgp::apply(): => route_with_same_params__exists="+str(route_with_same_params__exists))
      logger.info("proxy_exabgp::apply(): => route.status="+str(route.status))

      ##
  
      if operation == "delete":
        logger.info("proxy_exabgp::apply(): requesting a delete operation")
        if route_with_same_params__exists:
          logger.info("proxy_exabgp::apply(): route_with_same_params__exists, nothing todo")
          status =True
          msg = "route_with_same_params__exists, nothing todo"
        elif route_original__status!="INACTIVE" and route_original__status!="PENDING":
          logger.info("proxy_exabgp::apply(): route_original__status!=INACTIVE/PENDING, ignoring request")
          status = True
          msg = "status!=INACTIVE/PENDING, ignoring request"
        else:
          logger.info("proxy_exabgp::apply(): actually have to withdraw route")
          status, msg1 = self.withdraw_route(route)
          logger.info("proxy_exabgp::apply(): withdrawing done status="+str(status)+", "+str(msg1))
          msg = "withdraw route: "+str(msg1)
        if status:
          return status, "successfully committed", msg
        else:
          return status, msg, msg
  
      elif operation == "replace":
        logger.info("proxy_exabgp::apply(): requesting a replace operation")
 
        logger.info("proxy_exabgp::apply(): route_original="+str(route_original))
        if route_original==None:
          logger.error("proxy_exabgp::apply(): route_original has to be defined")
          return False, "route_original has to be defined"
       
        route__spec = self.helper_get_exabgp__route_parameter_string(route)
        logger.info("proxy_exabgp::apply(): route__spec="+str(route__spec))
        route_original__spec = self.helper_get_exabgp__route_parameter_string(route_original)
        logger.info("proxy_exabgp::apply(): route_original__spec="+str(route_original__spec))
 
        route_with_same_old_params__exists = self.helper_active_routes_with_same_parameters_exist(route_original, route_objects_all, False)
        logger.info("proxy_exabgp::apply(): => route_with_same_old_params__exists="+str(route_with_same_old_params__exists))
 
        route_status_changed = route_original__status!=route.status or route.status=="PENDING"
        logger.info("proxy_exabgp::apply(): => route_original__status="+str(route_original__status))
        logger.info("proxy_exabgp::apply(): => route.status="+str(route.status))
        logger.info("proxy_exabgp::apply(): => route_status_changed="+str(route_status_changed))
 
        if route.status!="ACTIVE" and route.status!="PENDING":
          logger.info("proxy_exabgp::apply(): route status="+str(route.status)+"!=ACTIVE/PENDING, ignoring request")
          status = True
          msg = "status!=ACTIVE/PENDING, ignoring request"
        elif route__spec==route_original__spec and not route_status_changed:
          #logger.info("proxy_exabgp::apply(): route effetively did not change in parameters or status")
          #return True, "nothing todo"
          logger.info("proxy_exabgp::apply(): route effetively did not change in parameters or status; anyway ensuring route is announced")
          status, msg1 = self.announce_route(route)
          logger.info("proxy_exabgp::apply(): announcing done status="+str(status)+", "+str(msg1))
          msg = "re-announce unchanged flow: "+str(msg1)
        elif route__spec==route_original__spec and not route_status_changed:
          logger.info("proxy_exabgp::apply(): route effetively did not change in parameters but in status; announcing route")
          status, msg1 = self.announce_route(route)
          logger.info("proxy_exabgp::apply(): announcing done status="+str(status)+", "+str(msg1))
          msg = "announce (re)-added flow: "+str(msg1)

        else:
  
          status_del = True
          if route_with_same_old_params__exists:
            logger.info("proxy_exabgp::apply(): route_with_same_old_params__exists => no need to withdraw old route")
            status_del = True
            msg_del = "route_with_same_old_params__exists, nothing todo"
          else:
            logger.info("proxy_exabgp::apply(): NO route_with_same_old_params__exists => need to withdraw old route")
            status_del, msg1 = self.withdraw_route(route_original) 
            logger.info("proxy_exabgp::apply(): withdrawing done status="+str(status_del)+", "+str(msg1))
            msg_del = "withdraw old flow: "+str(msg1)+"; "
 
          if route_with_same_params__exists:
            #logger.info("proxy_exabgp::apply(): route_with_same_params__exists => no need to announce changed route")
            logger.info("proxy_exabgp::apply(): route_with_same_params__exists; anyway ensuring route is announced")
            status, msg1 = self.announce_route(route)
            logger.info("proxy_exabgp::apply(): announcing done status="+str(status)+", "+str(msg1))
            status = status_del and status 
            msg = msg_del+"re-announced changed flow: "+str(msg1)
          else:
            logger.info("proxy_exabgp::apply(): NO route_with_same_params__exists => need to announce changed route")
            status, msg1 = self.announce_route(route)
            logger.info("proxy_exabgp::apply(): announcing done status="+str(status)+", "+str(msg1))
            status = status_del and status 
            msg = msg_del+"announced changed flow: "+str(msg1)

        if status:
          return status, "successfully committed", msg
        else:
          return status, msg, msg
 
      else: # add operation
        logger.info("proxy_exabgp::apply(): requesting (implicitly) an add operation")

        if route.status!="ACTIVE" and route.status!="PENDING":
          logger.info("proxy_exabgp::apply(): route.status="+str(route.status)+", ignoring request")
          status = True
          msg = "status!=ACTIVE/PENDING, ignoring request"
        elif route_with_same_params__exists:
          logger.info("proxy_exabgp::apply(): route_with_same_params__exists, nothing todo")
          status = True
          msg = "route_with_same_params__exists, nothing todo"
        else:
          logger.info("proxy_exabgp::apply(): actually have to announce route")
          status, msg1 = self.announce_route(route)
          logger.info("proxy_exabgp::apply(): announcing done status="+str(status)+", "+str(msg1))
          msg = "announce new flow: "+str(msg1)

        if status:
          return status, "successfully committed", msg
        else:
          return status, msg, msg

    except Exception as e:
        logger.error("proxy_exabgp::apply(): got exception="+str(e), exc_info=True)

#    def delete_routes(self):
#        if self.route_objects:
#            logger.info("Generating XML config")
#            device = np.Device()
#            flow = np.Flow()
#            for route_object in self.route_objects:
#                route_obj = route_object
#                route = np.Route()
#                flow.routes.append(route)
#                route.name = route_obj.name
#                route.operation = 'delete'
#            device.routing_options.append(flow)
#            device = device.export(netconf_config=True)
#            return ET.tostring(device)
#        else:
#            return False
#
#    def get_route_name(self): 
#        route_name=None
#        if self.route_object:
#            # support for dummy route_object as dicts 
#            if isinstance(self.route_object, dict):
#              route_name = self.route_object["name"] 
#            else:
#              route_name = self.route_object.name
#
#        return route_name
#
#    def get_existing_config_xml(self):
#        route_name = self.get_route_name()
#        logger.info("get_existing_config_xml(): route_name="+str(route_name))
#        retriever0 = Retriever(xml=None, route_name=route_name)
#        config_xml_running = retriever0.fetch_xml()
#        #logger.info("proxy::get_existing_config(): config_xml_running="+str(config_xml_running))
#        return config_xml_running
#
#    def get_existing_config_xml_generic(self):
#        route_name = self.get_route_name()
#        logger.info("get_existing_config_xml_generic(): route_name="+str(route_name))
#        retriever0 = Retriever(xml=None, route_name=route_name)
#        config_xml_running = retriever0.proccess_xml_generic()
#        #logger.info("proxy::get_existing_config(): config_xml_running="+str(config_xml_running))
#        return config_xml_running
#
#    def get_existing_config(self):
#        route_name = self.get_route_name()
#        logger.info("get_existing_config_xml(): route_name="+str(route_name))
#        retriever0 = Retriever(xml=None)
#        config_parsed = retriever0.proccess_xml()
#        #logger.info("proxy::get_existing_config(): config_parsed="+str(config_parsed))
#        return config_parsed
#
#    def get_existing_routes(self):
#        #config_parsed = self.get_existing_config_xml()
#        config_parsed = self.get_existing_config_xml_generic()
#        if True:
#          routes_existing = []
#          logger.info("config_parsed="+str(config_parsed))
#          #logger.info("config_parsed="+str(ET.dump(config_parsed)))
#          #flow = config_parsed.routing_options[0]
#          #for route in config_parsed.iter('ns1:route'):
#          for route in config_parsed.findall(".//{http://xml.juniper.net/xnm/1.1/xnm}route"):
#              logger.info("proxy::get_existing_routes(): found route="+str(route))
#              routes_existing.append(route)
#          return routes_existing
#        else:
#          logger.info("proxy::get_existing_routes(): no routing_options or is empty")
#          return []
#
#    def get_existing_route_names(self):
#      routes_existing = self.get_existing_routes()
#      #route_ids_existing = [route.name for route in routes_existing]
#      #route_ids_existing = [ET.SubElement(route, './/{http://xml.juniper.net/xnm/1.1/xnm}name') for route in routes_existing]
#      route_ids_existing = [route.find('.//{http://xml.juniper.net/xnm/1.1/xnm}name').text for route in routes_existing]
#      logger.info("proxy::get_existing_route_names(): config_parsed.flow.routes.ids="+str(route_ids_existing))
#      return route_ids_existing
#
#def is_successful(response):
#    if response.ok:
#        return True, None
#    elif response.error:
#        return False, '%s %s' % (response.error.type, response.error.message)
#    else:
#        return False, "Unknown error"

