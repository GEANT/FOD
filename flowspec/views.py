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

import json
from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.urls import reverse
from django.contrib import messages
from accounts.models import *
from ipaddress import *
from django.db.models import Q
from django.contrib.auth import authenticate, login

from django.forms.models import model_to_dict

from flowspec.forms import *
from flowspec.models import *
from peers.models import *

from django_registration.backends.activation.views import RegistrationView

from copy import deepcopy

from django.views.decorators.cache import never_cache
from django.conf import settings
from django.template.defaultfilters import slugify
from django.core.exceptions import PermissionDenied
from flowspec.helpers import send_new_mail, get_peer_techc_mails
import datetime
import os

LOG_FILENAME = os.path.join(settings.LOG_FILE_LOCATION, 'celery_jobs.log')
# FORMAT = '%(asctime)s %(levelname)s: %(message)s'
# logging.basicConfig(format=FORMAT)
#formatter = logging.Formatter('%(asctime)s %(levelname)s %(user)s: %(message)s')
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(LOG_FILENAME)
handler.setFormatter(formatter)
logger.addHandler(handler)


@login_required
def user_routes(request):
    user_routes = Route.objects.filter(applier=request.user)
    return render(
        request,
        'user_routes.html',
        {
            'routes': user_routes
        },
    )


def welcome(request):
    return render(
        request,
        'welcome.html',
    )


@login_required
@never_cache
def dashboard(request):
    all_group_routes = []
    message = ''
    #message = eee.aa
    try:
        peers = request.user.userprofile.peers.select_related()
    except UserProfile.DoesNotExist:
        error = "User <strong>%s</strong> does not belong to any peer or organization. It is not possible to create new firewall rules.<br>Please contact Helpdesk to resolve this issue" % request.user.username
        return render(
            request,
            'error.html',
            {
                'error': error
            }
        )
    if peers:
        if request.user.is_superuser:
            all_group_routes = Route.objects.all().order_by('-last_updated')[:10]
        else:
            query = Q()
            for peer in peers:
                query |= Q(applier__userprofile__in=peer.userprofile.all())
            all_group_routes = Route.objects.filter(query)
        if all_group_routes is None:
            message = 'You have not added any rules yet'
    else:
        message = 'You are not associated with a peer.'
        return render(
            request,
            'dashboard.html',
            {
                'message': message
            }
        )
    return render(
        request,
        'dashboard.html',
        {
            'routes': all_group_routes.prefetch_related(
                'applier',
                'applier',
                'fragmenttype',
                'protocol',
                'dscp',
            ),
            'message': message
        },
    )


@login_required
@never_cache
def group_routes(request):
    try:
        request.user.userprofile.peers.select_related()
    except UserProfile.DoesNotExist:
        error = "User <strong>%s</strong> does not belong to any peer or organization. It is not possible to create new firewall rules.<br>Please contact Helpdesk to resolve this issue" % request.user.username
        return render(
            request,
            'error.html',
            {
                'error': error
            }
        )
    return render(
        request,
        'user_routes.html',
        {}
    )


@login_required
@never_cache
def group_routes_ajax(request):
    all_group_routes = []
    try:
        peers = request.user.userprofile.peers.prefetch_related('networks')
    except UserProfile.DoesNotExist:
        error = "User <strong>%s</strong> does not belong to any peer or organization. It is not possible to create new firewall rules.<br>Please contact Helpdesk to resolve this issue" % request.user.username
        return render(
            request,
            'error.html',
            {'error': error}
        )
    if request.user.is_superuser:
        all_group_routes = Route.objects.all()
    else:
        query = Q()
        for peer in peers:
            query |= Q(applier__userprofile__in=peer.userprofile.all())
        all_group_routes = Route.objects.filter(query)
    jresp = {}
    routes = build_routes_json(all_group_routes, request.user.is_superuser)
    jresp['aaData'] = routes
    return HttpResponse(json.dumps(jresp), content_type='application/json')


