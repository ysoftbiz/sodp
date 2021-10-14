import asyncio
import requests
import pandas as pd
import json

from aiohttp import ClientSession
from urllib.parse import urlparse
from time import sleep

BASE_URL = "https://apiv2.ahrefs.com?"
LIMIT=15000

def getAhrefsInfo(token, domain):
    ahrefs_url = "{base_url}token={token}&target={domain}&output=json&from=pages_extended&mode=domain&limit={LIMIT}&where=http_code%3D200&order_by=ahrefs_rank:desc".format(base_url=BASE_URL,
        token=token, domain=domain)
    return ahrefs_url

async def getAhrefsUrls(token, domain):
    info = getAhrefsInfo(token, domain)
    resp = requests.get(url=info)
    if resp:
        data = resp.json()

        pages = data.get('pages', [])
        if len(pages)>0:
            url = pages[0].get("url", None)
            if url:
                url = urlparse(url).path
                ahrefs_results[url] = pages[0]

    return ahrefs_results
