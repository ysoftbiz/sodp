import io
import json
import os
import pandas as pd
import xlsxwriter 

from celery import shared_task
from celery.contrib import rdb
from pprint import pprint

from sodp.reports.models import report
from sodp.views.models import view as viewmodel
from sodp.utils import google_utils, ahrefs
from sodp.utils import sitemap as sm
from sodp.utils import dataforseo

from datetime import datetime
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.core.serializers.json import DjangoJSONEncoder
from django.template.loader import get_template
from django.utils.translation import gettext as _

import asyncio

SUFFIXES = ( '.xml', '.pdf', '.doc', '.docx' )

RECOMENDATION_TEXTS = {
    "100": "Manually review",
    "200": "Leave as is",
    "301": "Redirect or update",
    "404": "Delete"
}

CHUNK_SIZE=1000

def setErrorStatus(report, error_code):
    report.status = "error"
    report.errorDescription = error_code

def setStatusComplete(report, path, dashboard):
    report.path = path
    report.status = 'complete'
    report.dashboard = dashboard
    report.processingEndDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report.save(update_fields=["path", "status", "processingEndDate", "dashboard"])

# sends an email to the user with the report URL
def sendReportCompletedEmail(report, url):
    message = get_template("emails/reportCompleted.html").render({
        'url': url
    })
    mail = EmailMessage(
        _("SODP - Report completed"),
        message,
        settings.EMAIL_FROM,
        to=[report.user.email]
    )
    mail.content_subtype = "html"
    mail.send()



# calculate recomendation based on row data and tresholds
def calculateRecomendation(pageViews, organicViews, backlinks, thresholds, period):

    # get threshold depending on period
    threshold_backlinks = int(thresholds["BACKLINKS"])
    if period == "ga:yearmonth":
        threshold_volume = float(thresholds["VOLUME"])
        threshold_traffic = float(thresholds["TRAFFIC"])
    elif period == "ga:yearweek":
        threshold_volume = float(thresholds["VOLUME"])/4
        threshold_traffic = float(thresholds["TRAFFIC"])/4
    else:
        threshold_volume = float(thresholds["VOLUME"])/30
        threshold_traffic = float(thresholds["TRAFFIC"])/30

    # filter by volume and traffic
    if (int(pageViews)>=threshold_volume):
        if (int(organicViews)>=threshold_traffic):
            return "200"
        else:
            # filter by backlinks
            if (int(backlinks)>=threshold_backlinks):
                return "200"
            else:
                return "100"    # manually review
    else:
        if int(backlinks)>=threshold_backlinks:
            return "301"
        else:
            return "404"

    return "100"

# uploads file to s3 and returns url
def uploadExcelFile(report, dataframe):    
    file_directory_within_bucket = 'reports/{username}'.format(username=report.user.pk)
    dt_string = datetime.now().strftime("%Y%m%d%H%M%S")

    file_path = "report_{report_id}_{timestamp}.xls".format(report_id=report.pk, timestamp=dt_string)
    final_path = file_directory_within_bucket+"/"+file_path

    # write to excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, 'sheet_name')
    data = output.getvalue()    

    if not default_storage.exists(final_path): # avoid overwriting existing file
        default_storage.save(final_path, ContentFile(data))
        file_url = default_storage.url(final_path)
        return file_path, file_url

    return False, False            

# calculates if there is a decay in content
def calculateContentDecay(firstViews, lastViews, thresholds):
    if lastViews >= firstViews:
        return 0
    else:
        # calculate decrease
        change = (abs(lastViews - firstViews)/firstViews)*100
        if change >= float(thresholds["CONTENT DECAY"]):
            return change

    return 0

# calculate dashboard content and return in a dict
def calculateDashboard(project, report_pk, dataframe):
    # retrieve top 5 urls from dataframe
    topurls = dataframe.head(5)

    data = {}
    data['urls'] = []
    for top in topurls.itertuples():
        # retrieve timeline
        timeline = google_utils.getStatsFromURL(project, report_pk, top.loc)
        data['urls'].append((top.loc, timeline.to_dict(orient='records')))

    # second, division by report
    s=dataframe.recomendationCode.value_counts(normalize=True,sort=False).mul(100) # mul(100) is == *100
    s.index.name,s.name='recomendationCode','percentage_' #setting the name of index and series
    grouped = s.to_frame()
    data['percentage'] = grouped.to_dict()

    # third, top urls
    data['top'] = topurls.to_dict(orient='records')
    return data