@login_required
@never_cache
def overview_routes_ajax(request):
    all_group_routes = []
    try:
        # TODO all()?
        peers = request.user.userprofile.peers.all().select_related()
    except UserProfile.DoesNotExist:
        error = "User <strong>%s</strong> does not belong to any peer or organization. It is not possible to create new firewall rules.<br>Please contact Helpdesk to resolve this issue" % request.user.username
        return render(request, 'error.html', {'error': error})
    query = Q()
    for peer in peers:
        query |= Q(applier__userprofile__in=peer.userprofile.all())
    all_group_routes = Route.objects.filter(query)
    if request.user.is_superuser or request.user.has_perm('accounts.overview'):
        all_group_routes = Route.objects.all()
    jresp = {}
    routes = build_routes_json(all_group_routes, request.user.is_superuser)
    jresp['aaData'] = routes
    return HttpResponse(json.dumps(jresp), content_type='application/json')


def build_routes_json(groutes, is_superuser):
    routes = []
    for r in groutes.prefetch_related(
            'applier',
            'fragmenttype',
            'protocol',
            'dscp',
    ):
        rd = {}
        rd['id'] = r.pk
        rd['port'] = r.port
        rd['sourceport'] = r.sourceport
        rd['destinationport'] = r.destinationport
        # name with link to rule details
        rd['name'] = r.name
        rd['details'] = '<a href="%s">%s</a>' % (r.get_absolute_url(), r.name)
        if not r.comments:
            rd['comments'] = 'Not Any'
        else:
            rd['comments'] = r.comments
        rd['match'] = r.get_match()
        rd['then'] = r.get_then()
        rd['status'] = r.status
        # in case there is no applier (this should not occur)
        try:
            #rd['applier'] = r.applier.username
            userinfo = r.applier_username_nice
            #if is_superuser:
            #  applier_username = r.applier.username
            #  if applier_username != userinfo:
            #    userinfo += " ("+applier_username+")"
            rd['applier'] = userinfo
        except:
            rd['applier'] = 'unknown'
            rd['peer'] = ''
        else:
            peers = r.applier.userprofile.peers.select_related()
            username = None
            for peer in peers:
                if username:
                    break
                for network in peer.networks.all():
                    net = ip_network(network)
                    if ip_network(r.destination) in net:
                        username = peer.peer_name
                        break
            try:
                rd['peer'] = username
            except UserProfile.DoesNotExist:
                rd['peer'] = ''

        rd['expires'] = "%s" % r.expires
        rd['response'] = "%s" % r.response
        routes.append(rd)
    return routes


@login_required
@never_cache
def add_route(request):
    applier_peer_networks = []
    applier = request.user.pk
    if request.user.is_superuser:
        applier_peer_networks = PeerRange.objects.all()
    else:
        # TODO all()?
        user_peers = request.user.userprofile.peers.all()
        for peer in user_peers:
            applier_peer_networks.extend(peer.networks.all())
    if not applier_peer_networks:
        messages.add_message(
            request,
            messages.WARNING,
            ('Insufficient rights on administrative networks. Cannot add rule. Contact your administrator')
        )
        return HttpResponseRedirect(reverse("group-routes"))
    if request.method == "GET":
        form = RouteForm(initial={'applier': applier})
        if not request.user.is_superuser:
            form.fields['then'] = forms.ModelMultipleChoiceField(queryset=ThenAction.objects.filter(action__in=settings.UI_USER_THEN_ACTIONS).order_by('action'), required=True)
            form.fields['protocol'] = forms.ModelMultipleChoiceField(queryset=MatchProtocol.objects.filter(protocol__in=settings.UI_USER_PROTOCOLS).order_by('protocol'), required=False)
        return render(request, 'apply.html', {'form': form,
            'applier': applier,
            'maxexpires': settings.MAX_RULE_EXPIRE_DAYS })

    else:
        request_data = request.POST.copy()
        if request.user.is_superuser:
            request_data['issuperuser'] = request.user.username
        else:
            request_data['applier'] = applier
            try:
                del requset_data['issuperuser']
            except:
                pass
        form = RouteForm(request_data)
        if form.is_valid():
            route = form.save(commit=False)
            if not request.user.is_superuser:
                route.applier = request.user
            route.status = "PENDING"
            route.response = "Applying"
            route.source = ip_network('%s/%s' % (ip_network(route.source).network_address.compressed, ip_network(route.source).prefixlen)).compressed
            route.destination = ip_network('%s/%s' % (ip_network(route.destination).network_address.compressed, ip_network(route.destination).prefixlen)).compressed
            try:
                route.requesters_address = request.META['HTTP_X_FORWARDED_FOR']
            except:
                # in case the header is not provided
                route.requesters_address = 'unknown'
            route.save()
            form.save_m2m()
            # We have to make the commit after saving the form
            # in order to have all the m2m relations.
            route.commit_add()
            return HttpResponseRedirect(reverse("group-routes"))
        else:
            if not request.user.is_superuser:
                form.fields['then'] = forms.ModelMultipleChoiceField(queryset=ThenAction.objects.filter(action__in=settings.UI_USER_THEN_ACTIONS).order_by('action'), required=True)
                form.fields['protocol'] = forms.ModelMultipleChoiceField(queryset=MatchProtocol.objects.filter(protocol__in=settings.UI_USER_PROTOCOLS).order_by('protocol'), required=False)
            return render(
                request,
                'apply.html',
                {
                    'form': form,
                    'applier': applier,
                    'maxexpires': settings.MAX_RULE_EXPIRE_DAYS
                }
            )


