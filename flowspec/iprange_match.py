# -*- coding: utf-8 -*- vim:fileencoding=utf-8:
# vim: tabstop=4:shiftwidth=4:softtabstop=4:expandtab

#from flowspec.models import *
from flowspec.model_utils import convert_container_to_queryset
from peers.models import *

from ipaddress import *
from intervaltree.intervaltree import IntervalTree, Interval

import os
import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "iprange_match.log", False)

def build_ival_trees_per_ipversion(user):
    
    # build ival trees for users peer ip ranges
    try:
      # venv/lib/python3.8/site-packages/intervaltree/intervaltree.py
      ivaltrees_per_version = {}

      if user.is_superuser:
        peers = Peer.objects.all()
      else:
        peers = user.userprofile.peers.all()
      for peer in peers:
        for network in peer.networks.all():
          net = ip_network(network, strict=False)
          # Intervals are half open ivals [a, b), so use b+1 instead of b => [a, b+1) intersect Int = [a,b] intersect Int
          # int(...) necessary to allow for .+1 not to get an ip address overflow for 255.255.255.255
          ival1 = Interval(int(net.network_address), int(net.broadcast_address)+1, peer)
          #logger.info("views::build_routes_json(): "+str(net.network_address)+"::"+str(net.broadcast_address)+" => ival1="+str(ival1))
          if not net.version in ivaltrees_per_version:
            ivaltrees_per_version[net.version] = IntervalTree()
          ivaltrees_per_version[net.version].add(ival1)
    except Exception as e:
      logger.error("iprange_match::build_ival_trees_per_ipversion(): got exception: "+str(e), exc_info=True)

    return ivaltrees_per_version


def get_matching_related_peer_for_rule_destination(ivaltrees_per_version, route):

   is_applier_related = True
   peer_name_tmp = None
   peer_name_tmp_not_applier_related = None
   try:
      applier = route.applier
   except:
      applier = None

   try:
     if applier!=None:    
       route_applier__peers_related = set(applier.userprofile.peers.select_related())
     else:
       route_applier__peers_related = None

     route_destination = route.destination

     qnet = ip_network(route_destination, strict=False)
     qival = Interval(int(qnet.network_address), int(qnet.broadcast_address)+1)
     if qnet.version in ivaltrees_per_version:
       result = ivaltrees_per_version[qnet.version].overlap(qival)
     else:
       result = []
     #logger.info("iprange_match::get_matching_related_peer_for_rule_destination(): qnet.network_address="+str(qnet.network_address)+" qnet.broadcast_address="+str(qnet.broadcast_address)+" => qival="+str(qival)+" => result="+str(result))
     for rval in result:
       if route_applier__peers_related==None or rval.data in route_applier__peers_related:
         peer_name_tmp = rval.data.peer_name
         break
       else:
         #logger.info("iprange_match::get_matching_related_peer_for_rule_destination(): qival="+str(qival)+" => result="+str(result)+" rval="+str(rval)+" : not in route_applier__peers_related="+str(route_applier__peers_related))
         if peer_name_tmp_not_applier_related==None:
           peer_name_tmp_not_applier_related = rval.data.peer_name

     if peer_name_tmp==None and peer_name_tmp_not_applier_related!=None:
       #logger.info("iprange_match::get_matching_related_peer_for_rule_destination(): no applier related peer could be found, so using applier unrelated peer "+str(peer_name_tmp_not_applier_related))
       peer_name_tmp = peer_name_tmp_not_applier_related
       is_applier_related = False

   except Exception as e:
       logger.error("iprange_match::get_matching_related_peer_for_rule_destination(): got exception: "+str(e), exc_info=True)

   return (peer_name_tmp, is_applier_related)

##

def filter_rules_by_ivaltree(ivaltrees_per_version, all_routes):
      filtered_routes = [route for route in all_routes if get_matching_related_peer_for_rule_destination(ivaltrees_per_version, route)[0]!=None]
      return filtered_routes

#def filter_rules_by_ivaltree__ret_queryset(ivaltrees_per_version, all_routes):
#      filtered_routes = filter_rules_by_ivaltree(ivaltrees_per_version, all_routes)
#      filtered_routes_qs = convert_container_to_queryset(filtered_routes, Route)
#      #filtered_routes_qs = flowspec.models.convert_container_to_queryset(filtered_routes, Route)
#      return filtered_routes_qs

##

def find_matching_peer_by_ipprefix__simple(peers, route_destination):
    net_route_destination = ip_network(route_destination, strict=False)
    return find_matching_peer_by_ipnet__simple(peers, net_route_destination)

def find_matching_peer_by_ipnet__simple(peers, net_route_destination):
    peer_matched__name=None
    for peer in peers:
      if peer_matched__name:
        break
      for network in peer.networks.all():
        net = ip_network(network, strict=False)
        if net_route_destination in net:
          peer_matched__name = peer
          break
    return peer_matched__name


