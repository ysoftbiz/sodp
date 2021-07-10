from typing import Any

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.http import HttpRequest
from sodp.users.models import User
from django.urls import reverse

class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def get_login_redirect_url(self, request):
        print("He entrado en el redirect")
        url = super(AccountAdapter, self).get_login_redirect_url(request)
        user = request.user
        
        ahrefs_token = request.user.ahrefs_token
        google_token = request.user.google_token

        if not ahrefs_token or not google_token:
            url = reverse("users:credentials")


        else:
            url = reverse("users:detail", kwargs={"username": self.request.user.username})
        return url


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest, sociallogin: Any):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

