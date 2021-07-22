from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.db import models
from oauth2client import client

import httplib2

class User(AbstractUser):
    """Default user for SODP."""
    #: First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    ahrefs_token = CharField(_("ahrefs_token"), blank=True, null=True, max_length=255)
    google_api_token = CharField(_("google_api_token"), blank=True, null=True, max_length=255)
    google_refresh_token = CharField(_("google_refresh_token"), blank=True, null=True, max_length=255)
    first_name = None  # type: ignore
    last_name = None  # type: ignore

    def get_absolute_url(self):
        """Get url for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})

    def disableGoogleCredential(self):
        self.google_token = None
        self.save(update_fields=['google_token'])

    def getGoogleCredentials(self, google_token):
        try:
            cred = client.GoogleCredentials(None, settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET,
                                            google_token, None, "https://accounts.google.com/o/oauth2/token", None)
            http = cred.authorize(httplib2.Http())
            cred.refresh(http)

            return cred
        except:
            return False