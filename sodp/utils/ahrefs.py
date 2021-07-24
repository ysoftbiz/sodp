import requests
import pandas as pd
import json

BASE_URL = "https://apiv2.ahrefs.com?"
LIMIT = 5000

def getAhrefsInfo(token, domain):
    ahrefs_url = "{url}token={token}&target={domain}&limit={limit}&output=json&from=pages_extended&mode=domain&order_by=ahrefs_rank:desc".format(url=BASE_URL,
    token=token, domain=domain, limit=LIMIT)

    try:
        r = requests.get(ahrefs_url).content
        data = json.loads(r)
        df = pd.json_normalize(data)
        return df
    except Exception as e:
        print(str(e))
        return False