@shared_task(name="sodp.reports.tasks.processReport", time_limit=3600, soft_time_limit=3600)
def processReport(pk):
    # get report data with that PK
    obj = report.objects.get(pk=pk)
    if obj:
        # check if report is pending
        if obj.status == 'pending':
            # set to processing
            obj.status='process'
            obj.save(update_fields=["status"])
        else:
            return False
        
        # authenticate to big query
        google_big = google_utils.authenticateBigQuery()

        # retrieve url sitemap
        urlsSitemap = []
        bannedUrls = []
        if (obj.allowedUrlsPath):
            urlsSitemap = sm.getUrlsFromFile(obj.user.pk, obj.allowedUrlsPath)

        if (obj.bannedUrlsPath):
            bannedUrls = sm.getUrlsFromFile(obj.user.pk, obj.bannedUrlsPath)

        # get domain from view
        objview = viewmodel.objects.get(id=obj.project)
        domain = urlparse(objview.url).netloc

        # retrieve global domain data
        seoclient = dataforseo.RestClient("login", "password")

        # calculate period
        diff_months = (obj.dateTo.year - obj.dateFrom.year) * 12 + obj.dateTo.month - obj.dateFrom.month
        if diff_months>=6:
            period = "ga:yearmonth"
        elif diff_months>=3:
            period = "ga:yearweek"
        else:
            period = "ga:date"

        # retrieve google credentials
        try:
            credentials = google_utils.getOfflineCredentials(obj.user.google_api_token, obj.user.google_refresh_token)
        except Exception as e:
            print(str(e))
            setErrorStatus(obj, "WRONG_ANALYTICS")
            return False

        # get a list of all pages sorted by views, if we do not have a sitemap
        if len(urlsSitemap)<=0:
            if credentials:
                urlsSitemap = google_utils.getAllUrls(credentials, objview.project, pk, objview.url, obj.dateFrom, obj.dateTo)

        # iterate over all rows in sitemap and get google stats from it
        google_traffic = {}
        google_organic_traffic = {}
        backlinks = {}

        organic_urls = []

        # create a sitemap with all urls
        urlsSitemap = [ x for x in urlsSitemap if x not in bannedUrls]
        urlsSitemap = filter(lambda x: not x.endswith(SUFFIXES), urlsSitemap)
        urlsSitemap = list(map(lambda x: urlparse(x).path , urlsSitemap))

        # generate unique urls
        urlsSitemap = list(set(urlsSitemap))
        pd_filtered_sm = pd.DataFrame(columns=["loc", "pageViews", "organicSessions", "backLinks", "recomendationCode", "recomendationText"])

        # create table if it does not exist, and truncate their values
        table_id = google_utils.createTable(google_big, "stats", objview.project, pk)
        table_report_id = google_utils.createTableReport(google_big, "report", objview.project, pk)

        # divide the dataframe in chunks, to fit the google max size
        final = [urlsSitemap[i * CHUNK_SIZE:(i + 1) * CHUNK_SIZE] for i in range((len(urlsSitemap) + CHUNK_SIZE - 1) // CHUNK_SIZE )] 
        organic_urls = []
        pd_entries = []

        for batch in final:
            # get stats for the expected google view id
            if credentials:
                # get all ahrefs queries
                loop = asyncio.get_event_loop()
                ahrefs_infos, ahrefs_pages = loop.run_until_complete(ahrefs.getAhrefsUrls(settings.AHREFS_TOKEN, objview.url, batch))

                # get keywords from google
                #loop1 = asyncio.get_event_loop()
                #google_keywords = loop1.run_until_complete(google_utils.getTopKeywordsBatch(credentials, objview.url, batch, obj.dateFrom, obj.dateTo))
                google_keywords = {}

                entries = google_utils.getStatsFromView(credentials, objview.project, objview.url, batch, obj.dateFrom, obj.dateTo, period)

                # iterate over all urls and generate data
                seoTraffic , nonSeoTraffic = 0, 0
                seoTrafficNum , nonSeoTrafficNum = 0, 0

                for url, entries in entries.items():
                    # insert table data
                    if len(entries)>0:
                        google_utils.insertBigTable(google_big, table_id, entries)


                    # iterate over all entries
                    firstPageViews, firstOrganicViews, lastPageViews, lastOrganicViews = 0, 0, 0, 0
                    firstOrganic, firstNormal = True, True
                    for entry in entries:
                        if entry["segment"] == "All Users":
                            if firstNormal:
                                firstNormal = False
                                firstPageViews = float(entry["pageViews"])
                            lastPageViews = float(entry["pageViews"])
                            nonSeoTraffic += float(entry["pageViews"])
                            nonSeoTrafficNum += 1
                        else:
                            if firstOrganic:
                                firstOrganic = False
                                firstOrganicViews = float(entry["pageViews"])
                            lastOrganicViews = float(entry["pageViews"])
                            seoTraffic += float(entry["pageViews"])
                            seoTrafficNum += 1

                    # calculate decay
                    decay = calculateContentDecay(float(firstOrganicViews), float(lastOrganicViews), obj.thresholds)

                    # add to urls
                    organic_urls.append({"page_path": url, "startViews": int(firstOrganicViews), "endViews": int(lastOrganicViews), "decay": round(decay, 5)})

                    info = ahrefs_infos.get(url, {})
                    backlinks = info.get('dofollow', 0)
                    publishDate = info.get('first_seen', None)
                    if publishDate:
                        publishDate = publishDate[0:10] # just date

                    pageinfo = ahrefs_pages.get(url, {})
                    title = pageinfo.get('title', '')
                    words = pageinfo.get('words', 0)

                    # finally execute the calculation
                    recomendation_code = calculateRecomendation(lastPageViews, lastOrganicViews, backlinks, obj.thresholds, period)
                    recomendation_text = RECOMENDATION_TEXTS[recomendation_code]

                    # create entry in dataframe
                    if seoTrafficNum == 0:
                        avgTraffic = 0
                    else:
                        avgTraffic = round((float(seoTraffic)/float(seoTrafficNum)), 4)

                    if nonSeoTrafficNum == 0:
                        nonAvgTraffic = 0
                    else:
                        nonAvgTraffic = round((float(nonSeoTraffic)/float(nonSeoTrafficNum)), 4)

                    top_keywords = google_keywords.get(url, [])
                    pd_entry = {"url": url, "title": title, "publishDate": publishDate, "topKw": ",".join(top_keywords),
                        "vol": 0, "clusterInKw": False, "clusterInTitle": False, "wordCount": int(words),
                        "seoTraffic": avgTraffic, "nonSeoTraffic": nonAvgTraffic,
                        "backLinks": backlinks, "decay": round(decay, 4), "prune": False, 
                        "recomendationCode": recomendation_code, "recomendationText": recomendation_text }
                    pd_entries.append(pd_entry)
                    pd_filtered_sm = pd_filtered_sm.append(pd_entry, ignore_index=True)

        # insert into table
        google_utils.insertUrlsTable(google_big, objview.project, pk, organic_urls)
        google_utils.insertBigTable(google_big, table_report_id, pd_entries)

        # calculate dashboard entries
        pd_filtered_sm = pd_filtered_sm.sort_values(by=['seoTraffic'], ascending=False)
        dashboard = calculateDashboard(objview.project, pk, pd_filtered_sm)
            
        # upload dataframe to storage
        path, url = uploadExcelFile(obj, pd_filtered_sm)
        if path and url:
            sendReportCompletedEmail(obj, url)

            # update as completed with path
            setStatusComplete(obj, path, json.dumps(dashboard, cls=DjangoJSONEncoder))
        else:
            setErrorStatus(obj, "ERROR_SAVING")
           
    else:
        print("Report not pending")
        return False

    return True