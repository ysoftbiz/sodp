import httplib2
import google.oauth2.credentials
import google_auth_oauthlib.flow

import os

from apiclient.discovery import build
from pprint import pprint

from oauth2client import GOOGLE_REVOKE_URI, GOOGLE_TOKEN_URI, client
from django.conf import settings
from django.urls import reverse

def getGoogleConfig(request):
    return {
        "installed": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uris": [ request.build_absolute_uri('/')+"users/~googlecredentials/", "urn:ietf:wg:oauth:2.0:oob"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://accounts.google.com/o/oauth2/token"
        }
    }

def getScopes():
    return [
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.googleapis.com/auth/analytics.readonly',
        'https://www.googleapis.com/auth/userinfo.email',
        'openid'        
    ]
def generateGoogleURL(request):

    # Use the client_secret.json file to identify the application requesting
    # authorization. The client ID (from that file) and access scopes are required.
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_config=getGoogleConfig(request),
        scopes=getScopes())

    # Indicate where the API server will redirect the user after the user completes
    # the authorization flow. The redirect URI is required. The value must exactly
    # match one of the authorized redirect URIs for the OAuth 2.0 client, which you
    # configured in the API Console. If this value doesn't match an authorized URI,
    # you will get a 'redirect_uri_mismatch' error.
    flow.redirect_uri = request.build_absolute_uri('/')+"users/~googlecredentials/"

    # Generate URL for request to Google's OAuth 2.0 server.
    # Use kwargs to set optional request parameters.
    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        prompt='consent',
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true')

    return authorization_url    

def getUserCredentials(request):
    os.environ['AUTHLIB_INSECURE_TRANSPORT'] = '1'

    try:
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config=getGoogleConfig(request),
            scopes=getScopes())
        flow.redirect_uri = request.build_absolute_uri('/')+"users/~googlecredentials/"
        authorization_response = request.build_absolute_uri(request.get_full_path()).replace("http:", "https:", 1)
        flow.fetch_token(authorization_response=authorization_response)
        credentials = flow.credentials
        return credentials
    except Exception as e:
        print(str(e))
        return False

def getOfflineCredentials(auth_token, refresh_token):
    try:
        credentials = client.OAuth2Credentials(
            access_token=None,  # set access_token to None since we use a refresh token
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            refresh_token=refresh_token,
            token_expiry=None,
            token_uri=GOOGLE_TOKEN_URI,
            user_agent=None,
            revoke_uri=GOOGLE_REVOKE_URI)
        return credentials       
    except Exception as e:
        print(str(e))
        return False        

# get all the projects that the user has with that credentials
def getProjectsFromCredentials(credentials):
  analytics = build('analytics', 'v3', credentials=credentials)
  accounts = analytics.management().accounts().list().execute()

  projects = {}
  if accounts.get('items'):
      for item in accounts.get('items'):
          projects[item["id"]] = item["name"]

  return projects