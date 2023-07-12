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

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from flowspec.tasks import *

from flowspec.helpers import send_new_mail, get_peer_techc_mails
from utils.proxy import PR0 as PR
from ipaddress import *
from ipaddress import ip_network
import datetime
import json
from peers.models import PeerRange, Peer

from utils.route_spec_utils import create_junos_name
from utils.flowspec_utils import map__ip_proto__for__ip_version__from_flowspec

#import flowspec.iprange_match
from flowspec.iprange_match import find_matching_peer_by_ipprefix__simple

from utils.randomizer import id_generator as id_gen

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "flowspec_models.log", False)


FRAGMENT_CODES = (
    ("dont-fragment", "Don't fragment"),
    ("first-fragment", "First fragment"),
    ("is-fragment", "Is fragment"),
    ("last-fragment", "Last fragment"),
    ("not-a-fragment", "Not a fragment")
)

THEN_CHOICES = (
    ("accept", "Accept"),
    ("discard", "Discard"),
    ("community", "Community"),
    ("next-term", "Next term"),
    ("routing-instance", "Routing Instance"),
    ("rate-limit", "Rate limit"),
    ("sample", "Sample")
)

MATCH_PROTOCOL = (
    ("ah", "ah"),
    ("egp", "egp"),
    ("esp", "esp"),
    ("gre", "gre"),
    ("icmp", "icmp"),
    ("icmp6", "icmp6"),
    ("igmp", "igmp"),
    ("ipip", "ipip"),
    ("ospf", "ospf"),
    ("pim", "pim"),
    ("rsvp", "rsvp"),
    ("sctp", "sctp"),
    ("tcp", "tcp"),
    ("udp", "udp"),
)

ROUTE_STATES = (
    ("ACTIVE", "ACTIVE"),
    ("ERROR", "ERROR"),
    ("EXPIRED", "EXPIRED"),
    ("PENDING", "PENDING"),
    ("PENDING_TODELETE", "PENDING_TODELETE"),
    ("OUTOFSYNC", "OUTOFSYNC"),
    ("INACTIVE", "INACTIVE"),
    ("INACTIVE_TODELETE", "INACTIVE_TODELETE"),
    ("ADMININACTIVE", "ADMININACTIVE"),
)


#def days_offset(): return datetime.date.today() + datetime.timedelta(days = settings.EXPIRATION_DAYS_OFFSET)
def days_offset(): return datetime.date.today() + datetime.timedelta(days = settings.EXPIRATION_DAYS_OFFSET-1)

class MatchPort(models.Model):
    port = models.CharField(max_length=24, unique=True)
    def __unicode__(self):
        return self.port
    def __str__(self):
        return self.__unicode__()
    class Meta:
        db_table = u'match_port'

class MatchDscp(models.Model):
    dscp = models.CharField(max_length=24)
    def __unicode__(self):
        return self.dscp
    def __str__(self):
        return self.__unicode__()
    class Meta:
        db_table = u'match_dscp'

class MatchProtocol(models.Model):
    protocol = models.CharField(max_length=24, unique=True)
    def __unicode__(self):
        return self.protocol
    def __str__(self):
        return self.__unicode__()
    def __eq__(self, b):
        if self.protocol == b.protocol:
            return True
        else:
            return super().__eq__(b)
    class Meta:
        db_table = u'match_protocol'

class FragmentType(models.Model):
    fragmenttype = models.CharField(max_length=20, choices=FRAGMENT_CODES, verbose_name="Fragment Type")

    def __unicode__(self):
        return "%s" %(self.fragmenttype)

    def __str__(self):
        return self.__unicode__()


class ThenAction(models.Model):
    action = models.CharField(max_length=60, choices=THEN_CHOICES, verbose_name="Action")
    action_value = models.CharField(max_length=255, blank=True, null=True, verbose_name="Action Value")

    def __unicode__(self):
        ret = "%s:%s" %(self.action, self.action_value)
        return ret.rstrip(":")

    def __str__(self):
        return self.__unicode__()

    class Meta:
        db_table = u'then_action'
        ordering = ['action', 'action_value']
        unique_together = ("action", "action_value")


