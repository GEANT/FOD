from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from rest_framework import viewsets
from flowspec.models import Route, ThenAction, FragmentType, MatchProtocol, MatchDscp

from flowspec.serializers import (
    RouteSerializer,
    ThenActionSerializer,
    FragmentTypeSerializer,
    MatchProtocolSerializer,
    MatchDscpSerializer)

from flowspec.validators import check_if_rule_exists
from rest_framework.response import Response

import os
import logging
FORMAT = '%(asctime)s %(levelname)s: %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
LOG_FILENAME = os.path.join(settings.LOG_FILE_LOCATION, 'viewsets.log')
handler = logging.FileHandler(LOG_FILENAME)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class RouteViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Route.objects.all()
    serializer_class = RouteSerializer

    def get_queryset(self):
        scope=""
        try:
          logger.debug("RouteViewSet::get_queryset(): param scope="+str(self.request.query_params['scope']))
          scope=self.request.query_params['scope'] 
        except: 
          pass

        if scope == "applier":
            return convert_container_to_queryset(self.get_users_routes_by_applier_only(), Route)
        elif scope == "peer":
            return convert_container_to_queryset(self.get_users_routes_by_its_peers(), Route)
        elif scope == "user":
            return convert_container_to_queryset(self.get_users_routes_all(), Route)

        if self.request.user.is_superuser:
            return Route.objects.all() # default for admin is all
        else:
            return convert_container_to_queryset(self.get_users_routes_all(), Route) #default for non-admin is "user"

    def get_users_routes_all(self):
        return global__get_users_routes_all(self.request.user)

    def get_users_routes_by_its_peers(self):
        return global__get_users_routes_by_its_peers(self.request.user)

    def get_users_routes_by_applier_only(self):
        return global__get_users_routes_by_applier_only(self.request.user)


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
                    logger.info("RouteViewSet::create(): obj.type="+str(type(obj)))
                    logger.info("RouteViewSet::create(): obj="+str(obj))
                    logger.info("RouteViewSet::create(): obj.dir="+str(dir(obj)))
                    logger.info("RouteViewSet::create(): obj.items="+str(obj.items))
                    logger.info("RouteViewSet::create(): obj.data="+str(obj.data))
                    logger.info("RouteViewSet::create(): obj.data.id="+str(obj.data["id"]))
                    route = get_object_or_404(self.get_queryset(), pk=obj.data["id"])
                    route.response = "N/A"
                    route.set_no_expire() # REST API created routes should have no expiration date

                    if requested_status == "ACTIVE":
                        route.status = "PENDING"
                        route.save()
                        route.commit_add()
                    elif requested_status == "INACTIVE":
                        route.status = "INACTIVE"
                        route.save()
                    else:
                        route.save()
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

        def work_on_active_object(obj, new_status):
            """
            Decides which `commit` action to choose depending on the
            requested status

            Cases:
            * `ACTIVE` ~> `INACTIVE`: The `Route` must be deleted from the
                flowspec device (`commit_delete`)
            * `ACTIVE` ~> `ACTIVE`: The `Route` is present, so it must be
                edited (`commit_edit`)

            :param new_status: the newly requested status
            :type new_status: str
            :param obj: the `Route` object
            :type obj: `flowspec.models.Route`
            """
            set_object_pending(obj)
            if new_status == 'INACTIVE':
                obj.commit_delete()
            else:
                obj.commit_edit()

        def work_on_inactive_object(obj, new_status):
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
        
        #if not partial:
        #   raise PermissionDenied('Permission Denied')

        obj = get_object_or_404(self.queryset, pk=pk)
        old_status = obj.status

        serializer = RouteSerializer(
            obj, context={'request': request},
            #data=request.DATA, partial=partial)
            data=request.data, partial=partial)
        logger.info("RouteViewSet::update(): request.data="+str(request.data))

        if serializer.is_valid():
            #new_status = serializer.object.status
            new_status = serializer.data["status"]
            requested_status = request.data["status"]
            #if requested_status == 'INACTIVE':
            new_status = requested_status
            #logger.info("RouteViewSet::update(): data="+str(request.data))
            logger.info("RouteViewSet::update(): pk="+str(pk))
            logger.info("RouteViewSet::update(): request="+str(requested_status))
            logger.info("RouteViewSet::update(): obj.type="+str(type(obj)))
            logger.info("RouteViewSet::update(): obj="+str(obj))
            logger.info("RouteViewSet::update(): old_status="+str(old_status)+", new_status="+str(new_status))
            super(RouteViewSet, self).update(request, pk, partial=partial)
            if old_status == 'ACTIVE':
                work_on_active_object(obj, new_status)
            elif old_status in ['INACTIVE', 'ERROR']:
                work_on_inactive_object(obj, new_status)
            logger.info("RouteViewSet::update(): obj="+str(obj))
            return Response(
                RouteSerializer(obj,context={'request': request}).data,
                status=200)
        else:
            return Response(serializer.errors, status=400)

    def pre_save(self, obj):
        # DEBUG
        if settings.DEBUG:
            if self.request.user.is_anonymous():
                from django.contrib.auth.models import User
                obj.applier = User.objects.all()[0]
            elif self.request.user.is_authenticated():
                obj.applier = self.request.user
            else:
                raise PermissionDenied('User is not Authenticated')
        else:
            obj.applier = self.request.user

    def post_save(self, obj, created):
        if created:
            obj.commit_add()

    def pre_delete(self, obj):
        logger.info("RouteViewSet::pre delete(): start")
        if True or not self.request.user.is_superuser:
           raise PermissionDenied('Permission Denied')
        logger.info("RouteViewSet::pre delete: pre commit_delete")
        obj.commit_delete()

    def delete(self, request, pk=None, partial=False):
        obj = get_object_or_404(self.queryset, pk=pk)
        logger.info("RouteViewSet::delete(): pk="+str(pk)+" obj="+str(obj))

        username_request = request.user.username
        user_is_admin = request.user.is_superuser
        full_delete_is_allowed = (user_is_admin and settings.ALLOW_DELETE_FULL_FOR_ADMIN) or settings.ALLOW_DELETE_FULL_FOR_USER_ALL or (username_request in settings.ALLOW_DELETE_FULL_FOR_USER_LIST)
        logger.info("RouteViewSet::delete(): username_request="+str(username_request)+" user_is_admin="+str(user_is_admin)+" => full_delete_is_allowed="+str(full_delete_is_allowed))

        #if True or not self.request.user.is_superuser():
        if not full_delete_is_allowed:
           raise PermissionDenied('Permission Denied')
        logger.info("RouteViewSet::delete(): pre commit_delete")
        obj.commit_delete()

    def destroy(self, request, pk=None):
        obj = get_object_or_404(self.queryset, pk=pk)
        logger.info("RouteViewSet::destroy(): pk="+str(pk)+" obj="+str(obj))
        logger.info("RouteViewSet::destroy(): pre commit_delete")

        username_request = request.user.username
        user_is_admin = request.user.is_superuser
        full_delete_is_allowed = (user_is_admin and settings.ALLOW_DELETE_FULL_FOR_ADMIN) or settings.ALLOW_DELETE_FULL_FOR_USER_ALL or settings.ALLOW_DELETE_FULL_FOR_USER_LIST.contains(username_request)
        logger.info("RouteViewSet::destroy(): username_request="+str(username_request)+" user_is_admin="+str(user_is_admin)+" => full_delete_is_allowed="+str(full_delete_is_allowed))

        if obj.status == 'ACTIVE':
          if full_delete_is_allowed:
            obj.status = "PENDING_TODELETE"
          else:
            obj.status = "PENDING"
          obj.response = "N/A"
          obj.save()
          obj.commit_delete()
          serializer = RouteSerializer(obj, context={'request': request})
          return Response(serializer.data)
        else:
          try:
            #if not settings.ALLOW_ADMIN__FULL_RULEDEL or not self.request.user.is_superuser:
            if not full_delete_is_allowed:
              raise PermissionDenied('Permission Denied')
          except Exception as e:
              raise PermissionDenied('Permission Denied')
          # this will delete the rule from DB
          return super(RouteViewSet, self).destroy(self, request, pk=pk)

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
# global helpers 

# class1's attribute 'id' should be existing and be the primary key, e.g., be a Django model class
def convert_container_to_queryset(list1, class1):
         #temp1_ids = [obj.id for obj in list1]
         temp1_ids = [obj.id for obj in list1 if obj != None]
         temp2_ids = set(temp1_ids)
         return class1.objects.filter(id__in=temp2_ids)

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
        users_peers_set = set(user.userprofile.peers.all())
        routes_all = list(Route.objects.filter())
        #routes_all = list(Route.objects)
        #temp1 = [obj for obj in routes_all]
        temp1 = [obj for obj in routes_all if len(set(obj.containing_peers()).intersection(users_peers_set))>0]
        return temp1

def global__get_users_routes_by_applier_only(user):
        #return list(Rule.objects.filter(applier=user))
        return Route.objects.filter(applier=user)

#############################################################################
#############################################################################

