from django.shortcuts import get_object_or_404
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from rest_framework import viewsets
from flowspec.models import Route, ThenAction, FragmentType, MatchProtocol, MatchDscp
from flowspec.models import convert_container_to_queryset

from flowspec.tasks import announce

from flowspec.serializers import (
    RouteSerializer,
    ThenActionSerializer,
    FragmentTypeSerializer,
    MatchProtocolSerializer,
    MatchDscpSerializer)

from flowspec.validators import check_if_rule_exists
from rest_framework.response import Response

from flowspec.tasks import *

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "flowspec_viewsets.log", False)

class RouteViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Route.objects.all()
    serializer_class = RouteSerializer

    def get_queryset(self):
        scope=""
        try:
          logger.info("RouteViewSet::get_queryset(): param scope="+str(self.request.query_params['scope']))
          scope=self.request.query_params['scope'] 
        except:
          pass

        user=self.request.user
        try:
          if self.request.user.is_superuser and 'username' in self.request.query_params:
            username=self.request.query_params['username'] 
            logger.info("RouteViewSet::get_queryset(): username="+str(username))
            user=User.objects.get(username=username)
            logger.info("RouteViewSet::get_queryset(): param username="+str(self.request.query_params['username']))
        except Exception as e: 
          logger.info("RouteViewSet::get_queryset(): got exception e="+str(e))
          return convert_container_to_queryset([], Route)
        #logger.info("RouteViewSet::get_queryset(): user="+str(user))

        if scope == "applier":
            return convert_container_to_queryset(self.get_users_routes_by_applier_only(user), Route)
        elif scope == "peer":
            return convert_container_to_queryset(self.get_users_routes_by_its_peers(user), Route)
        elif scope == "user":
            return convert_container_to_queryset(self.get_users_routes_all(user), Route)

        if self.request.user.is_superuser:
            return Route.objects.all() # default for admin is all
        else:
            return convert_container_to_queryset(self.get_users_routes_all(user), Route) #default for non-admin is "user"

    def get_users_routes_all(self, user):
        return global__get_users_routes_all(user)

    def get_users_routes_by_its_peers(self, user):
        return global__get_users_routes_by_its_peers(user)

    def get_users_routes_by_applier_only(self, user):
        return global__get_users_routes_by_applier_only(user)


    def list(self, request):
        serializer = RouteSerializer(
            self.get_queryset(), many=True, context={'request': request})
        return Response(serializer.data)

    def create(self, request):
        logger.debug("RouteViewSet::create(): request.data="+str(request.data))
        serializer = RouteSerializer(
            context={'request': request}, data=request.data, partial=True) # is this correct ???
        try:
            #raise test from None 
            if serializer.is_valid():
                (exists, message) = check_if_rule_exists(
                    {
                     #'source': serializer.object.source,
                     'source': request.data["source"],
                     #'destination': serializer.object.destination,
                     'destination': request.data["destination"]},
                    self.get_queryset())
                if exists:
                    return Response({"non_field_errors": [message]}, status=400)
                else:
                    #return super(RouteViewSet, self).create(request)
                    obj = super(RouteViewSet, self).create(request)
                    requested_status = request.data.get("status", "INACTIVE")
                    logger.debug("RouteViewSet::create(): requested_status="+str(requested_status))
                    #logger.info("RouteViewSet::create(): obj.type="+str(type(obj)))
                    #logger.info("RouteViewSet::create(): obj="+str(obj))
                    #logger.info("RouteViewSet::create(): obj.dir="+str(dir(obj)))
                    #logger.info("RouteViewSet::create(): obj.items="+str(obj.items))
                    logger.info("RouteViewSet::create(): obj.data="+str(obj.data))
                    #logger.info("RouteViewSet::create(): obj.data.id="+str(obj.data["id"]))
                    route = get_object_or_404(self.get_queryset(), pk=obj.data["id"])
                    route.response = "N/A"

                    #logger.info("RouteViewSet::create(): obj.data="+str(obj.data))
                    #logger.info("RouteViewSet::create(): route.expires="+str(route.expires))
                    if (not ('expires' in obj.data)) or obj.data['expires']=='':
                      route.set_no_expire() # REST API created routes without expires value should have no expiration date by default
                    obj.data['expires'] = route.expires

                    net_route_source=ip_network(route.source, strict=False)
                    net_route_destination=ip_network(route.destination, strict=False)
                    if net_route_source.version != net_route_destination.version:
                      return Response({"address family (IP version) of source prefix and destination prefix have to be equal"}, status=400)

                    if requested_status == "ACTIVE":
                        route.status = "PENDING"
                        route.save()
                        route.commit_add()
                    elif requested_status == "INACTIVE":
                        route.status = "INACTIVE"
                        route.save()
                        announce("[%s] new inactive Rule added: %s" % (route.applier_username_nice, route.name_visible), route.applier, route)
                    else:
                        route.save()
                        announce("[%s] new non-active Rule added: %s" % (route.applier_username_nice, route.name_visible), route.applier, route)

                    obj.data["status"] = route.status
                    logger.info("RouteViewSet::create(): => route="+str(route))
                    logger.info("RouteViewSet::create(): => route.status="+str(route.status))
                    logger.info("RouteViewSet::create(): => obj="+str(obj))

                    return obj
            else:
                return Response(serializer.errors, status=400)
        except BaseException as e:
            logger.error("RouteViewSet::create(): got exception", exc_info=True)

    def retrieve(self, request, pk=None):
        route = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = RouteSerializer(route, context={'request': request})
        return Response(serializer.data)

    def update(self, request, pk=None, partial=False):
        """
        Overriden to customize `status` update behaviour.
        Changes in `status` need to be handled here, since we have to know the
        previous `status` of the object to choose the correct action.
        """

        def set_object_pending(obj):
            """
            Sets an object's status to "PENDING". This reflects that
            the object has not already been commited to the flowspec device,
            and the asynchronous job that will handle the sync will
            update the status accordingly

            :param obj: the object whose status will be changed
            :type obj: `flowspec.models.Route`
            """
            obj.status = "PENDING"
            obj.response = "N/A"
            obj.save()

        def work_on_active_object(obj, new_status, partial, route_params_changed):
            """
            Decides which `commit` action to choose depending on the
            requested status

            Cases:
            * `ACTIVE` ~> `INACTIVE`: The `Route` must be deleted from the
                flowspec device (`commit_deactivate`)
            * (not partial or route_params_changed) and `ACTIVE` ~> `ACTIVE`: The `Route` is present and to be changed actually, so it must be
                edited (`commit_edit`)
            * partial (PATCH method) and !route_params_changed and `ACTIVE` ~> `ACTIVE`: only update database object 

            :param new_status: the newly requested status
            :type new_status: str
            :param obj: the `Route` object
            :type obj: `flowspec.models.Route`
            """

            if new_status == 'INACTIVE':
                set_object_pending(obj)
                deactivate_route.delay(obj.pk)
            elif not partial or route_params_changed: # in case of an PATCH without status change and !route_params_changed dont re-commit object
                set_object_pending(obj)
                obj.commit_edit()
            else:
                obj.save()
                announce("[%s] Rule non-flowspec-params updated: %s" % (obj.applier_username_nice, obj.name_visible), obj.applier, obj)

        def work_on_inactive_object(obj, new_status, partial):
            """
            Decides which `commit` action to choose depending on the
            requested status

            Cases:
            * `INACTIVE` ~> `ACTIVE`: The `Route` is not present on the device

            :param new_status: the newly requested status
            :type new_status: str
            :param obj: the `Route` object
            :type obj: `flowspec.models.Route`
            """
            if new_status == 'ACTIVE':
                set_object_pending(obj)
                obj.commit_add()
            else:
                obj.save()
                announce("[%s] Rule non-flowspec-params updated: %s" % (obj.applier_username_nice, obj.name_visible), obj.applier, obj)
        
        #if not partial:
        #   raise PermissionDenied('Permission Denied')

        obj = get_object_or_404(self.queryset, pk=pk)
        old_status = obj.status

        serializer = RouteSerializer(obj, context={'request': request}, data=request.data, partial=partial)
        logger.info("RouteViewSet::update(): partial="+str(partial)+" request.data="+str(request.data))

        if serializer.is_valid():
            #new_status = serializer.object.status
            new_status = serializer.data["status"]

            try:
              requested_status = request.data["status"]
            except KeyError:
              if partial:
                requested_status = old_status
              else:
                return Response("no status specified", status=400)

            net_route_source=ip_network(obj.source, strict=False)
            net_route_destination=ip_network(obj.destination, strict=False)
            net_route_source__edit=ip_network(request.data["source"], strict=False)
            net_route_destination__edit=ip_network(request.data["destination"], strict=False)
            logger.info("RouteViewSet::update(): net_route_source="+str(net_route_source)+" net_route_source__edit="+str(net_route_source__edit))
            if net_route_source__edit.version != net_route_source.version:
              return Response({"address family (IP version) of source prefix of an existing rule cannot be changed"}, status=400)
            if net_route_destination__edit.version != net_route_destination.version:
              return Response({"address family (IP version) of destination prefix of an existing rule cannot be changed"}, status=400)

            #if requested_status == 'INACTIVE':
            new_status = requested_status
            #logger.info("RouteViewSet::update(): data="+str(request.data))
            logger.info("RouteViewSet::update(): pk="+str(pk))
            logger.info("RouteViewSet::update(): request="+str(requested_status))
            logger.info("RouteViewSet::update(): obj.type="+str(type(obj)))
            logger.info("RouteViewSet::update(): obj="+str(obj))
            logger.info("RouteViewSet::update(): old_status="+str(old_status)+", new_status="+str(new_status))
        
            route_params_changed = self.helper_check_route_params_change(partial, obj, serializer, request.data)

            super(RouteViewSet, self).update(request, pk, partial=partial)
            obj = get_object_or_404(self.queryset, pk=pk)

            if old_status == 'ACTIVE':
                work_on_active_object(obj, new_status, partial, route_params_changed)
            elif old_status in ['INACTIVE', 'ERROR']:
                work_on_inactive_object(obj, new_status, partial)
            logger.info("RouteViewSet::update(): returning (obj="+str(obj)+" obj.status="+str(obj.status)+")")
            return Response(RouteSerializer(obj, context={'request': request}).data, status=200)
        else:
            return Response(serializer.errors, status=400)

    def helper_check_route_params_change(self, is_partial, obj, serializer, request_data):

            #old_source = obj.source
            old_source = serializer.data["source"]
            try:
              new_source = request_data["source"]
            except KeyError:
              if is_partial:
                new_source = old_source
              else:
                new_source = None

            #old_destination = obj.destination
            old_destination = serializer.data["destination"]
            try:
              new_destination = request_data["destination"]
            except KeyError:
              if is_partial:
                new_destination = old_destination
              else:
                new_destination = None

            #old_sourceport = obj.sourceport
            old_sourceport = serializer.data["sourceport"]
            try:
              new_sourceport = request_data["sourceport"]
            except KeyError:
              if is_partial:
                new_sourceport = old_sourceport
              else:
                new_sourceport = None

            #old_destinationport = obj.destinationport
            old_destinationport = serializer.data["destinationport"]
            try:
              new_destinationport = request_data["destinationport"]
            except KeyError:
              if is_partial:
                new_destinationport = old_destinationport
              else:
                new_destinationport = None

            #old_port = obj.port
            old_port = serializer.data["port"]
            try:
              new_port = request_data["port"]
            except KeyError:
              if is_partial:
                new_port = old_port
              else:
                new_port = None

            #old_protocol = [str(el) for el in obj.protocol.all()]
            old_protocol = [str(el) for el in serializer.data["protocol"]]
            old_protocol.sort()
            try:
              new_protocol = [str(el) for el in request_data["protocol"]]
              new_protocol.sort()
            except KeyError:
              if is_partial:
                new_protocol = old_protocol
              else:
                new_protocol = []

            #old_fragmentype = [str(el) for  el in obj.fragmenttype.all()]
            old_fragmentype = [str(el) for el in serializer.data["fragmenttype"]]
            old_fragmentype.sort()
            try:
              new_fragmentype = [str(el) for el in request_data["fragmenttype"]]
              new_fragmentype.sort()
            except KeyError:
              if is_partial:
                  new_fragmentype = old_fragmentype
              else:
                  new_fragmentype = []

            old_icmptype = obj.icmptype
            #old_icmptype = serializer.data["icmptype"]
            try:
              new_icmptype = request_data["icmptype"]
            except KeyError:
              if is_partial:
                new_icmptype = old_icmptype
              else:
                new_icmptype = None

            old_icmpcode = obj.icmpcode
            #old_icmpcode = serializer.data["icmpcode"]
            try:
              new_icmpcode = request_data["icmpcode"]
            except KeyError:
              if is_partial:
                new_icmpcode = old_icmpcode
              else:
                new_icmpcode = None

            old_tcpflag = obj.tcpflag
            #old_tcpflag = serializer.data["tcpflag"]
            try:
              new_tcpflag = request_data["tcpflag"]
            except KeyError:
              if is_partial:
                new_tcpflag = old_tcpflag
              else:
                new_tcpflag = None

            old_dscp = obj.dscp
            #old_dscp = serializer.data["dscp"]
            try:
              new_dscp = request_data["dscp"]
            except KeyError:
              if is_partial:
                new_dscp = old_dscp
              else:
                new_dscp = None

            old_packetlength = obj.packetlength
            #old_packetlength = serializer.data["packetlength"]
            try:
              new_packetlength = request_data["packetlength"]
            except KeyError:
              if is_partial:
                new_packetlength = old_packetlength
              else:
                new_packetlength = None

            #old_then = [str(el) for el in obj.then.all()]
            old_then = [str(el) for el in serializer.data["then"]]
            old_then.sort()
            try:
              new_then = [str(el) for el in request_data["then"]]
              new_then.sort()
            except KeyError:
              if is_partial:
                new_then = old_then
              else:
                new_then = None
            
            #logger.info("RouteViewSet::helper_check_route_params_change(): old_source="+str(old_source)+", new_source="+str(new_source))
            #logger.info("RouteViewSet::helper_check_route_params_change(): old_sourceport="+str(old_sourceport)+", new_sourceport="+str(new_sourceport))
            #logger.info("RouteViewSet::helper_check_route_params_change(): old_destination="+str(old_destination)+", new_destination="+str(new_destination))
            #logger.info("RouteViewSet::helper_check_route_params_change(): old_destinationport="+str(old_destinationport)+", new_destinationport="+str(new_destinationport))
            #logger.info("RouteViewSet::helper_check_route_params_change(): old_protocol="+str(old_protocol)+", new_protocol="+str(new_protocol))
            #logger.info("RouteViewSet::helper_check_route_params_change(): old_fragmentype="+str(old_fragmentype)+", new_fragmentype="+str(new_fragmentype))
            #logger.info("RouteViewSet::helper_check_route_params_change(): old_then="+str(old_then)+", new_then="+str(new_then))
            ##logger.info("RouteViewSet::helper_check_route_params_change(): old="+str(obj))
            #logger.info("RouteViewSet::helper_check_route_params_change(): old_icmptype="+str(old_icmptype)+", new_icmptype="+str(new_icmptype))
            #logger.info("RouteViewSet::helper_check_route_params_change(): old_icmpcode="+str(old_icmpcode)+", new_icmpcode="+str(new_icmpcode))
            #logger.info("RouteViewSet::helper_check_route_params_change(): old_tcpflag="+str(old_tcpflag)+", new_tcpflag="+str(new_tcpflag))
            #logger.info("RouteViewSet::helper_check_route_params_change(): old_dscp="+str(old_dscp)+", new_dscp="+str(new_dscp))
            #logger.info("RouteViewSet::helper_check_route_params_change(): old_packetlength="+str(old_packetlength)+", new_packetlength="+str(new_packetlength))

            route_params_changed = old_source!=new_source or old_destination != new_destination or old_sourceport!=new_sourceport or old_destinationport!=new_destinationport or old_protocol!=new_protocol or old_fragmentype!=new_fragmentype or old_then!=new_then
            logger.info("RouteViewSet::helper_check_route_params_change(): => route_params_changed="+str(route_params_changed))

            return route_params_changed

    def destroy(self, request, pk=None, partial=False):
        """ HTTTP DELETE Method """
        obj = get_object_or_404(self.queryset, pk=pk)
        logger.info("RouteViewSet::delete(): pk="+str(pk)+" obj="+str(obj))

        username_request = request.user.username
        user_is_admin = request.user.is_superuser
        full_delete_is_allowed = request.user.userprofile.is_delete_allowed()
        logger.info("RouteViewSet::delete(): username_request="+str(username_request)+" user_is_admin="+str(user_is_admin)+" => full_delete_is_allowed="+str(full_delete_is_allowed))

        try:
          restapidel_fornonallowedusers_decativates = settings.RESTAPI_DEL_METHOD__FOR_NONALLOWED_USERS__DEACTIVATES
        except:
          restapidel_fornonallowedusers_decativates = False
        logger.info("RouteViewSet::delete(): restapidel_fornonallowedusers_decativates="+str(restapidel_fornonallowedusers_decativates))

        if (not full_delete_is_allowed) and (not restapidel_fornonallowedusers_decativates):
          return Response({"status": "deletion forbidden; for deactivation use PATCH instead."}, 403)

        add_info1=""
        if obj.status!="INACTIVE" :
            obj.status = "PENDING"
            obj.save()
            add_info1="non-inactive "
        else:
            add_info1="inactive "

        #if True or not self.request.user.is_superuser():
        if full_delete_is_allowed:
            job = delete_route.delay(obj.pk)
            return Response({"status": "Received task to delete "+add_info1+"route.", "job_id": str(job)}, 202)
        else:
            if obj.status == "INACTIVE":
                return Response({"status": "Cannot deactivate route that is inactive already."}, 406)
            job = deactivate_route.delay(obj.pk)
            return Response({"status": "Received task to deactivate route.", "job_id": str(job)}, 202)

