import requests
import pandas as pd
import json

BASE_URL = "https://apiv2.ahrefs.com?"

def getAhrefsInfo(token, url):
    ahrefs_url = "{base_url}token={token}&target={url}&output=json&from=pages_extended&mode=exact".format(base_url=BASE_URL,
        token=token, url=url)

    try:
        r = requests.get(ahrefs_url)
        data = json.loads(r.content.decode('utf-8'))
        pages = data.get('pages', [])
        if len(pages)>0:
            return pages[0].get('backlinks', 0)
    except Exception as e:
        print(str(e))
    
    return 0