@login_required
@never_cache
def edit_route(request, route_slug):
    applier = request.user.pk
    route_edit = get_object_or_404(Route, name=route_slug)

    applier_peer_networks = []
    if request.user.is_superuser:
        applier_peer_networks = PeerRange.objects.all()
    else:
        user_peers = request.user.userprofile.peers.all()
        for peer in user_peers:
            applier_peer_networks.extend(peer.networks.all())
    if not applier_peer_networks:
        messages.add_message(
            request,
            messages.WARNING,
            ('Insufficient rights on administrative networks. Cannot add rule. Contact your administrator')
        )
        return HttpResponseRedirect(reverse("group-routes"))
    if route_edit.status == 'PENDING':
        messages.add_message(
            request,
            messages.WARNING,
            ('Cannot edit a pending rule: %s.') % (route_slug)
        )
        return HttpResponseRedirect(reverse("group-routes"))
    route_original = deepcopy(route_edit)
    if request.POST:
        request_data = request.POST.copy()
        if request.user.is_superuser:
            request_data['issuperuser'] = request.user.username
        else:
            request_data['applier'] = applier
            try:
                del request_data['issuperuser']
            except:
                pass
        form = RouteForm(
            request_data,
            instance=route_edit
        )
        critical_changed_values = ['source', 'destination', 'sourceport', 'destinationport', 'port', 'protocol', 'then', 'fragmenttype']
        if form.is_valid():
            changed_data = form.changed_data
            route = form.save(commit=False)
            route.name = route_original.name
            route.status = route_original.status
            route.response = route_original.response
            if not request.user.is_superuser:
                route.applier = request.user
            if bool(set(changed_data) & set(critical_changed_values)) or (not route_original.status == 'ACTIVE'):
                route.status = "PENDING"
                route.response = "Applying"
                route.source = ip_network('%s/%s' % (ip_network(route.source).network_address.compressed, ip_network(route.source).prefixlen)).compressed
                route.destination = ip_network('%s/%s' % (ip_network(route.destination).network_address.compressed, ip_network(route.destination).prefixlen)).compressed
                try:
                    route.requesters_address = request.META['HTTP_X_FORWARDED_FOR']
                except:
                    # in case the header is not provided
                    route.requesters_address = 'unknown'

            route.save()
            if bool(set(changed_data) & set(critical_changed_values)) or (not route_original.status == 'ACTIVE'):
                form.save_m2m()
                route.commit_edit()
            return HttpResponseRedirect(reverse("group-routes"))
        else:
            if not request.user.is_superuser:
                form.fields['then'] = forms.ModelMultipleChoiceField(queryset=ThenAction.objects.filter(action__in=settings.UI_USER_THEN_ACTIONS).order_by('action'), required=True)
                form.fields['protocol'] = forms.ModelMultipleChoiceField(queryset=MatchProtocol.objects.filter(protocol__in=settings.UI_USER_PROTOCOLS).order_by('protocol'), required=False)
            return render(request, 'apply.html',
                {
                    'form': form,
                    'edit': True,
                    'applier': applier,
                    'maxexpires': settings.MAX_RULE_EXPIRE_DAYS
                })
    else:
        if (not route_original.status == 'ACTIVE'):
            route_edit.expires = datetime.date.today() + datetime.timedelta(days=settings.EXPIRATION_DAYS_OFFSET-1)
        dictionary = model_to_dict(route_edit, fields=[], exclude=[])
        if request.user.is_superuser:
            dictionary['issuperuser'] = request.user.username
        else:
            try:
                del dictionary['issuperuser']
            except:
                pass
        form = RouteForm(dictionary)
        if not request.user.is_superuser:
            form.fields['then'] = forms.ModelMultipleChoiceField(queryset=ThenAction.objects.filter(action__in=settings.UI_USER_THEN_ACTIONS).order_by('action'), required=True)
            form.fields['protocol'] = forms.ModelMultipleChoiceField(queryset=MatchProtocol.objects.filter(protocol__in=settings.UI_USER_PROTOCOLS).order_by('protocol'), required=False)
        return render(request, 'apply.html',
            {
                'form': form,
                'edit': True,
                'applier': applier,
                'maxexpires': settings.MAX_RULE_EXPIRE_DAYS
            })