class Route(models.Model):
    name = models.SlugField(max_length=128, verbose_name=_("Name"))
    #applier = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    applier = models.ForeignKey(User, blank=True, null=True, on_delete=models.DO_NOTHING)
    source = models.CharField(max_length=45+4, help_text=_("Network address. Use address/CIDR notation"), verbose_name=_("Source Address"))
    sourceport = models.TextField(blank=True, null=True, verbose_name=_("Source Port"))
    destination = models.CharField(max_length=45+4, help_text=_("Network address. Use address/CIDR notation"), verbose_name=_("Destination Address"))
    destinationport = models.TextField(blank=True, null=True, verbose_name=_("Destination Port"))
    port = models.TextField(blank=True, null=True, verbose_name=_("Port"))
    dscp = models.ManyToManyField(MatchDscp, blank=True, verbose_name="DSCP")
    fragmenttype = models.ManyToManyField(FragmentType, blank=True, verbose_name="Fragment Type")
    icmpcode = models.CharField(max_length=32, blank=True, null=True, verbose_name="ICMP Code")
    icmptype = models.CharField(max_length=32, blank=True, null=True, verbose_name="ICMP Type")
    packetlength = models.IntegerField(blank=True, null=True, verbose_name="Packet Length")
    protocol = models.ManyToManyField(MatchProtocol, blank=True, verbose_name=_("Protocol"))
    tcpflag = models.CharField(max_length=128, blank=True, null=True, verbose_name="TCP flag")
    then = models.ManyToManyField(ThenAction, verbose_name=_("Then"))
    filed = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=ROUTE_STATES, blank=True, null=True, verbose_name=_("Status"), default="PENDING")
