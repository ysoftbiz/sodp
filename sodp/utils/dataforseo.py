import asyncio

from django.conf import settings
from http.client import HTTPSConnection
from base64 import b64encode
from json import loads
from json import dumps

from aiohttp import ClientSession
from collections import Counter
from sodp.utils import nlp
from time import sleep
from urllib.parse import urlparse

KEYWORDS_NUMBER=25
TOP_KEYWORDS=5

# get keyword per url
async def getDataForSeoRequest(url, headers, post_data, session):
    async with session.post(url, headers=headers, json=post_data) as r:
        return await r.json()        

# get keywords asynchronously
async def getKeywords(domain, urls):
    post_data = dict()
    tasks = []

    domain = urlparse(domain).netloc

    base64_bytes = b64encode(
                ("%s:%s" % (settings.DATAFORSEO_EMAIL, settings.DATAFORSEO_PASSWORD)).encode("ascii")
                ).decode("ascii")
    headers = {'Authorization' : 'Basic %s' %  base64_bytes, 'Content-Encoding' : 'gzip'} 

    async with ClientSession(headers=headers) as session:
        for url in urls:
            sleep(0.005)

            post_data = [{
                "target":domain,
                "filters": [
                    ["ranked_serp_element.serp_item.relative_url", "=", url],
                ],
                "item_types": ["organic",],
                "order_by": ["ranked_serp_element.serp_item.relative_url,asc", "keyword_data.keyword_info.competition,desc"],
                "limit": KEYWORDS_NUMBER
            }]

            task = asyncio.ensure_future(getDataForSeoRequest("https://api.dataforseo.com/v3/dataforseo_labs/ranked_keywords/live",
                headers, post_data, session))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        keywords_per_url = {}
        keywords_for_volume = []

        # get keyword per url
        for response in responses:
            data = response
            if data["status_code"] == 20000:
                results = data["tasks"][0]["result"]
                if results:
                    items = results[0]["items"]
                    if items:
                        url = items[0]["ranked_serp_element"]["serp_item"]["relative_url"]
                        final_keywords = []

                        # get all keywords
                        for keyword in items:
                            keyword_words = keyword["keyword_data"]["keyword"]
                            keywords = nlp.getKeywords(keyword_words)
                            final_keywords.extend(keywords)

                        # count popular
                        counter = Counter(final_keywords)
                        most_common = counter.most_common(TOP_KEYWORDS)
                        keywords_per_url[url] = {"keywords": [seq[0] for seq in most_common], "volume": 0 }
                        if len(most_common)>0:
                            keywords_for_volume.append(most_common[0][0])

        # get unique keywords and search the volume
        keyword_tasks = []
        for keyword in list(set(keywords_for_volume)):
            sleep(0.005)

            post_data = [{
                "keywords": [keyword,],
            }]

            keyword_task = asyncio.ensure_future(getDataForSeoRequest("https://api.dataforseo.com/v3/keywords_data/google/search_volume/live",
                headers, post_data, session))
            keyword_tasks.append(keyword_task)

        keyword_responses = await asyncio.gather(*keyword_tasks)
        # iterate for each keyword
        for response in keyword_responses:
            if response["status_code"] == 20000:
                data = response
                results = data["tasks"][0]["result"]
                if results:
                    keyword = data["tasks"][0]["data"]["keywords"][0]
                    volume = results[0]["search_volume"]

                    # search by all urls, looking for first keyword
                    for url, keywords in keywords_per_url.items():
                        if len(keywords_per_url[url]["keywords"])>0 and keywords_per_url[url]["keywords"][0]==keyword:
                            # search volume for first keyword
                            keywords_per_url[url]["volume"] = volume

        return keywords_per_url