@login_required
@never_cache
def delete_route(request, route_slug):
    if request.is_ajax():
        route = get_object_or_404(Route, name=route_slug)
        peers = route.applier.userprofile.peers.all()
        username = None
        for peer in peers:
            if username:
                break
            for network in peer.networks.all():
                net = ip_network(network)
                if ip_network(route.destination) in net:
                    username = peer
                    break
        applier_peer = username
        peers = request.user.userprofile.peers.all()
        username = None
        for peer in peers:
            if username:
                break
            for network in peer.networks.all():
                net = ip_network(network)
                if ip_network(route.destination) in net:
                    username = peer
                    break
        requester_peer = username
        if applier_peer == requester_peer or request.user.is_superuser:
            route.status = "PENDING"
            route.expires = datetime.date.today()
            if not request.user.is_superuser:
                route.applier = request.user
            route.response = "Deactivating"
            try:
                route.requesters_address = request.META['HTTP_X_FORWARDED_FOR']
            except:
                # in case the header is not provided
                route.requesters_address = 'unknown'
            route.save()
            route.commit_delete()
        html = "<html><body>Done</body></html>"
        return HttpResponse(html)
    else:
        return HttpResponseRedirect(reverse("group-routes"))


@login_required
@never_cache
def user_profile(request):
    user = request.user
    try:
        peers = request.user.userprofile.peers.all()
        if user.is_superuser:
            peers = Peer.objects.all()
    except UserProfile.DoesNotExist:
        error = "User <strong>%s</strong> does not belong to any peer or organization. It is not possible to create new firewall rules.<br>Please contact Helpdesk to resolve this issue" % user.username
        return render(
            request,
            'error.html',
            {'error': error}
        )
    return render(
        request,
        'profile.html',
        {
            'user': user,
            'peers': peers
        },
    )

def get_shibboleth_attrib_info_from_settings(attrib_key, add_long_info):
  try:
    attrib_name = getattr(settings, attrib_key).get[0]
  except:
    attrib_key = attrib_key
  try:
    attrib_display_name = getattr(settings, attrib_key+"_DISPLAY_NAME")
  except:
    attrib_display_name = None
  try:
    attrib_display_addinfo = getattr(settings, attrib_key+"_DISPLAY_ADDINFO")
  except:
      attrib_display_addinfo = None

  attrib_info = ""
  if attrib_display_name != None and attrib_display_name!="":
    attrib_info = attrib_display_name
  else:
    attrib_info = attrib_key # remove ^HTTP_ and then ^SHIB_
    if attrib_info.startswith("HTTP_"):
      attrib_info[len("HTTP_"):]
    if attrib_info.startswith("SHIB_"):
      attrib_info[len("SHIB_"):]

  if add_long_info and attrib_display_addinfo != None and attrib_display_addinfo!="":
    attrib_info = attrib_info+" ("+attrib_display_addinfo+")"

  return attrib_info

