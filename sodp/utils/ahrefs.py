import asyncio
import requests
import pandas as pd
import json

from urllib.parse import urlparse
from time import sleep

BASE_URL = "https://apiv2.ahrefs.com?"
LIMIT=15000

def getAhrefsInfo(token, domain, maxlength):
    # do not query more than length of the sitemap
    if (maxlength<LIMIT):
        limit = maxlength
    else:
        limit = LIMIT

    ahrefs_url = "{base_url}token={token}&target={domain}&output=json&from=pages_extended&mode=domain&limit={limit}&where=http_code%3D200&order_by=ahrefs_rank:desc".format(base_url=BASE_URL,
        token=token, domain=domain, limit=limit)
    return ahrefs_url

def getAhrefsUrls(token, domain, maxlength):
    domainparts = urlparse(domain)
    info = getAhrefsInfo(token, domainparts.netloc, maxlength)
    resp = requests.get(url=info)
    ahrefs_results = {}
    if resp and resp.status_code==200:
        data = resp.json()

        pages = data.get('pages', [])
        for page in pages:
            url = page.get("url", None)
            if url:
                url = urlparse(url).path
                ahrefs_results[url] = page

    return ahrefs_results