class ThenActionViewSet(viewsets.ModelViewSet):
    queryset = ThenAction.objects.all()
    serializer_class = ThenActionSerializer


class FragmentTypeViewSet(viewsets.ModelViewSet):
    queryset = FragmentType.objects.all()
    serializer_class = FragmentTypeSerializer


class MatchProtocolViewSet(viewsets.ModelViewSet):
    queryset = MatchProtocol.objects.all()
    serializer_class = MatchProtocolSerializer


class MatchDscpViewSet(viewsets.ModelViewSet):
    queryset = MatchDscp.objects.all()
    serializer_class = MatchDscpSerializer

class StatsRoutesViewSet(viewsets.ViewSet):
    """
    A simple Vieset for retrieving statistics of the route by
    an authenticated user.
    """
    permission_classes = (IsAuthenticated,)
    def retrieve(self, request, pk=None):
        logger.info("StatsRoutesViewSet:::retrieve(): pk="+str(pk))
        queryset = Route.objects.all()
        from flowspec.views import routestats
        route = get_object_or_404(queryset, id=pk)
        logger.info("StatsRoutesViewSet:::retrieve(): route.name="+str(route.name))
        return routestats(request, route.name)

#############################################################################
#############################################################################

def global__get_users_routes_all(user):
         routes1=global__get_users_routes_by_its_peers(user)
         routes2=global__get_users_routes_by_applier_only(user)
         routes_all=list(routes1)+list(routes2)
         routes_all=list(set(routes_all)) # make uniques list
         return routes_all