@never_cache
def user_login(request):
    try:
        error_username = False
        error_orgname = False
        error_entitlement = False
        error_mail = False
        has_entitlement = False
        error = ''
        username = lookupShibAttr(settings.SHIB_USERNAME, request.META)
        if not username:
            error_username = True
        firstname = lookupShibAttr(settings.SHIB_FIRSTNAME, request.META)
        lastname = lookupShibAttr(settings.SHIB_LASTNAME, request.META)
        mail = lookupShibAttr(settings.SHIB_MAIL, request.META)
        entitlement = lookupShibAttr(settings.SHIB_ENTITLEMENT, request.META)

        username__attrib_info1 = get_shibboleth_attrib_info_from_settings("SHIB_USERNAME", False)
        entitlement__attrib_info1 = get_shibboleth_attrib_info_from_settings("SHIB_ENTITLEMENT", False)
        mail__attrib_info1 = get_shibboleth_attrib_info_from_settings("SHIB_MAIL", False)
        username__attrib_info = get_shibboleth_attrib_info_from_settings("SHIB_USERNAME", True)
        entitlement__attrib_info = get_shibboleth_attrib_info_from_settings("SHIB_ENTITLEMENT", True)
        mail__attrib_info = get_shibboleth_attrib_info_from_settings("SHIB_MAIL", True)
        givenname__attrib_info = get_shibboleth_attrib_info_from_settings("SHIB_FIRSTNAME", True)
        surname__attrib_info = get_shibboleth_attrib_info_from_settings("SHIB_LASTNAME", True)

        if settings.SHIB_AUTH_ENTITLEMENT != "":
          required_attributes_attribute_info__list = [ username__attrib_info, mail__attrib_info, entitlement__attrib_info ]
        else:
          required_attributes_attribute_info__list = [ username__attrib_info, mail__attrib_info ]

        optional_attributes_attribute_info__list = [ givenname__attrib_info, surname__attrib_info ]

        if settings.SHIB_AUTH_ENTITLEMENT in entitlement.split(";"):
            has_entitlement = True
        if not has_entitlement:
            error_entitlement = True
        if not mail:
            error_mail = True
        if error_username:
            #error = _("Your idP should release the HTTP_EPPN attribute towards this service<br>")
            error = _("Your idP should release the "+username__attrib_info1+" attribute towards this service<br>")
        if error_entitlement:
            #error = error + _("Your idP should release an appropriate HTTP_SHIB_EP_ENTITLEMENT attribute towards this service<br>")
            error = error + _("Your idP should release an appropriate "+entitlement__attrib_info1+" attribute towards this service<br>")
        if error_mail:
            #error = error + _("Your idP should release the HTTP_SHIB_INETORGPERSON_MAIL attribute towards this service")
            error = error + _("Your idP should release the "+mail__attrib_info1+" attribute towards this service")
        if error_username or error_orgname or error_entitlement or error_mail:
            return render(
                request,
                'error.html',
                {
                    'error': error,
                    "missing_attributes": True,
                    "required_attributes_attribute_info__list" : required_attributes_attribute_info__list,
                    "optional_attributes_attribute_info__list" : optional_attributes_attribute_info__list
                },
            )
        try:
            if settings.SHIB_SLUGIFY_USERNAME:
                username = slugify(username)
            user = User.objects.get(username__exact=username)
            user.email = mail
            user.first_name = firstname
            user.last_name = lastname
            user.save()
            user_exists = True
        except:
            user_exists = False
        user = authenticate(username=username, firstname=firstname, lastname=lastname, mail=mail, authsource='shibboleth')
        logger.debug('Authentication of %s' % user)

        if user is not None:
            try:
                user.userprofile.peers.all()
            except:
                form = UserProfileForm()
                form.fields['user'] = forms.ModelChoiceField(queryset=User.objects.filter(pk=user.pk), empty_label=None)
                form.fields['peer'] = forms.ModelChoiceField(queryset=Peer.objects.all(), empty_label=None)
                return render(request, 'django_registration/select_institution.html', {'form': form})
            if not user_exists:
                user_activation_notify(request, user)
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect(reverse("dashboard"))
            else:
                error = _("User account <strong>%s</strong> is pending activation. Administrators have been notified and will activate this account within the next days. <br>If this account has remained inactive for a long time contact your technical coordinator or GEANT Helpdesk") %user.username
                return render(
                    request,
                    'error.html',
                    {
                        'error': error,
                        'inactive': True
                    },
                )
        else:
            error = _("Something went wrong during user authentication. Contact your administrator")
            return render(
                request,
                'error.html',
                {'error': error},
            )
    except User.DoesNotExist as e:
        error = _("Invalid login procedure. Error: %s" % e)
        return render(
            request,
            'error.html',
            {
                'error': error
            },
        )


