from django.utils.translation import ugettext as _
from django.db.models.signals import class_prepared
from django.core.validators import MaxLengthValidator
from flowspy.monkey_patch import MAX_USERNAME_LENGTH

def longer_username(sender, *args, **kwargs):
    if sender.__name__ == "User" and sender.__module__ == "django.contrib.auth.models":
        sender._meta.get_field("username").max_length = MAX_USERNAME_LENGTH()
        # For Django 1.2 to work, the validator has to be declared apart from max_length
        sender._meta.get_field("username").validators = [MaxLengthValidator(MAX_USERNAME_LENGTH())]
        #sender._meta.get_field("username").help_text = _("Required, %s characters or fewer. Only letters, numbers, and @, ., +, -, or _ characters." % MAX_USERNAME_LENGTH())
class_prepared.connect(longer_username)
