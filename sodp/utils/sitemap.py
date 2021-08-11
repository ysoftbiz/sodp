import logging
import pandas as pd

from django.core.files.storage import default_storage

def parseSitemap(url):
    logging.getLogger("usp.fetch_parse").setLevel(logging.WARNING)
    logging.getLogger("usp.helpers").setLevel(logging.WARNING)
    logging.getLogger("usp.tree").setLevel(logging.WARNING)
    df = pd.DataFrame(columns=['loc'])        

    tree = sitemap_tree_for_homepage(url)
    if tree:
        # we need to sort pages by date modification desc
        all_pages = list(tree.all_pages())
        all_pages.sort(key=lambda x:(x.last_modified is None, x.last_modified), reverse=True)
        for page in all_pages:
            df = df.append({'loc': page.url}, ignore_index=True)
    return df

def getUrlsFromFile(user, path):
    # generate path
    csv_path = "reports/{user_id}/{path}".format(user_id=user, path=path)
    if (default_storage.exists(csv_path)):
        # read object
        with default_storage.open(csv_path) as handle:
            df = pd.read_csv(handle)
            if not df.empty:
                return df.iterrows()

    return []

        