def user_activation_notify(request, user):
    if not settings.DISABLE_EMAIL_NOTIFICATION:
        current_site = Site.objects.get_current()
        peers = user.userprofile.peers.all()
        reg_view = RegistrationView()
        reg_view.request = request
        reg_view.email_body_template = 'django_registration/activation_email.txt'
        reg_view.email_subject_template = 'django_registration/activation_email_subject.txt'

        # Email subject *must not* contain newlines
        # TechCs will be notified about new users.
        # Platform admins will activate the users.

        subject = render_to_string(
            'django_registration/activation_email_subject.txt',
            {
                'site': current_site
            }
        )
        subject = ''.join(subject.splitlines())
        
        if settings.NOTIFY_ADMIN_MAILS:
            admin_mails = settings.NOTIFY_ADMIN_MAILS
            message = render_to_string(
                template_name = reg_view.email_body_template,
                context=reg_view.get_email_context(reg_view.get_activation_key(user)),
                request=request
            )

            send_new_mail(
                settings.EMAIL_SUBJECT_PREFIX + subject,
                message,
                settings.SERVER_EMAIL,
                admin_mails,
                []
            )
        for peer in peers:
            try:
                PeerNotify.objects.get(peer=peer, user=user)
            except:
                peer_notification = PeerNotify(peer=peer, user=user)
                peer_notification.save()
                # Mail to domain techCs plus platform admins (no activation hash sent)
                subject = render_to_string(
                    'django_registration/activation_email_peer_notify_subject.txt',
                    {
                        'site': current_site,
                        'peer': peer
                    }
                )
                subject = ''.join(subject.splitlines())
                message = render_to_string(
                    'django_registration/activation_email_peer_notify.txt',
                    {
                        'user': user,
                        'peer': peer
                    }
                )
                send_new_mail(
                    settings.EMAIL_SUBJECT_PREFIX + subject,
                    message,
                    settings.SERVER_EMAIL,
                    get_peer_techc_mails(user, peer), [])


@login_required
@never_cache
def add_rate_limit(request):
    if request.method == "GET":
        form = ThenPlainForm()
        return render(
            request,
            'add_rate_limit.html',
            {
                'form': form,
            },
        )
    else:
        form = ThenPlainForm(request.POST)
        if form.is_valid():
            then = form.save(commit=False)
            then.action_value = "%sk" % then.action_value
            then.save()
            response_data = {}
            response_data['pk'] = "%s" % then.pk
            response_data['value'] = "%s:%s" % (then.action, then.action_value)
            return HttpResponse(
                json.dumps(response_data),
                content_type='application/json'
            )
        else:
            return render(
                request,
                'add_rate_limit.html',
                {
                    'form': form,
                },
            )


@login_required
@never_cache
def add_port(request):
    if request.method == "GET":
        form = PortRangeForm()
        return render(
            request,
            'add_port.html',
            {
                'form': form,
            },
        )
    else:
        form = PortRangeForm(request.POST)
        if form.is_valid():
            port = form.save()
            response_data = {}
            response_data['value'] = "%s" % port.pk
            response_data['text'] = "%s" % port.port
            return HttpResponse(
                json.dumps(response_data),
                content_type='application/json'
            )
        else:
            return render(
                request,
                'add_port.html',
                {
                    'form': form,
                },
            )


@never_cache
def selectinst(request):
    if request.method == 'POST':
        request_data = request.POST.copy()
        user = request_data['user']
        try:
            UserProfile.objects.get(user=user)
            error = _("Violation warning: User account is already associated with an institution.The event has been logged and our administrators will be notified about it")
            return render(
                request,
                'error.html',
                {
                    'error': error,
                    'inactive': True
                },
            )
        except UserProfile.DoesNotExist:
            pass

        form = UserProfileForm(request_data)
        if form.is_valid():
            userprofile = form.save()
            user_activation_notify(request, userprofile.user)
            error = _("User account <strong>%s</strong> is pending activation. Administrators have been notified and will activate this account within the next days. <br>If this account has remained inactive for a long time contact your technical coordinator or GEANT Helpdesk") %userprofile.user.username
            return render(
                request,
                'error.html',
                {
                    'error': error,
                    'inactive': True
                },
            )
        else:
            return render(
                request,
                'django_registration/select_institution.html',
                {
                    'form': form
                }
            )


