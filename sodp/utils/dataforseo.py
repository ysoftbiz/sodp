from django.conf import settings
from http.client import HTTPSConnection
from base64 import b64encode
from json import loads
from json import dumps

from collections import Counter
from sodp.utils import nlp
from time import sleep
from urllib.parse import urlparse

KEYWORDS_NUMBER=25
TOP_KEYWORDS=5

from http.client import HTTPSConnection
from base64 import b64encode
from json import loads
from json import dumps

class RestClient:
    domain = "api.dataforseo.com"

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def request(self, path, method, data=None):
        connection = HTTPSConnection(self.domain)
        try:
            base64_bytes = b64encode(
                ("%s:%s" % (self.username, self.password)).encode("ascii")
                ).decode("ascii")
            headers = {'Authorization' : 'Basic %s' %  base64_bytes, 'Content-Encoding' : 'gzip'}
            connection.request(method, path, headers=headers, body=data)
            response = connection.getresponse()
            return loads(response.read().decode())
        finally:
            connection.close()

    def get(self, path):
        return self.request(path, 'GET')

    def post(self, path, data):
        if isinstance(data, str):
            data_str = data
        else:
            data_str = dumps(data)
        return self.request(path, 'POST', data_str)

# get keywords asynchronously
def getVolume(keywords):
    post_data = dict()
    tasks = []

    client = RestClient(settings.DATAFORSEO_EMAIL, settings.DATAFORSEO_PASSWORD)
    # get unique keywords and search the volume
    post_data = [{
        "keywords": keywords,
    }]

    response = client.post("/v3/keywords_data/google/search_volume/live", post_data)

    # iterate for each keyword
    volume_keywords = {}
    if response["status_code"] == 20000:
        data = response
        results = data["tasks"][0]["result"]
        if results:
            for volume_data in results:
                keyword = volume_data["keyword"]
                volume = volume_data["search_volume"]

                volume_keywords[keyword] = volume
    
    return volume_keywords