from ipaddress import ip_network
import datetime
from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import ugettext as _
from peers.models import PeerRange, Peer
from flowspec.models import Route, MatchProtocol
from django.urls import reverse

import os
import logging
FORMAT = '%(asctime)s %(levelname)s: %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
LOG_FILENAME = os.path.join(settings.LOG_FILE_LOCATION, 'mylog.log')
handler = logging.FileHandler(LOG_FILENAME)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def get_network(ip):
    try:
        address = ip_network(ip)
    except ValueError as e:
        logger.info("validators::get_network(): ip="+str(ip)+" got exception type="+str(type(e))+" :"+str(e))
        return (False, _('Invalid network address format: '+str(e)))
    except Exception as e:
        logger.info("validators::get_network(): ip="+str(ip)+" got exception type="+str(type(e))+" :"+str(e))
        return (False, _('Invalid network address format'))
    else:
        return (True, address)


def clean_ip(address):
    if False and address.is_private:
            return _('Private addresses not allowed')

    #if address.version == 4 and int(address.prefixlen) == 32:
    #    if int(address.network_address.compressed.split('.')[-1]) == 0:
    #        return _('Malformed address format. Cannot be ...0/32')
    #    elif int(address.network.compressed.split('.')[-1]) == 255:
    #        return _('Malformed address format. Cannot be ...255/32')


def clean_status(status):
    """
    Verifies the `status` of a `Route` is valid.
    Only allows `ACTIVE` / `INACTIVE` states since the rest should be
    assigned from the application

    :param status: the status of a `Route`
    :type status: str

    :returns: Either the status or a validation error message
    :rtype: str
    """

    allowed_states = ['ACTIVE', 'INACTIVE', 'INACTIVE_TODELETE']

    if status not in allowed_states:
        return _('Invalid status value. You are allowed to use "{}".'.format(
            ', '.join(allowed_states)))
    return status


def clean_source(user, source):
    success, address = get_network(source)
    if not success:
        return address
    for net in settings.PROTECTED_SUBNETS:
        if address in ip_network(net):
            mail_body = "User %s %s attempted to set %s as the source address in a firewall rule" % (user.username, user.email, source)
            send_mail(
                settings.EMAIL_SUBJECT_PREFIX + "Caught an attempt to set a protected IP/network as a source address",
                mail_body,
                settings.SERVER_EMAIL,
                settings.NOTIFY_ADMIN_MAILS,
                fail_silently=True
            )
            return _('You have no authority on this subnet')
    return source


def clean_destination(user, destination):
    success, address = get_network(destination)
    if not success:
        return address
    for net in settings.PROTECTED_SUBNETS:
        if address in ip_network(net):
            mail_body = "User %s %s attempted to set %s as the destination address in a firewall rule" % (user.username, user.email, destination)
            send_mail(
                settings.EMAIL_SUBJECT_PREFIX + "Caught an attempt to set a protected IP/network as the destination address",
                mail_body, settings.SERVER_EMAIL,
                settings.NOTIFY_ADMIN_MAILS,
                fail_silently=True
            )
            return _('You have no authority on this subnet')

    # make sure its a network prefix that
    # can be used, depending on settings.PREFIX_LENGTH

    if ip_network(address).version>4:
      if address.prefixlen < settings.PREFIX_LENGTH_IPV6:
        return _("Currently no IPv6 prefix lengths < %s are allowed") % settings.PREFIX_LENGTH_IPV6
    else:
      if address.prefixlen < settings.PREFIX_LENGTH:
        return _("Currently no prefix lengths < %s are allowed") % settings.PREFIX_LENGTH

    # make sure its a valid ip
    error = clean_ip(address)

    # make sure user can apply rule in these networks
    if error:
        return error
    if not user.is_superuser:
        networks = PeerRange.objects.filter(peer__in=user.userprofile.peers.all())
    else:
        networks = PeerRange.objects.filter(peer__in=Peer.objects.all()).distinct()
    network_is_mine = False
    dest_net = ip_network(destination)
    for network in networks:
        net = ip_network(network.network)

        if dest_net.network_address in net and dest_net.prefixlen >= net.prefixlen:
            network_is_mine = True
    if not network_is_mine:
        return (_('Destination address/network should belong to your administrative address space. Check My Profile to review your networks'))
    return destination