@never_cache
def overview(request):
    user = request.user
    if user.is_authenticated:
        if user.has_perm('accounts.overview'):
            users = User.objects.all()
            return render(
                request,
                'overview/index.html',
                {
                    'users': users
                },
            )
        else:
            violation = True
            return render(
                request,
                'overview/index.html',
                {
                    'violation': violation
                },
            )
    else:
        return HttpResponseRedirect(reverse("altlogin"))


@login_required
@never_cache
def user_logout(request):
    logout(request)
    return HttpResponseRedirect(settings.SHIB_LOGOUT_URL or reverse('group-routes'))


@never_cache
def load_jscript(request, file):
    long_polling_timeout = int(settings.POLL_SESSION_UPDATE) * 1000 + 10000
    return render(request, '%s.js' % file, {'timeout': long_polling_timeout}, content_type="text/javascript")


def lookupShibAttr(attrmap, requestMeta):
    logger.debug("lookupShibAttr: requestMeta=%s" % str(requestMeta))
    for attr in attrmap:
        if (attr in requestMeta.keys()):
            if len(requestMeta[attr]) > 0:
                return requestMeta[attr]
    return ''


# show the details of specific route
@login_required
@never_cache
def routedetails(request, route_slug):
    route = get_object_or_404(Route, name=route_slug)
    #return render(request, 'flowspy/route_details.html', {'route': route})
    now = datetime.datetime.now()
    return render(request, 'flowspy/route_details.html', {
      'route': route, 
      'mytime': now, 
      'tz' : settings.TIME_ZONE,
      'is_superuser' : request.user.is_superuser,
      'route_comments_len' : len(str(route.comments))
      })

@login_required
def routestats(request, route_slug):
    route = get_object_or_404(Route, name=route_slug)
    import junos
    import time
    res = {}
    try:
        with open(settings.SNMP_TEMP_FILE, "r") as f:
            res = json.load(f)
        f.close()
        routename = create_junos_name(route)
        route_id = str(route.id)
        if not res:
            raise Exception("No data stored in the existing file.")
        if settings.STATISTICS_PER_RULE==False:
            if routename in res:
              return HttpResponse(json.dumps({"name": routename, "data": res[routename]}), content_type="application/json")
            else:
              return HttpResponse(json.dumps({"error": "Route '{}' was not found in statistics.".format(routename)}), content_type="application/json", status=404)
        else:
            if route_id in res['_per_rule']:
              return HttpResponse(json.dumps({"name": routename, "data": res['_per_rule'][route_id]}), content_type="application/json")
            else:
              return HttpResponse(json.dumps({"error": "Route '{}' was not found in statistics.".format(route_id)}), content_type="application/json", status=404)

    except Exception as e:
        logger.error('routestats failed: %s' % e)
        return HttpResponse(json.dumps({"error": "No data available. %s" % e}), content_type="application/json", status=404)

def setup(request):
    if User.objects.count() == 0:
        if request.method == "POST":
            form = SetupForm(request.POST)
            if form.is_valid():
                u = User.objects.create_user(username="admin", email="email@example.com", password=form.cleaned_data["password"])
                u.is_superuser = True
                u.is_staff = True
                u.save()
                pr = PeerRange(network = form.cleaned_data["test_peer_addr"])
                pr.save()
                p = Peer(peer_name = "testpeer", peer_tag = "testpeer")
                p.save()
                p.networks.add(pr)
                ua = UserProfile()
                ua.user = u
                ua.save()
                ua.peers.add(p)

                with open("flowspy/settings_local.py", "a") as f:
                    f.write("NETCONF_DEVICE = \"%s\"\n" % form.cleaned_data["netconf_device"])
                    f.write("NETCONF_USER = \"%s\"\n"   % form.cleaned_data["netconf_user"])
                    f.write("NETCONF_PASS = \"%s\"\n"   % form.cleaned_data["netconf_pass"])
                    f.write("NETCONF_PORT = %s\n"       % form.cleaned_data["netconf_port"])

                # logger.error('TODO REMOVE: password: %s' % form.cleaned_data["password"])
                return HttpResponseRedirect(reverse("welcome"))
        else:
            form = SetupForm()
            return render(request, 'flowspy/setup.html', {'form': form})
    else:
        raise PermissionDenied