# all these following functions return normal containers, not particular query sets
# if needed convert them back to query sets by convert_container_to_queryset
def global__get_users_routes_by_its_peers(user):
        #users_peers_set = set(user.userprofile.peers.all())
        users_peers = list(user.userprofile.peers.all())
        users_peer_ranges0 = [peer.networks.all() for peer in users_peers]

        # flatten list of lists
        users_peer_ranges = []
        for sub_list in users_peer_ranges0:
           users_peer_ranges += sub_list

        users_peer_ranges = list(set(users_peer_ranges)) # make elements unique

        logger.info("viewsets::global__get_users_routes_by_its_peers(): users_peer_ranges="+str(users_peer_ranges))

        #

        routes_all = list(Route.objects.filter())
        #routes_all = list(Route.objects)
        #temp1 = [obj for obj in routes_all]

        # has bad perf:
        #temp1 = [obj for obj in routes_all if len(set(obj.containing_peers()).intersection(users_peers_set))>0]

        temp1 = [obj for obj in routes_all if len(obj.containing_ip_networks(users_peer_ranges))>0]
        
        return temp1

def global__get_users_routes_by_applier_only(user):
        #return list(Rule.objects.filter(applier=user))
        return Route.objects.filter(applier=user)

#############################################################################
#############################################################################

