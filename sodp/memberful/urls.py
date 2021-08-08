from allauth.socialaccount.providers.oauth.urls import default_urlpatterns
from .provider import MemberfulProvider

urlpatterns = default_urlpatterns(MemberfulProvider)