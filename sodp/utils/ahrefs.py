import asyncio
import requests
import pandas as pd
import json

from aiohttp import ClientSession
from urllib.parse import urlparse
from time import sleep

BASE_URL = "https://apiv2.ahrefs.com?"
LIMIT=1

async def fetchAhrefsUrl(url, session):
    async with session.get(url) as response:
        return await response.read()

def getAhrefsInfo(token, domain, url):
    fullurl = "%s%s" % (urlparse(domain).netloc, url)
    ahrefs_url = "{base_url}token={token}&target={fullurl}&output=json&from=pages_extended&mode=exact".format(base_url=BASE_URL,
        token=token, fullurl=fullurl)
    return ahrefs_url

def getAhrefsPageInfo(token, domain, url):
    fullurl = "%s%s" % (urlparse(domain).netloc, url)

    ahrefs_url = "{base_url}token={token}&target={fullurl}&output=json&from=pages_info&mode=exact".format(base_url=BASE_URL,
        token=token, fullurl=fullurl, limit=LIMIT)
    return ahrefs_url

async def getAhrefsUrls(token, domain, urls):
    tasks, tasks_pages = [], []
    ahrefs_results, ahrefs_results_pages = {}, {}
    async with ClientSession() as session:
        for url in urls:
            sleep(0.005)
            # queue ahrefs queries
            info = getAhrefsInfo(token, domain, url)
            page = getAhrefsPageInfo(token, domain, url)
            task = asyncio.ensure_future(fetchAhrefsUrl(info, session))
            tasks.append(task)

            task = asyncio.ensure_future(fetchAhrefsUrl(page, session))
            tasks_pages.append(task)

        responses = await asyncio.gather(*tasks)
        for response in responses:
            data = json.loads(response.decode('utf-8'))

            pages = data.get('pages', [])
            if len(pages)>0:
                url = pages[0].get("url", None)
                if url:
                    url = urlparse(url).path
                    ahrefs_results[url] = pages[0]

        responses = await asyncio.gather(*tasks_pages)
        for response in responses:
            data = json.loads(response.decode('utf-8'))

            pages = data.get('pages', [])
            if len(pages)>0:
                url = pages[0].get("url", None)
                if url:
                    url = urlparse(url).path
                    ahrefs_results_pages[url] = pages[0]

    return ahrefs_results, ahrefs_results_pages
