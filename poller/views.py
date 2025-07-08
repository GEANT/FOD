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

# This component is used to retrieve stream of notifications from server into browser;
# the notifications are "announced" by flowspec/tasks.py announce() method;
# all notifications are passed via redis, the key is created as notifstream_%s, where %s is a peertag.
# The key is used to store stream of objects: {"m": "%s", "time": "timestamp"},
# where %s is a notification message, and timestamp is in "%Y-%m-%d %H:%M:%S"
# format.

import json

import uuid
import datetime
from django.shortcuts import render
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from peers.models import Peer
from gevent.event import Event
import redis

import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "poller.log", False)

def is_ajax(request):
  return request.headers.get("X-Requested-With") == "XMLHttpRequest"

def create_message(message, user, msgid, time, peer_id):
    """Create new message that will be sent in a response to client with text "message".
    Params:
        message: str text of the notification
        user: str username of logged in user
        str: str message id from redis
    Returns:
        dict with the following keys: id, body, user, time
    """
    data = {'id': msgid, 'body': message, 'user':user, 'time':time, 'peerid': peer_id}
    data['html'] = render_to_string('poll_message.html', {'message': data})
    return data


def json_response(value, **kwargs):
    kwargs.setdefault('content_type', 'text/javascript; charset=UTF-8')
    return HttpResponse(json.dumps(value), **kwargs)


class Msgs(object):
    cache_size = 500

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Msgs, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        logger.debug("poller::views(): initializing")
        self.user = None
        self.user_cache = {}
        self.user_cursor = {}
        self.cache = []
        self.new_message_event = None
        self.new_message_user_event = {}

    def main(self, request):
        #if self.user_cache:
        #    request.session['cursor'] = self.user_cache[-1]['id']
        #return render(request, 'poll.html', {'messages': self.user_cache})
        pass

    def message_existing(self, request, peer_id):
        if is_ajax(request):
            logger.debug("Polling all existing notifications")
            return self.message_updates(request, peer_id, "")
        return HttpResponseRedirect(reverse('group-routes'))

    def message_updates(self, request, peer_id, last_id=""):
        if is_ajax(request):
            if last_id:
                logger.debug("Polling updates of notifications since " + last_id)
            last_id = bytes(last_id, "utf-8")

            try:
                user = Peer.objects.get(pk=peer_id).peer_tag
                logger.debug("Polling by user %s", str(user))
            except:
                user = None
                return False
            r = redis.StrictRedis(host=settings.REDIS_HOST)
            key = "notifstream_%s" % user
            logger.debug(str((key, user)))
            if last_id and last_id != b"null":
                logger.debug("Polling from last_id %s", last_id)
                msgs = r.xrange(key, min=last_id)
            else:
                msgs = r.xrange(key)
            msglist = []
            for i, msg in msgs:
                if last_id != i:
                    msglist.append(create_message(msg[b"m"].decode("utf-8"), request.user.username, i.decode("utf-8"), msg[b"time"].decode("utf-8"), peer_id))
            logger.debug(str(msgs))
            if not msgs:
                return HttpResponse(content='', content_type=None, status=204)
            return json_response({'messages': msglist})

        return HttpResponseRedirect(reverse('group-routes'))


msgs = Msgs()
main = msgs.main

message_updates = msgs.message_updates
message_existing = msgs.message_existing


