"""
Serializers for flowspec models
"""
from rest_framework import serializers
from flowspec.models import (
    Route, MatchPort, ThenAction, FragmentType, MatchProtocol, MatchDscp)
from flowspec.validators import (
    clean_source, clean_destination, clean_expires, clean_status, clean_bgpextendedcommunity, clean_route_form)

from django.conf import settings

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "flowspec_serializers.log", False)

class ThenActionSerializer(serializers.Serializer):
    class Meta:
        model = Route
        fields = ('id', 'action', 'action_value')
        read_only_fields = ('id')

    def to_representation(self, obj):
        if obj.action_value:
            return f"{obj.action}:{obj.action_value}"
        return obj.action

    def to_internal_value(self, data):
        action_desc = str(data).split(":")
        action = action_desc[0]
        action_value = action_desc[1] if len(action_desc) > 1 else "" 
        try:
            return ThenAction.objects.get(action=action, action_value=action_value)
        except ThenAction.DoesNotExist:
            raise serializers.ValidationError('ThenAction does not exist.')

class MatchProtocolSerializer(serializers.Serializer):
    def to_representation(self, obj):
        return obj.protocol

    def to_internal_value(self, data):
        try:
            return MatchProtocol.objects.get(protocol=data)
        except MatchProtocol.DoesNotExist:
            raise serializers.ValidationError('MatchProtocol does not exist.')

class FragmentTypeSerializer(serializers.Serializer):
    def to_representation(self, obj):
        return obj.fragmenttype

    def to_internal_value(self, data):
        try:
            return FragmentType.objects.get(fragmenttype=data)
        except FragmentType.DoesNotExist:
            raise serializers.ValidationError('FragmentType does not exist.')

class RouteSerializer(serializers.HyperlinkedModelSerializer):
    """
    A serializer for `Route` objects
    """
    applier = serializers.CharField(source='applier.username', read_only=True)

    def create(self, validated_data):
        if "applier" not in validated_data:
            u = self.context.get('request').user
            validated_data["applier"] = u
        if "expires" not in validated_data and "isnonexpire" not in validated_data :
            #validated_data["isnonexpire"] = True
            validated_data["expires"] = "2999-01-01"
        protocol = validated_data.pop('protocol', set())
        then = validated_data.pop('then')
        fragmenttype = validated_data.pop('fragmenttype', set())
        try:
            status = validated_data.pop("status")
        except KeyError:
            status = 'INACTIVE'
            validated_data["status"] = status
        route = Route.objects.create(**validated_data)
        route.protocol.set(protocol)
        route.fragmenttype.set(fragmenttype)
        route.then.set(then)
        return route

    def validate_applier(self, attrs, source):
        user = self.context.get('request').user
        return source

    #def validate_source(self, attrs, source):
    def validate_source(self, source):
        request = self.context.get('request')
        if request==None:
          return source
        else:
          user = request.user
          res = clean_source(user, source)
          if res != source:
              raise serializers.ValidationError(res)
          #return attrs
          return res

    #def validate_destination(self, attrs, source):
    def validate_destination(self, destination):
        request = self.context.get('request')
        if request==None:
          return destination
        else:
          user = request.user
          #destination = attrs.get('destination')
          res = clean_destination(user, destination)
          if res != destination:
            raise serializers.ValidationError(res)
          #return attrs
          return res

    #def validate_expires(self, attrs, source):
    def validate_expires(self, expires):
        #expires = attrs.get('expires')
        res = clean_expires(expires)
        if res != expires:
            raise serializers.ValidationError(res)
        #return attrs
        return res

    #def validate_status(self, attrs, source):
    def validate_status(self, status):
        #status = attrs.get('status')
        res = clean_status(status)
        if res != status:
            raise serializers.ValidationError(res)
        #return attrs
        return res

    def validate_bgpextendedcommunity(self, value):
        res = clean_bgpextendedcommunity(value)
        if res != value:
            raise serializers.ValidationError(res)
        return res

    def validate(self, data):
        if self.context and self.context["request"] and self.context["request"].method == "POST":
            if "applier" not in data:
                u = self.context.get('request').user
                logger.info("Adding applier according to authentized user %s" % u.username)
                data["applier"] = u
            error = clean_route_form(data) 
            if error:
                raise serializers.ValidationError(error)
        return super().validate(data)

    def update(self, instance, validated_data):
        if 'name' in validated_data:
            del validated_data["name"]	

        if "expires" not in validated_data and "isnonexpire" not in validated_data :
            #validated_data["isnonexpire"] = True
            validated_data["expires"] = "2999-01-01"

        fragmenttype = validated_data.pop('fragmenttype', None)
        if fragmenttype:
            instance.fragmenttype.set(fragmenttype)

        protocol = validated_data.pop('protocol', None)
        if protocol:
            instance.protocol.set(protocol)

        then = validated_data.pop('then', None)
        if then:
            instance.then.set(then)

        instance =  super().update(instance, validated_data)
        return instance

    then = ThenActionSerializer(many=True)
    protocol = MatchProtocolSerializer(many=True, required=False)
    fragmenttype = FragmentTypeSerializer(many=True, required=False)

    class Meta:
        model = Route
        fields = (
            'name', 'id', 'comments', 
            'applier', 
            'packetlength',
            'source', 'destination', 
            'dscp', 'fragmenttype',
            'protocol',
            'icmptype', 'icmpcode', 
            'sourceport', 'destinationport', 'port', 
            'tcpflag', 
            'then', 
            'filed', 'last_updated', 
            'status', 'expires', 'response', 
            'requesters_address',
            'bgprd',
            'bgpextendedcommunity')
        read_only_fields = (
            'id', 'requesters_address', 'filed', 'last_updated', 'response')


class PortSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = MatchPort
        fields = ('id', 'port', )
        read_only_fields = ('id', )

class MatchDscpSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = MatchDscp
        fields = ('id', 'dscp', )
        read_only_fields = ('id', )