#    is_online = models.BooleanField(default=False)
#    is_active = models.BooleanField(default=False)
    #expires = models.DateField(default=days_offset, verbose_name=_("Expires"))
    expires = models.DateField(default=days_offset, verbose_name=_("Expires"))
    response = models.CharField(max_length=512, blank=True, null=True, verbose_name=_("Response"))
    comments = models.TextField(null=True, blank=True, verbose_name=_("Comments"))
    requesters_address = models.CharField(max_length=255, blank=True, null=True)

    @property
    def name_visible(self):
        l = len(settings.RULE_NAME_PREFIX)
        prefix = self.name[0:l]
        if prefix==settings.RULE_NAME_PREFIX:
          return self.name[l:len(self.name)]
        else:
          return self.name

    @property
    def applier_username(self):
        if self.applier:
            return self.applier.username
        else:
            return None

    @property
    def applier_username_nice(self):
        if self.applier:
            if self.applier.first_name or self.applier.last_name:
                fn = self.applier.first_name if self.applier.first_name else ""
                ln = self.applier.last_name if self.applier.last_name else ""
                ret = "{0} {1}".format(fn, ln).strip()
            elif self.applier.email:
                ret = self.applier.email
            else:
                ret = self.applier.username
            return ret
        else:
            return None

    def ip_version(self):
            
        route_obj = self

        source_ip_version = 4
        destination_ip_version = 4
        try:
          source_ip_version = ip_network(route_obj.source, strict=False).version
          destination_ip_version = ip_network(route_obj.destination, strict=False).version
        except Exception as e:
          logger.error("model::route::ip_version(): exception in trying to determine ip_version: "+str(e))
        pass

        #logger.debug("model::route::ip_version(): source_ip_version="+str(source_ip_version)+" destination_ip_version="+str(destination_ip_version))
        if source_ip_version != destination_ip_version:
          logger.error("model::route::ip_version(): source_ip_version="+str(source_ip_version)+" != destination_ip_version="+str(destination_ip_version))
          return -1

        ip_version = source_ip_version and destination_ip_version
        #logger.debug("model::route::ip_version(): ip_version="+str(ip_version))

        return ip_version
    
    def is_ipv4(self):
        return self.ip_version()==4


    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.__unicode__()

    class Meta:
        db_table = u'route'
        verbose_name = "Rule"
        verbose_name_plural = "Rules"

    def save(self, *args, **kwargs):
        if not self.pk:
            suff = id_gen()
            #self.name = "%s_%s" % (self.name, suff)
            self.name = "%s%s_%s" % (settings.RULE_NAME_PREFIX, self.name, suff)
        super(Route, self).save(*args, **kwargs)

    def clean(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        if self.destination:
            try:
                address = ip_network(self.destination, strict=False)
                self.destination = address.exploded
            except Exception:
                raise ValidationError(_('Invalid network address format at Destination Field'))
        if self.source:
            try:
                address = ip_network(self.source, strict=False)
                self.source = address.exploded
            except Exception:
                raise ValidationError(_('Invalid network address format at Source Field'))

    def commit_add(self, *args, **kwargs):
        peers = self.applier.userprofile.peers.all()

        #username = None
        #for peer in peers:
        #    if username:
        #        break
        #    for network in peer.networks.all():
        #        net = ip_network(network, strict=False)
        #        if ip_network(self.destination, strcit=False) in net:
        #            username = peer
        #            break
        username = find_matching_peer_by_ipprefix__simple(peers, self.destination)

        if username:
            peer = username.peer_tag
        else:
            peer = None

        send_message("[%s] Adding rule %s. Please wait..." % (self.applier_username_nice, self.name_visible), peer, self)
        response = add.delay(self.pk)
        logger.info('Got add job id: %s' % response)
        if not settings.DISABLE_EMAIL_NOTIFICATION:
            fqdn = Site.objects.get_current().domain
            admin_url = 'https://%s%s' % (
                fqdn,
                reverse('edit-route', kwargs={'route_slug': self.name})
            )
            mail_body = render_to_string(
                'rule_action.txt',
                {
                    'route': self,
                    'address': self.requesters_address,
                    'action': 'creation',
                    'url': admin_url,
                    'peer': username
                }
            )
            user_mail = '%s' % self.applier.email
            user_mail = user_mail.split(';')
            send_new_mail(
                settings.EMAIL_SUBJECT_PREFIX + 'Rule %s creation request submitted by %s' % (self.name, self.applier_username_nice),
                mail_body,
                settings.SERVER_EMAIL, user_mail,
                get_peer_techc_mails(self.applier, username)
            )
            d = {
                'clientip': '%s' % self.requesters_address,
                'user': self.applier.username
            }
            logger.info(mail_body, extra=d)

    def commit_edit(self, *args, **kwargs):
        peers = self.applier.userprofile.peers.all()

        route_original = kwargs['route_original']
        logger.info("models::commit_edit(): self="+str(self)+" route_original="+str(route_original)+" kwargs="+str(kwargs))

        #username = None
        #for peer in peers:
        #    if username:
        #        break
        #    for network in peer.networks.all():
        #        net = ip_network(network, strict=False)
        #        if ip_network(self.destination, strict=False) in net:
        #            username = peer
        #            break
        username = find_matching_peer_by_ipprefix__simple(peers, self.destination)

        if username:
            peer = username.peer_tag
        else:
            peer = None

        send_message('[%s] Editing rule %s. Please wait...' % (self.applier_username_nice, self.name_visible), peer, self)
        response = edit.delay(self.pk, route_original)
        logger.info('Got edit job id: %s' % response)
        if not settings.DISABLE_EMAIL_NOTIFICATION:
            fqdn = Site.objects.get_current().domain
            admin_url = 'https://%s%s' % (
                fqdn,
                reverse(
                    'edit-route',
                    kwargs={'route_slug': self.name}
                )
            )
            mail_body = render_to_string(
                'rule_action.txt',
                {
                    'route': self,
                    'address': self.requesters_address,
                    'action': 'edit',
                    'url': admin_url,
                    'peer': username
                }
            )
            user_mail = '%s' % self.applier.email
            user_mail = user_mail.split(';')
            send_new_mail(
                settings.EMAIL_SUBJECT_PREFIX + 'Rule %s edit request submitted by %s' % (self.name, self.applier_username_nice),
                mail_body, settings.SERVER_EMAIL, user_mail,
                get_peer_techc_mails(self.applier, username)
            )
            d = {
                'clientip': self.requesters_address,
                'user': self.applier.username
            }
            logger.info(mail_body, extra=d)

    def commit_deactivate(self, *args, **kwargs):
        username = None

        reason_text = ''
        reason = ''
        if "reason" in kwargs:
            reason = kwargs['reason']
            reason_text = 'Reason: %s.' % reason

        peers = self.applier.userprofile.peers.all()

        #for peer in peers:
        #    if username:
        #        break
        #    for network in peer.networks.all():
        #        net = ip_network(network, strict=False)
        #        if ip_network(self.destination, strict=False) in net:
        #            username = peer
        #            break
        username = find_matching_peer_by_ipprefix__simple(peers, self.destination)

        if username:
            peer = username.peer_tag
        else:
            peer = None
        #send_message(
        #    '[%s] Suspending rule %s. %sPlease wait...' % (
        #        self.applier_username_nice,
        #        self.name_visible,
        #        reason_text
        #    ), 
        #    peer, self
        #)
        if not settings.DISABLE_EMAIL_NOTIFICATION:
            fqdn = Site.objects.get_current().domain
            admin_url = 'https://%s%s' % (
                fqdn,
                reverse(
                    'edit-route',
                    kwargs={'route_slug': self.name}
                )
            )
            mail_body = render_to_string(
                'rule_action.txt',
                {
                    'route': self,
                    'address': self.requesters_address,
                    'action': 'removal',
                    'url': admin_url,
                    'peer': username
                }
            )
            user_mail = '%s' % self.applier.email
            user_mail = user_mail.split(';')
            send_new_mail(
                settings.EMAIL_SUBJECT_PREFIX + 'Rule %s removal request submitted by %s' % (self.name, self.applier_username_nice),
                mail_body,
                settings.SERVER_EMAIL,
                user_mail,
                get_peer_techc_mails(self.applier, username)
            )
            d = {
                'clientip': self.requesters_address,
                'user': self.applier.username
            }
            logger.info(mail_body, extra=d)

    def has_expired(self):
        today = datetime.date.today()
        if today > self.expires:
            return True
        return False

    @property
    def is_no_expire(self):
        """Return True if route expires in more than 50 years"""
        return self.expires - datetime.timedelta(days=365*50) > datetime.date.today()

    def set_no_expire(self):
        """Used for REST API created routes that should have no expiration date"""
        self.expires = datetime.date.today() + datetime.timedelta(days=365*100) 

    def update_status(self, new_status):
        if self.status!=new_status:
          logger.info('models::route::update_status(): id='+str(self.id))
          self.status = new_status
          self.save()

    def check_sync(self, cached_routes=None):
        if not self.is_synced(cached_routes=cached_routes):
            #self.status = "OUTOFSYNC"
            #self.save()
            self.update_status("OUTOFSYNC")

    def is_synced(self, cached_routes=None):
        found = False
              
        retriever = PR.Retriever()
        try:
            # allows for caching of current routes, e.g., during tasks::check_sync
            if cached_routes==None:
              logger.info("models::is_synced(): querying routes newly from router")
              routes = retriever.retrieve_current_routes__globally_cached()
            else:
              logger.info("models::is_synced(): reusing cached routes")
              routes = cached_routes
        except Exception as e:
            #self.status = "EXPIRED"
            #self.save()
            self.update_status("EXPIRED")
            logger.error('models::is_synced(): no routing options on device. Exception: %s' % e)
            return True
        
        logger.info("models::is_synced(): routes="+str(routes))

        retriever_supports__named_routes = retriever.supports__named_routes()

        if not retriever_supports__named_routes:
          logger.info("models::is_synced(): retriever_supports__named_routes="+str(retriever_supports__named_routes)+", so check_sync is not supported")
          return True # assume synced

        my_ip_version = self.ip_version()

        if routes:
          for route in routes:
            logger.debug('models::is_synced(): loop routes self='+str(self))
            logger.debug('models::is_synced(): loop routes route='+str(route))
            logger.debug('models::is_synced(): loop routes')
            if not retriever_supports__named_routes or route.name == self.name:
                found = True
                logger.debug('models::is_synced(): Found a matching rule name')

                if hasattr(route, 'match'): # unfold match part if it exists, otherwisse assume flat attribute space
                  match = route.match
                else:
                  match = route

                try:
                    assert(self.destination)
                    assert(match['destination'][0])
                    if self.destination == match['destination'][0]:
                        found = found and True
                        logger.debug('models::is_synced(): Found a matching destination')
                    else:
                        found = False
                        logger.info('models::is_synced(): self='+str(self)+': destination fields do not match')
                except:
                    pass
                try:
                    assert(self.source)
                    assert(match['source'][0])
                    if self.source == match['source'][0]:
                        found = found and True
                        logger.debug('models::is_synced(): self='+str(self)+': found a matching source')
                    else:
                        found = False
                        logger.info('models::is_synced(): self='+str(self)+': source fields do not match')
                except:
                    pass

                try:
                    assert(self.fragmenttype.all())
                    assert(match['fragment'])
                    devitems = match['fragment']
                    dbitems = ["%s"%i for i in self.fragmenttype.all()]
                    intersect = list(set(devitems).intersection(set(dbitems)))
                    if ((len(intersect) == len(dbitems)) and (len(intersect) == len(devitems))):
                        found = found and True
                        logger.debug('models::is_synced(): self='+str(self)+': found a matching fragment type')
                    else:
                        found = False
                        logger.info('models::is_synced(): self='+str(self)+': fragment type fields do not match')
                except:
                    pass

                try:
                    assert(self.port.all())
                    assert(match['port'])
                    devitems = match['port']
                    dbitems = ["%s"%i for i in self.port.all()]
                    intersect = list(set(devitems).intersection(set(dbitems)))
                    if ((len(intersect) == len(dbitems)) and (len(intersect) == len(devitems))):
                        found = found and True
                        logger.debug('models::is_synced(): self='+str(self)+': found a matching port type')
                    else:
                        found = False
                        logger.info('models::is_synced(): self='+str(self)+': port type fields do not match')
                except:
                    pass

                try:
                    assert(self.protocol.all())
                    assert(match['protocol'])
                    devitems = match['protocol']
                    #dbitems = ["%s"%i for i in self.protocol.all()]
                    dbitems = [map__ip_proto__for__ip_version__to_flowspec(my_ip_version, "%s"%i) for i in self.protocol.all()]
                    #logger.info("models::is_synced(): dbitems="+str(dbitems))

                    intersect = list(set(devitems).intersection(set(dbitems)))
                    if ((len(intersect) == len(dbitems)) and (len(intersect) == len(devitems))):
                        found = found and True
                        logger.debug('models::is_synced(): self='+str(self)+': found a matching protocol type')
                    else:
                        found = False
                        logger.info('models::is_synced(): self='+str(self)+': protocol type fields do not match')
                except:
                    pass

                try:
                    assert(self.destinationport.all())
                    assert(match['destination-port'])
                    devitems = match['destination-port']
                    dbitems = ["%s"%i for i in self.destinationport.all()]
                    intersect = list(set(devitems).intersection(set(dbitems)))
                    if ((len(intersect) == len(dbitems)) and (len(intersect) == len(devitems))):
                        found = found and True
                        logger.debug('models::is_synced(): self='+str(self)+': found a matching destination port type')
                    else:
                        found = False
                        logger.info('models::is_synced(): self='+str(self)+': destination port type fields do not match')
                except:
                    pass

                try:
                    assert(self.sourceport.all())
                    assert(match['source-port'])
                    devitems = match['source-port']
                    dbitems = ["%s"%i for i in self.sourceport.all()]
                    intersect = list(set(devitems).intersection(set(dbitems)))
                    if ((len(intersect) == len(dbitems)) and (len(intersect) == len(devitems))):
                        found = found and True
                        logger.debug('models::is_synced(): self='+str(self)+': found a matching source port type')
                    else:
                        found = False
                        logger.info('models::is_synced(): self='+str(self)+': source port type fields do not match')
                except:
                    pass


#                try:
#                    assert(self.fragmenttype)
#                    assert(devicematch['fragment'][0])
#                    if self.fragmenttype == devicematch['fragment'][0]:
#                        found = found and True
#                        logger.debug('self='+str(self)+': found a matching fragment type')
#                    else:
#                        found = False
#                        logger.info('models::is_synced(): self='+str(self)+': fragment type fields do not match')
#                except:
#                    pass
                try:
                    assert(self.icmpcode)
                    assert(match['icmp-code'][0])
                    if self.icmpcode == match['icmp-code'][0]:
                        found = found and True
                        logger.debug('models::is_synced(): self='+str(self)+': found a matching icmp code')
                    else:
                        found = False
                        logger.info('models::is_synced(): self='+str(self)+': icmp code fields do not match')
                except:
                    pass
                try:
                    assert(self.icmptype)
                    assert(match['icmp-type'][0])
                    if self.icmptype == match['icmp-type'][0]:
                        found = found and True
                        logger.debug('models::is_synced(): self='+str(self)+': found a matching icmp type')
                    else:
                        found = False
                        logger.info('models::is_synced(): self='+str(self)+': icmp type fields do not match')
                except:
                    pass

                if found and self.status != "ACTIVE":
                    logger.error('models::is_synced(): rule '+str(self)+' is applied on device but appears in DB as offline')
                    #self.status = "ACTIVE"
                    #self.save()
                    self.update_status("ACTIVE")
                    found = True

        logger.info('models::is_synced(): self='+str(self)+ " status="+str(self.status)+" pre found="+str(found))
        if not found and (self.status == "ADMININACTIVE" or self.status == "INACTIVE" or self.status == "INACTIVE_TODELETE" or self.status == "PENDING_TODELETE" or self.status == "EXPIRED"):
          found = True
        
        logger.info('models::is_synced(): self='+str(self)+ " => returning found="+str(found))
        return found

    def get_then(self):
        ret = ''
        then_statements = self.then.all()
        for statement in then_statements:
            if statement.action_value:
                ret = "%s %s %s" %(ret, statement.action, statement.action_value)
            else:
                ret = "%s %s" %(ret, statement.action)
        return ret

    get_then.short_description = 'Then statement'
    get_then.allow_tags = True
#

    def get_match(self):
        ret = '<dl class="dl-horizontal">'
        if self.destination:
            ret = '%s <dt>Dst Addr</dt><dd>%s</dd>' %(ret, self.destination)
        if self.fragmenttype.all():
            ret = ret + "<dt>Fragment Types</dt><dd>%s</dd>" %(', '.join(["%s"%i for i in self.fragmenttype.all()]))
#            for fragment in self.fragmenttype.all():
#                    ret = ret + "Fragment Types:<strong>%s</dd>" %(fragment)
        if self.icmpcode:
            ret = "%s <dt>ICMP code</dt><dd>%s</dd>" %(ret, self.icmpcode)
        if self.icmptype:
            ret = "%s <dt>ICMP Type</dt><dd>%s</dd>" %(ret, self.icmptype)
        if self.packetlength:
            ret = "%s <dt>Packet Length</dt><dd>%s</dd>" %(ret, self.packetlength)
        if self.source:
            ret = "%s <dt>Src Addr</dt><dd>%s</dd>" %(ret, self.source)
        if self.tcpflag:
            ret = "%s <dt>TCP flag</dt><dd>%s</dd>" %(ret, self.tcpflag)
        if self.port:
            ret = ret + "<dt>Ports</dt><dd>%s</dd>" %(self.port)
#            for port in self.port.all():
#                    ret = ret + "Port:<strong>%s</dd>" %(port)
        if self.protocol.all():
            ret = ret + "<dt>Protocols</dt><dd>%s</dd>" %(', '.join(["%s"%i for i in self.protocol.all()]))
#            for protocol in self.protocol.all():
#                    ret = ret + "Protocol:<strong>%s</dd>" %(protocol)
        if self.destinationport:
            ret = ret + "<dt>DstPorts</dt><dd>%s</dd>" %(self.destinationport)
#            for port in self.destinationport.all():
#                    ret = ret + "Dst Port:<strong>%s</dd>" %(port)
        if self.sourceport:
            ret = ret + "<dt>SrcPorts</dt><dd>%s</dd>" %(self.sourceport)
#            for port in self.sourceport.all():
#                    ret = ret +"Src Port:<strong>%s</dd>" %(port)
        if self.dscp:
            for dscp in self.dscp.all():
                    ret = ret + "%s <dt>Port</dt><dd>%s</dd>" %(ret, dscp)
        ret = ret + "</dl>"
        return ret

    get_match.short_description = 'Match statement'
    get_match.allow_tags = True

    @property
    def applier_peers(self):
        try:
            peers = self.applier.userprofile.peers.all()
            applier_peers = ''.join(('%s, ' % (peer.peer_name)) for peer in peers)[:-2]
        except:
            applier_peers = None
        return applier_peers

    # perf has to be checked:
    @property 
    def containing_peer_ranges(self):
        try:
            destination_network = ip_network(self.destination, strict=False)
            logger.info("containing_peer_ranges(): destination_network="+str(destination_network))
            #logger.info("containing_peer_ranges(): peers all="+str(PeerRange.objects.all()))
            #containing_peer_ranges = PeerRange.objects.filter(network__contains(destination_network))
            #containing_peer_ranges = [obj for obj in PeerRange.objects.all() if ip_network(obj.network).__contains__(destination_network)]
            containing_peer_ranges = [obj for obj in PeerRange.objects.all() if destination_network.version==ip_network(obj.network, strict=False).version and ip_network(obj.network, strict=False).network_address <= destination_network.network_address and ip_network(obj.network, strict=False).broadcast_address >= destination_network.broadcast_address ]
            logger.info("containing_peer_ranges(): containing_peer_ranges="+str(containing_peer_ranges))
        except Exception as e:
            logger.info("containing_peer_ranges(): exception occured: "+str(e))
            #containing_peer_ranges = None
            containing_peer_ranges = []
        return containing_peer_ranges

    # perf has to be checked:
    def containing_peers(self):
        containing_peer_ranges2 = set(self.containing_peer_ranges)
        logger.info("containing_peers(): containing_peer_ranges="+str(containing_peer_ranges2))
        #return [obj.peer for obj in containing_peer_ranges2]
        return [obj for obj in Peer.objects.all() if len(set(obj.networks.all()).intersection(containing_peer_ranges2))>0]

    def containing_ip_networks(self, ip_ranges):
        try:
            ip_networks = [ip_network(ip_range, strict=False) for ip_range in ip_ranges]
            containing_ip_networks = [ip_net for ip_net in ip_networks if destination_network.version==ip_net.version and ip_net.network_address <= destination_network.network_address and ip_net.broadcast_address >= destination_network.broadcast_address ]
        except Exception as e:
            logger.info("containing_ip_networks(): exception occured: "+str(e))
            containing_ip_networks = []
        return containing_ip_networks

    @property
    def days_to_expire(self):
        if self.status not in ['EXPIRED', 'ADMININACTIVE', 'ERROR', 'INACTIVE', 'INACTIVE_TODELETE', 'PENDING_TODELETE']:
            expiration_days = (self.expires - datetime.date.today()).days
            if expiration_days < settings.EXPIRATION_NOTIFY_DAYS:
                return "%s" %expiration_days
            else:
                return False
        else:
            return False

    @property
    def junos_name(self):
        return create_junos_name(self)

    def get_absolute_url(self):
        return reverse('route-details', kwargs={'route_slug': self.name})

##

def send_message(msg, peer, route):
    ##    username = user.username
    ##b = beanstalkc.Connection()
    ##b.use(settings.POLLS_TUBE)
    #tube_message = json.dumps({'message': str(msg), 'username': peer})
    ##b.put(tube_message)
    ##b.close()

    # use new announce method in tasks.py
    announce(msg, peer, route)

#############################################################################
#############################################################################
# global helpers 

# class1's attribute 'id' should be existing and be the primary key, e.g., be a Django model class
def convert_container_to_queryset(list1, class1):
         #temp1_ids = [obj.id for obj in list1]
         temp1_ids = [obj.id for obj in list1 if obj != None]
         temp2_ids = set(temp1_ids)
         return class1.objects.filter(id__in=temp2_ids)

#############################################################################
#############################################################################

