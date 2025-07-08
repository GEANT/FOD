#
# -*- coding: utf-8 -*- vim:fileencoding=utf-8:

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
from django.urls import re_path

from poller import views
urlpatterns = [
    #'poller.views',
    re_path('^$', views.main),
    # 1st call to get all existing messages
    re_path('^message/existing/(?P<peer_id>[\w\-]+)/$', views.message_existing, name='fetch-existing'),
    # update - get new messages
    re_path('^message/updates/(?P<peer_id>[\w\-]+)/$', views.message_updates, name='fetch-updates'),
    re_path('^message/updates/(?P<peer_id>[\w\-]+)/(?P<last_id>[\w\-]+)$', views.message_updates, name='fetch-updates')
]
