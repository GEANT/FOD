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
from django.contrib.auth.models import AbstractBaseUser, User, BaseUserManager
from peers.models import Peer
from flowspec.models import Route

# TODO: dependency issue: move logging_utils to general package
import flowspec.logging_utils
logger = flowspec.logging_utils.logger_init_default(__name__, "accounts_model.log", False)

#


#

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    peers = models.ManyToManyField(Peer, related_name='user_profile')
    objects = BaseUserManager()
    USERNAME_FIELD = 'username'

    class Meta:
        permissions = (
            ("overview", "Can see registered users and rules"),
        )

    def username(self):
        return "%s" % (self.user.username)

    def __unicode__(self):
        return self.username()

    def get_address_space(self):
        networks = self.domain.networks.all()
        if not networks:
            return False
        return networks

    @property
    def get_owned_rules(self):
      routes_owned = Route.objects.filter(applier=self.user)   
      #logger.info("get_owned_rules(): self="+str(self)+" => routes_owned="+str(routes_owned))
      return routes_owned

    @property
    def get_related_user__for_adopting_on_user_deletion(self):
      user = self.user
      users_peers = self.peers.all()
      users_peers1 = None
      logger.info("get_related_user__for_adopting_on_user_deletion(): => users_peers="+str(users_peers))
      user_related1 = None
      if len(users_peers)==1:
        users_peers1 = users_peers[0]
        logger.info("get_related_user__for_adopting_on_user_deletion(): => users_peers[0]="+str(users_peers1))

        users_related = User.objects.filter(userprofile__peers__in=users_peers)
        logger.info("get_related_user__for_adopting_on_user_deletion(): => users_related="+str(users_related))
        user_related1 = None
        for user2 in users_related:
          if user2 != user:
              user_related1=user2
              break

      return user_related1

    # deleting of rules by this account is allowed
    def is_delete_allowed(self):
        user_is_admin = self.user.is_superuser
        username = self.username
        return (user_is_admin and settings.ALLOW_DELETE_FULL_FOR_ADMIN) or settings.ALLOW_DELETE_FULL_FOR_USER_ALL or (username in settings.ALLOW_DELETE_FULL_FOR_USER_LIST)

#

from django.dispatch import receiver
from django.db.models.signals import pre_delete

#@receiver(pre_delete, sender=UserProfile)
@receiver(pre_delete, sender=User)
def user_pre_delete_handler(sender, instance, **kwargs):
    logger.info("user_pre_delete_handler(): pre_delete instance="+str(instance))
    user_owned_rules_adopt_to_related_user(instance)

def user_owned_rules_adopt_to_related_user(user):
    routes_owned = Route.objects.filter(applier=user)   
    logger.info("user_owned_rules_adopt_to_related_user(): => routes_owned="+str(routes_owned))

    #users_peers = user.userprofile.peers.all()
    #users_peers1 = None
    #logger.info("user_owned_rules_adopt_to_related_user(): => users_peers="+str(users_peers))
    #if len(users_peers)==1:
    #  users_peers1 = users_peers[0]
    #  logger.info("user_owned_rules_adopt_to_related_user(): => users_peers[0]="+str(users_peers1))
    #  #peers1_userprofiles = users_peers[0].user_profile
    #  #logger.info("user_owned_rules_adopt_to_related_user(): => peers1_userprofiles="+str(peers1_userprofiles))

    #  users_related = User.objects.filter(userprofile__peers__in=users_peers)
    #  logger.info("user_owned_rules_adopt_to_related_user(): => users_related="+str(users_related))
    #  user_related1 = None
    #  for user2 in users_related:
    #      if user2 != user:
    #          user_related1=user2
    #          break

    #  logger.info("user_owned_rules_adopt_to_related_user(): => user_related1="+str(user_related1))
    user_related1 = user.userprofile.get_related_user__for_adopting_on_user_deletion()

    if user_related1!=None:
      if len(routes_owned)>0:
        logger.info("user_owned_rules_adopt_to_related_user(): len="+str(len(routes_owned)))
        for route in routes_owned:
          logger.info("user_owned_rules_adopt_to_related_user(): owned route="+str(route))
          route.applier = user_related1
          logger.info("user_owned_rules_adopt_to_related_user(): reassigning owned route="+str(route)+" by user to be deleted ("+str(user)+") to new owner "+str(user_related1))
          route.save()

    return (routes_owned, user_related1, users_peers1)

