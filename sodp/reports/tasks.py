from config import celery_app
from celery import shared_task
from celery.contrib import rdb
from pprint import pprint

from sodp.reports.models import report
from sodp.utils import google_utils, ahrefs
from sodp.utils import sitemap as sm

from urllib.parse import urlparse

SUFFIXES = ( '.xml', '.pdf', '.doc', '.docx' )

def setErrorStatus(report, error_code):
    pass

@shared_task(name="processReport")
def processReport(pk):
    # get report data with that PK
    obj = report.objects.get(pk=pk)
    if obj:
        # check if report is pending
        #if obj.status == 'pending':
        #    # set to processing
        #    obj.status='process'
        #    obj.save(update_fields=["status"])

        # retrieve url sitemap
        pd_sitemap = sm.parseSitemap(obj.sitemap, ["loc",])
        if len(pd_sitemap)<=0:
            setErrorStatus(obj, "WRONG_SITEMAP")

        # get domain from sitemap url
        domain = urlparse(obj.sitemap).netloc

        # retrieve ahrefs info
        ah = ahrefs.getAhrefsInfo(obj.user.ahrefs_token, domain)
        if len(ah)<0:
            setErrorStatus(obj, "WRONG_AHREFS")
            return False

        # get stats for the expected google view id
        try:
            credentials = google_utils.getOfflineCredentials(obj.user.google_api_token, obj.user.google_refresh_token)
            if credentials:
                google_export = google_utils.getStatsFromView(credentials, obj.project, obj.dateFrom, obj.dateTo)
        except Exception as e:
            setErrorStatus(obj, "WRONG_ANALYTICS")
            return False
        if len(google_export)<0:
            setErrorStatus(obj, "WRONG_ANALYTICS")

        # from original sitemap, remove xml, pdf and doc files
        pd_filtered_sm = pd_sitemap.loc[~pd_sitemap['loc'].str.endswith(SUFFIXES)]
        pd_filtered_sm["pageViews"] = 0
        pd_filtered_sm["organicSessions"] = 0
        pd_filtered_sm["backlinks"] = 0

        # iterate over all rows in sitemap and try to find the matching index in google one
        for index, row in pd_filtered_sm.iterrows():
            path = urlparse(row["loc"]).path
            
            # in the google dataframe, search for this path and 'All users' row
            google_row = google_export.loc[(google_export['pagePath'] == path) & (google_export['segment']=='All Users')]
            if len(google_row)>0:
                pd_filtered_sm.at[index, "pageViews"] = google_row.iloc[0]['pageViews']

            # now do the same for organic traffic
            google_row = google_export.loc[(google_export['pagePath'] == path) & (google_export['segment']=='Organic Traffic')]
            if len(google_row)>0:
                pd_filtered_sm.at[index, "organicSessions"] = google_row.iloc[0]['pageViews']

            # now search for the url in ahrefs and retrieve the dofollow number
            ahrefs_row = ah.loc[ah['url'] == row["loc"]]
            if len(ahrefs_row)>0:
                pd_filtered_sm.at[index, "backlinks"] = ahrefs_row.iloc[0]['dofollow']

        print(pd_filtered_sm)

    else:
        print("Report not pending")
        return False

    return True