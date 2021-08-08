from allauth.socialaccount import providers

from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider

from django.conf import settings as djangosettings

class MemberfulAccount(ProviderAccount):
    pass


class MemberfulProvider(OAuth2Provider):
    """Memberful OAuth authentication backend"""
    id = 'memberful'
    name = 'Memberful'
    account_class = MemberfulAccount

    def get_auth_params(self, request, action):
        return {"client_id": djangosettings.MEMBERFUL_CLIENT_ID, "response_type": "code", "state": "memberful"}

    def extract_uid(self, data):
        id = data["data"]["currentMember"]["id"]
        return id

    def extract_common_fields(self, data):
        extraData = dict(name=data["data"]["currentMember"]["fullName"], email=data["data"]["currentMember"]["email"])
        return extraData

providers.registry.register(MemberfulProvider)
