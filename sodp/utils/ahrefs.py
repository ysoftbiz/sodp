import requests
import pandas as pd
import json

from urllib.parse import urlparse


BASE_URL = "https://apiv2.ahrefs.com?"
LIMIT=10000

def getAhrefsInfo(token, domain):
    ahrefs_url = "{base_url}token={token}&target={domain}&limit={limit}&output=json&from=pages_extended&mode=domain&where=http_code%3D200&order_by=ahrefs_rank:desc".format(base_url=BASE_URL,
        token=token, domain=domain, limit=LIMIT)

    urls = {}
    try:
        r = requests.get(ahrefs_url)
        data = json.loads(r.content.decode('utf-8'))

        pages = data.get('pages', [])
        for page in pages:
            path = urlparse(page['url']).path
            urls[path] = page['dofollow']

    except Exception as e:
        print(str(e))
    
    return urls