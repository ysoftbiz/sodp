import json
import requests
from django.conf import settings
from pprint import pprint

from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)

from .provider import MemberfulProvider


class MemberfulOAuthAdapter(OAuth2Adapter):
    provider_id = MemberfulProvider.id
    request_token_url = settings.MEMBERFUL_TOKEN_URL
    access_token_url = settings.MEMBERFUL_TOKEN_URL
    authorize_url = settings.MEMBERFUL_AUTH_URL
    supports_state = False

    def get_graphql_query(self, token, query):
        headers = {"Authorization": str(token)}
        request = requests.get(settings.MEMBERFUL_GRAPHQL_ENDPOINT+"?access_token=%s&query=%s" % (str(token), query))
        if request.status_code == 200:
            return request.json()
        else:
            raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))

    def complete_login(self, request, app, token, response):
        query = """
{
  currentMember {
    email
    fullName
    id
    unrestrictedAccess
  }
}        
        """
        graphdata = self.get_graphql_query(token, query)

        return self.get_provider().sociallogin_from_response(request, graphdata)


oauth_login = OAuth2LoginView.adapter_view(MemberfulOAuthAdapter)
oauth_callback = OAuth2CallbackView.adapter_view(MemberfulOAuthAdapter)