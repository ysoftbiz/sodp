from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.db import models


class User(AbstractUser):
    """Default user for SODP."""
    #: First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    ahrefs_token = CharField(_("ahrefs_token"), blank=True, null=True, max_length=255)
    google_token = CharField(_("google_token"), blank=True, null=True, max_length=255)
    #ahrefs_token = models.CharField(serializers.CharField(required=False, max_length=255, allow_blank=True))
    #google_token = models.CharField(.CharField(required=False, max_length=255, allow_blank=True))
    first_name = None  # type: ignore
    last_name = None  # type: ignore

    def get_absolute_url(self):
        """Get url for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})

