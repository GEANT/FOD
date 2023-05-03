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

import pytest
from utils import proxy as PR
from celery import shared_task, subtask
import json
from django.conf import settings
import datetime
from django.core.mail import send_mail
from django.template.loader import render_to_string
from celery.exceptions import TimeLimitExceeded, SoftTimeLimitExceeded
from ipaddress import *
from os import fork,_exit
import os
from sys import exit
import time
import redis
from django.forms.models import model_to_dict

from peers.models import *

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "celery_jobs.log", False)
rule_changelog_logger = flowspec.logging_utils.logger_init_default(__name__ + "__rule_changelog", "rule_changelog.log", False)
import logging
rule_changelog_logger.setLevel(logging.INFO)

##

@shared_task(ignore_result=True, autoretry_for=(TimeoutError, TimeLimitExceeded, SoftTimeLimitExceeded), retry_backoff=True, retry_kwargs={'max_retries': settings.NETCONF_MAX_RETRY_BEFORE_ERROR})
def add(routepk, callback=None):
    from flowspec.models import Route
    route = Route.objects.get(pk=routepk)
    applier = PR.Applier(route_object=route)
    commit, response = applier.apply()
    if commit:
        route.status = "ACTIVE"
        #snmp_add_initial_zero_value.delay(str(route.id), True)
        snmp_add_initial_zero_value(str(route.id), True)
    elif response=="Task timeout":
        if deactivate_route.request.retries < settings.NETCONF_MAX_RETRY_BEFORE_ERROR:
            # repeat the action
            raise TimeoutError()
        route.status = "ERROR"
    else:
        route.status = "ERROR"
    route.response = response
    route.save()
    announce("[%s] Rule add: %s - Result: %s" % (route.applier_username_nice, route.name_visible, response), route.applier, route)


@shared_task(ignore_result=True, autoretry_for=(TimeLimitExceeded, SoftTimeLimitExceeded), retry_backoff=True, retry_kwargs={'max_retries': settings.NETCONF_MAX_RETRY_BEFORE_ERROR})
def edit(routepk, callback=None):
    from flowspec.models import Route
    route = Route.objects.get(pk=routepk)
    status_pre = route.status
    logger.info("tasks::edit(): route="+str(route)+", status_pre="+str(status_pre))
    applier = PR.Applier(route_object=route)
    commit, response = applier.apply(operation="replace")
    if commit:
        route.status = "ACTIVE"
        try:
          #snmp_add_initial_zero_value.delay(str(route.id), True)
          snmp_add_initial_zero_value(str(route.id), True)
        except Exception as e:
          logger.error("tasks::edit(): route="+str(route)+", ACTIVE, add_initial_zero_value failed: "+str(e))
    elif response=="Task timeout":
        if deactivate_route.request.retries < settings.NETCONF_MAX_RETRY_BEFORE_ERROR:
            # repeat the action
            raise TimeoutError()
        route.status = "ERROR"
    else:
        route.status = "ERROR"
    route.response = response
    route.save()
    announce("[%s] Rule edit: %s - Result: %s" % (route.applier_username_nice, route.name_visible, response), route.applier, route)