def clean_expires(date):
    if date:
        range_days = (date - datetime.date.today()).days
        if range_days > 0 and range_days < settings.MAX_RULE_EXPIRE_DAYS:
            return date
        else:
            return _(
                'Invalid date range. A rule cannot remain active '
                'for more than {} days'.format(settings.MAX_RULE_EXPIRE_DAYS))


def value_list_to_list(valuelist):
    vl = []
    for val in valuelist:
        vl.append(val[0])
    return vl


def get_matchingport_route_pks(portlist, routes):
    route_pk_list = []
    ports_value_list = value_list_to_list(portlist.values_list('port').order_by('port'))
    for route in routes:
        rsp = value_list_to_list(route.destinationport.all().values_list('port').order_by('port'))
        if rsp and rsp == ports_value_list:
            route_pk_list.append(route.pk)
    return route_pk_list


def get_matchingprotocol_route_pks(protocolist, routes):
    route_pk_list = []
    protocols_value_list = value_list_to_list(protocolist.values_list('protocol').order_by('protocol'))
    for route in routes:
        rsp = value_list_to_list(route.protocol.all().values_list('protocol').order_by('protocol'))
        if rsp and rsp == protocols_value_list:
            route_pk_list.append(route.pk)
    return route_pk_list


def clean_route_form(data):
    source = data.get('source', set())
    sourceports = data.get('sourceport', set())
    ports = data.get('port', set())
    then = data.get('then', None)
    destination = data.get('destination', None)
    destinationports = data.get('destinationport', None)
    user = data.get('applier', None)
    fragmenttypes = data.get('fragmenttypes', set())
    protocol = data.get('protocol', set())
    if (sourceports and ports):
        return _('Cannot create rule for source ports and ports at the same time. Select either ports or source ports')
    if (destinationports and ports):
        return _('Cannot create rule for destination ports and ports at the same time. Select either ports or destination ports')
    if sourceports and not source:
        return _('Once source port is matched, source has to be filled as well. Either deselect source port or fill source address')
    if destinationports and not destination:
        return _('Once destination port is matched, destination has to be filled as well. Either deselect destination port or fill destination address')
    if not (source or sourceports or ports or destination or destinationports):
        return _('Fill at least a Rule Match Condition')
    #if (destinationports or sourceports or ports) and not protocol:
    #    return _('Protocol must be specified if ports are given')
    if protocol and MatchProtocol(protocol="icmp") in protocol and (destinationports or sourceports or ports):
        return _('ICMP protocol does not allow to specify ports')
    if not user.is_superuser and then[0].action not in settings.UI_USER_THEN_ACTIONS:
        return _('This action "%s" is not permitted') % (then[0].action)

    return None


def check_if_rule_exists(fields, queryset):
    """
    Checks if a `Route` object with the same source / destination
    addresses exists in a queryset. If not, it checks any `Route`
    object (belonging to any user) exists with the same addresses
    and reports respectively

    :param fields: the source / destination IP addresses
    :type fields: dict

    :param queryset: the queryset with the user's `Route` objects
    :type queryset: `django.db.models.query.QuerySet`

    :returns: if the rule exists or not, a message
    :rtype: tuple(bool, str)
    """

    if hasattr(settings, "ROUTES_DUPLICATES_CHECKING") and settings.ROUTES_DUPLICATES_CHECKING == False:
        return (False, None)
    routes = queryset.filter(
        source=fields.get('source'),
        destination=ip_network(fields.get('destination')).compressed,
    )
    if routes:
        ids = [str(item[0]) for item in routes.values_list('pk')]
        return (
            True, _('Rule(s) regarding those addresses already exist '
                    'with id(s) {}. Please edit those instead'.format(', '.join(ids))))

    routes = Route.objects.filter(
        source=fields.get('source'),
        destination=ip_network(fields.get('destination')).compressed,
    )
    for route in routes:
        return (
            True, _('Rule(s) regarding those addresses already exist '
                    'but you cannot edit them. Please refer to the '
                    'application\'s administrators for further clarification'))
    return (False, None)
