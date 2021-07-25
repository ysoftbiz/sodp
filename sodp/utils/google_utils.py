import httplib2
import google.oauth2.credentials
import google_auth_oauthlib.flow

import os
import pandas as pd

from apiclient.discovery import build
from pprint import pprint

from oauth2client import GOOGLE_REVOKE_URI, GOOGLE_TOKEN_URI, client
from django.conf import settings
from django.urls import reverse

DIMS = ['ga:pagePath', 'ga:segment']
METRICS = ['ga:pageViews', 'ga:uniquePageViews', 'ga:timeOnPage', 'ga:entrances', 'ga:bounceRate', 'ga:exitRate', 'ga:pageValue']
SEGMENTS = ['gaid::-1','gaid::-5']
PAGESIZE = 5000

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
        return False        

# get all the projects that the user has with that credentials
def getProjectsFromCredentials(credentials):
    if settings.USE_DUMMY_GOOGLE_DATA:
        projects = {
            "1": "Account 1 - Project 1 - http://sodp-test.herokuapp.com",
            "2": "Account 1 - Project 2 - http://www.ysoft.biz",
            "3": "Account 2 - Project 1 - http://www.google.com",
        }
    else:
        analytics = build('analytics', 'v3', credentials=credentials)
        accounts = analytics.management().accounts().list().execute()

        projects = {}
        if accounts.get('items'):
            for item in accounts.get('items'):
                account_id = item["id"]
                
                # now lets retrieve all the views
                profiles = analytics.management().profiles().list(accountId=account_id,
                                                        webPropertyId='~all'
                                                        ).execute()

                for profile in profiles.get('items'):
                    projects[profile["id"]] = item["name"]+" - "+profile["name"]+" - "+profile["websiteUrl"]

    return projects

# returns a dump of the desired stats for the specific credentials and view
def getStatsFromView(credentials, view_id, startDate, endDate):
    analytics = build('analyticsreporting', 'v4', credentials=credentials)

    data = analytics.reports().batchGet(
      body={
        'reportRequests': [
        {
          'viewId': view_id,
          'pageSize': PAGESIZE,
          'dateRanges': [{'startDate': startDate.strftime("%Y-%m-%d"), 'endDate': endDate.strftime("%Y-%m-%d")}],
          'metrics':  [{'expression': exp} for exp in METRICS],
          'dimensions': [{'name': name} for name in DIMS],
          'segments':  [{"segmentId": segment} for segment in SEGMENTS],   # organic traffic
        }]
      }
    ).execute()

    # embed into a pandas dataset
    data_dic = {f"{i}": [] for i in DIMS + METRICS}
    for report in data.get('reports', []):
        rows = report.get('data', {}).get('rows', [])
        for row in rows:
            for i, key in enumerate(DIMS):
                data_dic[key].append(row.get('dimensions', [])[i]) # Get dimensions
            dateRangeValues = row.get('metrics', [])
            for values in dateRangeValues:
                all_values = values.get('values', []) # Get metric values
                for i, key in enumerate(METRICS):
                    data_dic[key].append(all_values[i])
            
    df = pd.DataFrame(data=data_dic)
    df.columns = [col.split(':')[-1] for col in df.columns]
    df.tail()
    return df