@shared_task(ignore_result=True, autoretry_for=(TimeoutError, TimeLimitExceeded, SoftTimeLimitExceeded), retry_backoff=True, retry_kwargs={'max_retries': settings.NETCONF_MAX_RETRY_BEFORE_ERROR})
def deactivate_route(routepk, **kwargs):
    """Deactivate the Route in ACTIVE state. Permissions must be checked before this call."""

    reason_text = ''
    if "reason" in kwargs:
      reason = kwargs['reason']
      reason_text = 'Reason: %s.' % reason

    # here imported to avoid cyclic import on file level
    from flowspec.models import Route
    route = Route.objects.get(pk=routepk)
    initial_status = route.status
    if initial_status not in ("ACTIVE", "PENDING", "ERROR"):
        logger.error("tasks::deactivate(): Cannot deactivate route that is not in ACTIVE or potential ACTIVE status.")
        return
    logger.info("tasks::deactivate_route(): initial_status="+str(initial_status))
        
    announce("[%s] Suspending rule : %s. %sPlease wait..." % (route.applier_username_nice, route.name_visible, reason_text), route.applier, route)

    applier = PR.Applier(route_object=route)
    # Delete from router via NETCONF
    commit, response = applier.apply(operation="delete")
    #reason_text = ''
    logger.info("tasks::deactivate_route(): commit="+str(commit))
    if commit:
        route.status="INACTIVE"
        try:
            snmp_add_initial_zero_value(str(route.id), False)
        except Exception as e:
            logger.error("tasks::deactivate_route(): route="+str(route)+", INACTIVE, add_null_value failed: "+str(e))

        announce("[%s] Suspending rule : %s%s- Result %s" % (route.applier_username_nice, route.name_visible, reason_text, response), route.applier, route)
        route.status = "INACTIVE"
        route.response = response
        route.save()
        route.commit_deactivate()
        return
    
    else:
        # removing rule in NETCONF failed, it is still ACTIVE and also collects statistics
        # NETCONF "delete" operation failed, keep the object in DB
        if response=="Task timeout" and deactivate_route.request.retries < settings.NETCONF_MAX_RETRY_BEFORE_ERROR:
            # repeat the action
            raise TimeoutError()
        else:
            if "reason" in kwargs and kwargs['reason'] == 'EXPIRED':
                status = 'EXPIRED'
                reason_text = " Reason: %s " % status
            else:
                status = "ERROR"
            route.status = status
            route.response = response
            route.save()
            announce("[%s] Suspending rule : %s%s- Result %s" % (route.applier_username_nice, route.name_visible, reason_text, response), route.applier, route)

@shared_task(ignore_result=True, autoretry_for=(TimeoutError, TimeLimitExceeded, SoftTimeLimitExceeded), retry_backoff=True, retry_kwargs={'max_retries': settings.NETCONF_MAX_RETRY_BEFORE_ERROR})
def delete_route(routepk, **kwargs):
    """For Route in ACTIVE state, deactivate it at first. Finally, delete the Route from the DB. Permissions must be checked before this call."""
    from flowspec.models import Route
    route = Route.objects.get(pk=routepk)
    logger.info("tasks::delete_route(): initial route.status="+str(route.status))
    if route.status != "INACTIVE" and route.status != "EXPIRED":
        logger.info("Deactivating active route...")
        # call deactivate_route() directly since we are already on background (celery task)
        try:
            deactivate_route(routepk)
            route = Route.objects.get(pk=routepk)
        except TimeoutError:
            pass
        except Exception as e:
            logger.info("tasks::delete_route(): exception during deactivate_route: "+str(e))
        logger.info("tasks::delete_route(): deactivate_route done => route.status="+str(route.status))
        if route.status != "INACTIVE" and route.status != "EXPIRED" and delete_route.request.retries < settings.NETCONF_MAX_RETRY_BEFORE_ERROR:
            # Repeat due to error in deactivation
            route.status = "PENDING"
            route.save()
            if True:
              logger.error("Deactivation failed, repeat the deletion process.")
              raise TimeoutError()
            
    if route.status == "INACTIVE" or route.status == "EXPIRED":
        announce("[%s] Deleting inactive rule : %s" % (route.applier_username_nice, route.name_visible), route.applier, route)
        logger.info("Deleting inactive route...")
        route.delete()
        logger.info("Deleting finished.")
    else:
        route.status = "ERROR"
        route.save()
        logger.error("Deleting Route failed, it could not be deactivated - remaining in DB.")
    return

