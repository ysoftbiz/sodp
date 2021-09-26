import logging

from django.conf import settings
from http.client import HTTPSConnection
from base64 import b64encode
from json import loads
from json import dumps

from collections import Counter
from sodp.utils import nlp
from time import sleep
from urllib.parse import urlparse

TOP_KEYWORDS=5
MAX_KEYWORDS=1000

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
        except Exception as e:
            logging.exception(e)
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
    else:
        logging.error("dataforseo - getVolume - response: %s" % str(response))
    return volume_keywords

def getKeywords(domain, urls):
    keywords_per_url = {}
    domain = urlparse(domain).netloc
    all_keywords = []

    post_data = [{
        "target": domain,
        "language_code": "en",
        "filters": [
            [
                "keyword_data.keyword_info.search_volume", "<>", 0
            ], "and",
            [
                "ranked_serp_element.serp_item.relative_url", "in", urls,
            ]
        ],
        "limit": MAX_KEYWORDS,
        "load_rank_absolute": True,
        "order_by": [
            "keyword_data.keyword_info.search_volume,desc"
        ]
    }]

    client = RestClient(settings.DATAFORSEO_EMAIL, settings.DATAFORSEO_PASSWORD)
    response = client.post("/v3/dataforseo_labs/ranked_keywords/live", post_data)
    if response["status_code"] == 20000:
        results = response["tasks"][0]["result"]
        if results:
            items = results[0]["items"]
            if items:
                final_keywords = []

                # get all keywords
                for keyword_info in items:
                    url = keyword_info["ranked_serp_element"]["serp_item"]["relative_url"]
                    if url not in keywords_per_url:
                        keywords_per_url[url] = []

                    keyword_words = keyword_info["keyword_data"]["keyword"]
                    keywords = nlp.getKeywords(keyword_words)
                    keywords_per_url[url].extend(keywords)

                # count popular
                for url, keywords in keywords_per_url.items():
                    counter = Counter(keywords)
                    most_common = counter.most_common(TOP_KEYWORDS)
                    topkw = [seq[0] for seq in most_common]
                    keywords_per_url[url] = topkw

                    all_keywords.extend(topkw)
    else:
        logging.error("dataforseo - getKeywords - response: %s" % str(response))

    return keywords_per_url, all_keywords
