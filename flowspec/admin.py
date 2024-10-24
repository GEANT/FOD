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

from django.contrib import admin
from flowspec.models import MatchPort, MatchDscp, MatchProtocol, FragmentType, ThenAction, Route
from flowspec.forms import *
from accounts.models import UserProfile
from utils import proxy as PR
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from peers.models import *
from longerusername.forms import UserCreationForm, UserChangeForm


class RouteAdmin(admin.ModelAdmin):
    form = RouteForm
    actions = ['deactivate']
    search_fields = ['destination', 'name', 'applier__username']

    def deactivate(self, request, queryset):
        queryset = queryset.filter(status='ACTIVE')
        response = batch_delete.delay(queryset, reason="ADMININACTIVE")
        self.message_user(request, "Added request %s to job que. Check in a while for result" % response)
    deactivate.short_description = "Remove selected routes from network"

    def save_model(self, request, obj, form, change):
        obj.status = "PENDING"
        obj.save()
        if change:
            obj.commit_edit()
        else:
            obj.commit_add()

    def has_delete_permission(self, request, obj=None):
        return False

    list_display = ('name', 'status', 'applier_username', 'applier_peers', 'get_match', 'get_then', 'response', "expires", "comments")

    fieldsets = [
        (None, {'fields': ['name', 'applier']}),
        ("Match", {'fields': ['source', 'sourceport', 'destination', 'destinationport', 'port']}),
        ('Advanced Match Statements', {'fields': ['dscp', 'fragmenttype', 'icmpcode', 'icmptype', 'packetlength', 'protocol', 'tcpflag'], 'classes': ['collapse']}),
        ("Then", {'fields': ['then']}),
        ("Expires", {'fields': ['expires']}),
        (None, {'fields': ['comments', ]}),

    ]


class UserProfileInline(admin.StackedInline):
    model = UserProfile


class UserProfileAdmin(UserAdmin):
    search_fields = ['username']
    add_form = UserCreationForm
    form = UserChangeForm
    actions = ['deactivate', 'activate']
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_superuser', 'get_userprofile_peers')
    inlines = [UserProfileInline]

    def deactivate(self, request, queryset):
        queryset = queryset.update(is_active=False)
    deactivate.short_description = "Deactivate Selected Users"

    def activate(self, request, queryset):
        queryset = queryset.update(is_active=True)
    activate.short_description = "Activate Selected Users"

    def get_userprofile_peers(self, instance):
        # instance is User instance
        peers = instance.userprofile.peers.all()
        return ''.join(('%s, ' % (peer.peer_name)) for peer in peers)[:-2]

    get_userprofile_peers.short_description = "User Peer(s)"
#    fields = ('name', 'applier', 'expires')

    #def formfield_for_dbfield(self, db_field, **kwargs):
    #    if db_field.name == 'password':
    #        kwargs['widget'] = PasswordInput
    #    return db_field.formfield(**kwargs)

admin.site.unregister(User)
admin.site.register(MatchPort)
admin.site.register(MatchProtocol)
admin.site.register(MatchDscp)
admin.site.register(ThenAction)
admin.site.register(FragmentType)
admin.site.register(Route, RouteAdmin)
admin.site.register(User, UserProfileAdmin)
admin.site.disable_action('delete_selected')