# May not work in the first place... proxy is not aware of Route models
@shared_task
def batch_delete(routes, **kwargs):
    if routes:
        for route in routes:
            route.status = 'PENDING';route.save()
        applier = PR.Applier(route_objects=routes)
        conf = applier.delete_routes()
        commit, response = applier.apply(configuration=conf)
        reason_text = ''
        if commit:
            status = "INACTIVE"
            if "reason" in kwargs and kwargs['reason'] == 'EXPIRED':
                status = 'EXPIRED'
                reason_text = " Reason: %s " % status
            elif "reason" in kwargs and kwargs['reason'] != 'EXPIRED':
                status = kwargs['reason']
                reason_text = " Reason: %s " % status
        else:
            status = "ERROR"
        for route in routes:
            route.status = status
            route.response = response
            route.expires = datetime.date.today()
            route.save()
            announce("[%s] Rule removal: %s%s- Result %s" % (route.applier_username_nice, route.name_visible, reason_text, response), route.applier, route)
    else:
        return False


@shared_task(ignore_result=True)
def announce(messg, user, route):

  route_dict = model_to_dict(route)
  rule_changelog_logger.info(messg+" route_dict="+str(route_dict))

  try:
    if user!=None:
      #peers = user.userprofile.peers.all()
      peers = Peer.objects.all()
      username = user.username
    else:
      peers = Peer.objects.all()
      username = None

    visited_channel = {}
    tgt_net = ip_network(route.destination, strict=False)
    for peer in peers:
        for network in peer.networks.all():
            net = ip_network(network, strict=False)
            #logger.info("ANNOUNCE check ip " + str(tgt_net) + str(type(tgt_net)) + " in net " + str(net) + str(type(net)))
            # check if the target is a subnet of peer range (python3.6 doesn't have subnet_of())
            try:
              if tgt_net.version==net.version and tgt_net.network_address >= net.network_address and tgt_net.broadcast_address <= net.broadcast_address:
                peername = peer.peer_tag
                #logger.info("ANNOUNCE found peer " + str(peername))
                
                #break
                if peername not in visited_channel:
                  logger.info("ANNOUNCE found peer to announce to: " + str(peername))
                  visited_channel[peername]=True
                  announce_redis_lowlevel(messg, peername)
                else:
                  logger.info("ANNOUNCE peer already haveing announced to: " + str(peername))

            except TypeError:
               pass

    #self.announce_redis_lowlevel(messg, username)
  except Exception as e:
    logger.error("tasks::announce(): got excention e: " + str(e), exc_info=True)


