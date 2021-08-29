from http.client import HTTPSConnection
from base64 import b64encode
from json import loads
from json import dumps

from urllib.parse import urlparse

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
            print(headers)
            connection.request(method, path, headers=headers, body=data)
            response = connection.getresponse()
            print(loads(response.read().decode()))
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

def getKeywords(client, domain, urls):
    post_data = dict()

    domain = urlparse(domain).netloc

    post_data[len(post_data)] = dict(
        target=domain,
        filters=[
            ["keyword_data.keyword_info.search_volume", "<>", 0],
            "and", 
            [
                ["ranked_serp_element.serp_item.relative_url", "in", urls],
            ]
        ]
    )
    # POST /v3/dataforseo_labs/ranked_keywords/live
    response = client.post("/v3/dataforseo_labs/ranked_keywords/live", post_data)
    if response["status_code"] == 20000:
        print(response)
        # do something with result
    else:
        print("error. Code: %d Message: %s" % (response["status_code"], response["status_message"]))
