import logging
import pandas as pd

MAX_PAGES = 5000

from usp.tree import sitemap_tree_for_homepage

def parseSitemap(url):
    logging.getLogger("usp.fetch_parse").setLevel(logging.WARNING)
    logging.getLogger("usp.helpers").setLevel(logging.WARNING)
    logging.getLogger("usp.tree").setLevel(logging.WARNING)
    df = pd.DataFrame(columns=['loc'])        

    tree = sitemap_tree_for_homepage(url)
    count = 0
    if tree:
        # we need to sort pages by date modification desc
        all_pages = list(tree.all_pages())
        all_pages.sort(key=lambda x:x.last_modified, reverse=True)
        for page in all_pages:
            count+=1
            df = df.append({'loc': page.url}, ignore_index=True)
            if count>=MAX_PAGES:
                # just break on the 5k pages
                break

    return df
        