@shared_task(ignore_result=True)
def announce_redis_lowlevel(messg, channelname):
    messg = str(messg)
    logger.info("ANNOUNCE " + messg)
    r = redis.StrictRedis()
    key = "notifstream_%s" % channelname
    obj = {"m": messg, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    logger.info("ANNOUNCE " + str(obj))
    lastid = r.xadd(key, obj, maxlen=settings.NOTIF_STREAM_MAXSIZE, approximate=False)
    logger.info("ANNOUNCE key " + key + " with lastid " + lastid.decode("utf-8"))
    r.expire(key, settings.NOTIF_STREAM_MAXLIFE)

@shared_task(ignore_result=True,default_retry_delay=5,max_retries=2,autoretry_for=(TimeLimitExceeded, SoftTimeLimitExceeded))
def check_sync(route_name=None, selected_routes=[]):
    from flowspec.models import Route
    if not selected_routes:
        routes = Route.objects.all()
    else:
        routes = selected_routes
    if route_name:
        routes = routes.filter(name=route_name)

    try:
      logger.info("tasks::check_sync(): making single query whose result is to be used during loop processing")
      get_device = PR.Retriever()
      device = get_device.fetch_device()
    except Exception as e:
      logger.info("tasks::check_sync(): exception occured during get active routes on router: "+str(e))
      return

    for route in routes:
        if route.has_expired() and (route.status != 'EXPIRED' and route.status != 'ADMININACTIVE' and route.status != 'INACTIVE' and route.status != 'INACTIVE_TODELETE' and route.status != 'PENDING_TODELETE'):
            if route.status != 'ERROR':
                logger.info('Expiring %s route %s' %(route.status, route.name))
                subtask(deactivate_route).delay(str(route.id), reason="EXPIRED")
        else:
            if route.status != 'EXPIRED':
                old_status = route.status
                route.check_sync(netconf_device_queried=device)
                new_status = route.status
                if old_status != new_status:
                  logger.info('status of rule changed during check_sync %s : %s -> %s' % (route.name, old_status, new_status))
                  announce("[%s] Rule status change after sync check: %s - Result: %s" % ("-", route.name_visible, ""), route.applier, route)


@shared_task(ignore_result=True)
def notify_expired():
    from flowspec.models import Route
    from django.contrib.sites.models import Site
    logger.info('Initializing expiration notification')
    routes = Route.objects.all()
    for route in routes:
        if route.status not in ['EXPIRED', 'ADMININACTIVE', 'INACTIVE', 'INACTIVE_TODELETE', 'PENDING_TODELETE', 'ERROR']:
            expiration_days = (route.expires - datetime.date.today()).days
            if expiration_days < settings.EXPIRATION_NOTIFY_DAYS:
                try:
                    fqdn = Site.objects.get_current().domain
                    admin_url = "https://%s%s" % \
                    (fqdn,
                     "/edit/%s"%route.name)
                    mail_body = render_to_string("rule_action.txt",
                                             {"route": route, 'expiration_days':expiration_days, 'action':'expires', 'url':admin_url})
                    days_num = ' days'
                    expiration_days_text = "%s %s" %('in',expiration_days)
                    if expiration_days == 0:
                        days_num = ' today'
                        expiration_days_text = ''
                    if expiration_days == 1:
                        days_num = ' day'
                    logger.info('Route %s expires %s%s. Notifying %s (%s)' %(route.name, expiration_days_text, days_num, route.applier.username, route.applier.email))
                    send_mail(settings.EMAIL_SUBJECT_PREFIX + "Rule %s expires %s%s" %
                              (route.name,expiration_days_text, days_num),
                              mail_body, settings.SERVER_EMAIL,
                              [route.applier.email])
                except Exception as e:
                    logger.error("Exception: %s"%e)
                    pass
    logger.info('Expiration notification process finished')

##############################################################################
##############################################################################
# snmp task handling (including helper functions)

import os
import signal

def handleSIGCHLD(signal, frame):
  logger.info("handleSIGCHLD(): reaping childs")
  os.waitpid(-1, os.WNOHANG)

def snmp_lock_create(wait=0):
    first=1
    success=0
    while first or wait:
      first=0
      try:
          os.mkdir(settings.SNMP_POLL_LOCK)
          logger.debug("snmp_lock_create(): creating lock dir succeeded")
          success=1
          return success
      except OSError as e:
          logger.error("snmp_lock_create(): creating lock dir failed: OSError: "+str(e))
          success=0
      except Exception as e:
          logger.error("snmp_lock_create(): Lock already exists")
          logger.error("snmp_lock_create(): creating lock dir failed: "+str(e))
          success=0
      if not success and wait:
        time.sleep(1)
    return success;

def snmp_lock_remove():
    try:
      os.rmdir(settings.SNMP_POLL_LOCK)
    except Exception as e:
      logger.error("snmp_lock_remove(): failed "+str(e))

def exit_process():
    import sys
    pid = os.getpid()
    logger.info("exit_process(): before exit in child process (pid="+str(pid)+")")
    exit()
    logger.info("exit_process(): before exit in child process (pid="+str(pid)+"), after exit")
    sys.exit()
    logger.info("exit_process(): before exit in child process (pid="+str(pid)+"), after sys.exit")
    os._exit()
    logger.info("exit_process(): before exit in child process (pid="+str(pid)+"), after os._exit")

#@shared_task(ignore_result=True, time_limit=580, soft_time_limit=550)
@shared_task(ignore_result=True, max_retries=0)
def poll_snmp_statistics():
    from flowspec import snmpstats

    if not snmp_lock_create(0):
      return

    signal.signal(signal.SIGCHLD, handleSIGCHLD)

    pid = os.getpid()
    logger.info("poll_snmp_statistics(): before fork (pid="+str(pid)+")")
    npid = os.fork()
    if npid == -1:
      pass
    elif npid > 0:
      logger.info("poll_snmp_statistics(): returning in parent process (pid="+str(pid)+", npid="+str(npid)+")")
    else:
      logger.info("poll_snmp_statistics(): in child process (pid="+str(pid)+", npid="+str(npid)+")")
      try:
        snmpstats.poll_snmp_statistics()        
      except Exception as e:
        logger.error("poll_snmp_statistics(): exception occured in snmp poll (pid="+str(pid)+", npid="+str(npid)+"): "+str(e))
      snmp_lock_remove()
      #exit_process()
      logger.info("exit_process(): before exit in child process (pid="+str(pid)+", npid="+str(npid)+")")
      exit()
      logger.info("exit_process(): before exit in child process (pid="+str(pid)+", npid="+str(npid)+"), after exit")
      import sys
      sys.exit()
      logger.info("exit_process(): before exit in child process (pid="+str(pid)+", npid="+str(npid)+"), after sys.exit")
      os._exit()
      logger.info("exit_process(): before exit in child process (pid="+str(pid)+", npid="+str(npid)+"), after os._exit")

@shared_task(ignore_result=True, max_retries=0)
def snmp_add_initial_zero_value(rule_id, zero_or_null=True):
    from flowspec import snmpstats

    use_fork = False

    if not use_fork:
      snmpstats.add_initial_zero_value(rule_id, zero_or_null)
    else:
      signal.signal(signal.SIGCHLD, handleSIGCHLD)

      pid = os.getpid()
      logger.info("snmp_add_initial_zero_value(): before fork (pid="+str(pid)+" rule_id="+str(rule_id)+","+str(zero_or_null)+")")
      npid = os.fork()
      if npid == -1:
        pass
      elif npid > 0:
        logger.info("snmp_add_initial_zero_value(): returning in parent process (pid="+str(pid)+", npid="+str(npid)+")")
      else:
        logger.info("snmp_add_initial_zero_value(): in child process (pid="+str(pid)+", npid="+str(npid)+")")

        try:
          snmpstats.add_initial_zero_value(rule_id, zero_or_null)
          logger.debug("snmp_add_initial_zero_value(): rule_id="+str(rule_id)+","+str(zero_or_null)+" sucesss")
        except Exception as e:
          logger.error("snmp_add_initial_zero_value(): rule_id="+str(rule_id)+","+str(zero_or_null)+" failed: "+str(e))

        #exit_process()
        logger.info("exit_process(): before exit in child process (pid="+str(pid)+", npid="+str(npid)+")")
        exit()
        logger.info("exit_process(): before exit in child process (pid="+str(pid)+", npid="+str(npid)+"), after exit")
        sys.exit()
        logger.info("exit_process(): before exit in child process (pid="+str(pid)+", npid="+str(npid)+"), after sys.exit")
        os._exit()
        logger.info("exit_process(): before exit in child process (pid="+str(pid)+", npid="+str(npid)+"), after os._exit")


@pytest.mark.skip
@shared_task(ignore_result=True,default_retry_delay=5,max_retries=2,autoretry_for=(TimeoutError,))
def testcelerytask():
    lockname = "/tmp/testlock"
    try:
        os.mkdir(lockname)
        logger.info("testcelerytask: Do something and return")
        return
    except FileExistsError:
        logger.info("testcelerytask: SKipping, raising exception for repeating")
        os.rmdir(lockname)
        raise TimeoutError

