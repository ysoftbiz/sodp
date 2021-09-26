import io
import json
import logging
import os
import pandas as pd

from celery import shared_task
from celery.contrib import rdb
from pprint import pprint

from sodp.reports.models import report
from sodp.views.models import view as viewmodel
from sodp.utils import google_utils, ahrefs
from sodp.utils import sitemap as sm
from sodp.utils import dataforseo
from sodp.utils import nlp

from datetime import datetime, date
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

CHUNK_SIZE=700 #max we can handle per batch

def setErrorStatus(report, error_code):
    report.status = "error"
    report.processingEndDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report.errorDescription = error_code
    report.save(update_fields=["status", "processingEndDate", "errorDescription"])

def setStatusComplete(report, dashboard):
    report.status = 'complete'
    report.dashboard = dashboard
    report.processingEndDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report.save(update_fields=["status", "processingEndDate", "dashboard"])

# sends an email to the user with the report URL
def sendReportCompletedEmail(report, url):
    message = get_template("emails/reportCompleted.html").render({
        'url': url
    })
    try:
        mail = EmailMessage(
            _("SODP - Report completed"),
            message,
            settings.EMAIL_FROM,
            to=[report.user.email]
        )
        mail.content_subtype = "html"
        mail.send()
    except Exception as e:
        logging.exception("error sending email: %s" % str(e))


# calculate recomendation based on row data and tresholds
def calculateRecomendation(pageViews, organicViews, backlinks, thresholds, periodNumber):

    # get threshold depending on period
    threshold_backlinks = int(thresholds["BACKLINKS"])
    threshold_volume = float(thresholds["VOLUME"])/periodNumber
    threshold_traffic = float(thresholds["TRAFFIC"])/periodNumber

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
def calculateDashboard(project, report_pk, entries):
    if len(entries)>0:
        dataframe = pd.DataFrame.from_dict(entries)

        dataframe = dataframe.sort_values(by=['seoTraffic'], ascending=False)
        # retrieve top 5 urls from dataframe
        topurls = dataframe.head(5)

        data = {}
        data['urls'] = []
        for top in topurls.itertuples():
            # retrieve timeline
            timeline = google_utils.getStatsFromURL(project, report_pk, top.url)
            data['urls'].append((top.url, timeline.to_dict(orient='records')))

        # second, division by report
        s=dataframe.recomendationCode.value_counts(normalize=True,sort=False).mul(100) # mul(100) is == *100
        s.index.name,s.name='recomendationCode','percentage_' #setting the name of index and series
        grouped = s.to_frame()
        data['percentage'] = grouped.to_dict()

        # third, top urls
        data['top'] = topurls.to_dict(orient='records')
        return data
    else:
        logging.error("Calculate dashboard - no entries in report")
        data = {"urls":[], "percentage": {}, "top": {}}
        return data

@shared_task(name="sodp.reports.tasks.processReport", time_limit=7200, soft_time_limit=7200)
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
        try:
            google_big = google_utils.authenticateBigQuery()
        except Exception as e:
            logging.exception(str(e))
            setErrorStatus(obj, "WRONG_BIGQUERY")

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
            logging.exception(str(e))
            setErrorStatus(obj, "WRONG_ANALYTICS")
            return False

        # get a list of all pages sorted by views, if we do not have a sitemap
        if len(urlsSitemap)<=0:
            if credentials:
                urlsSitemap = google_utils.getAllUrls(credentials, objview.project, pk, objview.url, obj.dateFrom, obj.dateTo)
            else:
                setErrorStatus(obj, "WRONG_ANALYTICS")
                return False

        # iterate over all rows in sitemap and get google stats from it
        google_traffic = {}
        google_organic_traffic = {}
        backlinks = {}

        # create a sitemap with all urls
        urlsSitemap = [ x for x in urlsSitemap if x not in bannedUrls]
        urlsSitemap = filter(lambda x: not x.endswith(SUFFIXES), urlsSitemap)
        urlsSitemap = list(map(lambda x: urlparse(x).path , urlsSitemap))
        print("before url")

        # generate unique urls
        urlsSitemap = list(set(urlsSitemap))
        if len(urlsSitemap)<=0:
            setErrorStatus(obj, "NO_URLS")
            return False

        # create table if it does not exist, and truncate their values
        table_id = google_utils.createTable(google_big, "stats", objview.project, pk)
        table_report_id = google_utils.createTableReport(google_big, "report", objview.project, pk)
        if not table_id or not table_report_id:
            setErrorStatus(obj, "NO_BIGQUERY_TABLES")
            return False

        # divide the dataframe in chunks, to fit the google max size
        final = [urlsSitemap[i * CHUNK_SIZE:(i + 1) * CHUNK_SIZE] for i in range((len(urlsSitemap) + CHUNK_SIZE - 1) // CHUNK_SIZE )]
        organic_urls = []
        pd_entries = []
        keywords_for_volume = []
        print("before batch")

        for batch in final:
            # get stats for the expected google view id
            if credentials:
                # get keywords
                print("before get keywords")
                google_keywords, all_keywords = dataforseo.getKeywords(objview.url, batch)

                # get volume for keywords
                print("before get volume")
                dataforseo_volume_keywords = dataforseo.getVolume(all_keywords)

                # now extract volume for each url
                volume_keywords = {}
                for url, keywords in google_keywords.items():
                    volume_keywords[url] = 0
                    # get top kw and get volume
                    if len(keywords)>0:
                        volume = dataforseo_volume_keywords.get(keywords[0], 0)
                        volume_keywords[url] = volume

                # get all ahrefs queries
                print("before ahrefs")
                loop = asyncio.get_event_loop()
                ahrefs_infos, ahrefs_pages = loop.run_until_complete(ahrefs.getAhrefsUrls(settings.AHREFS_TOKEN, objview.url, batch))

                print("before stats")
                entries = google_utils.getStatsFromView(credentials, objview.project, objview.url, batch, obj.dateFrom, obj.dateTo, period)

                # iterate over all urls and generate data
                for url, itementries in entries.items():
                    print("in url")

                    seoTraffic , nonSeoTraffic = 0, 0
                    seoTrafficNum , nonSeoTrafficNum = 0, 0

                    # insert table data
                    if len(itementries)>0:
                        result = google_utils.insertBigTable(google_big, table_id, itementries)
                        #if not result:
                        #    setErrorStatus(obj, "ERROR_INSERT_BIGTABLE")
                        #    return False

                        # iterate over all entries
                        firstPageViews, firstOrganicViews, lastPageViews, lastOrganicViews = 0, 0, 0, 0
                        firstOrganic, firstNormal = True, True
                        for entry in itementries:
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
                        if publishDate is not None and len(publishDate)<=0:
                            publishDate = None

                        pageinfo = ahrefs_pages.get(url, {})
                        title = pageinfo.get('title', '')
                        words = pageinfo.get('words', 0)

                        # get period number
                        if period == "ga:yearmonth":
                            periodNumber = 1
                        elif period == "ga:yearweek":
                            periodNumber = 4
                        else:
                            periodNumber = 30

                        # finally execute the calculation
                        recomendation_code = calculateRecomendation(lastPageViews, lastOrganicViews, backlinks, obj.thresholds, periodNumber)
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

                        # date difference
                        if (publishDate):
                            today = date.today()
                            diffdate = today - datetime.strptime(publishDate, "%Y-%m-%d").date()
                            days = diffdate.days
                        else:
                            days = 999999

                        # check if keywords or title belong to cluster
                        url_keywords = google_keywords.get(url, None)
                        if url_keywords:
                            clusterInKw = nlp.belongsToCluster(obj.thresholds["CLUSTERS"], url_keywords)
                            keyword_str = ",".join(url_keywords)
                        else:
                            clusterInKw = False
                            keyword_str = ""

                        if title:
                            clusterInTitle = nlp.belongsToCluster(obj.thresholds["CLUSTERS"], nlp.getKeywords(title))
                        else:
                            clusterInTitle = False

                        if volume_keywords.get(url, 0) is None:
                            volkw = 0
                        else:
                            volkw = volume_keywords.get(url, 0)
                        # volume keywords
                        pd_entry = {"url": url, "title": title, "publishDate": publishDate,
                            "isContentOutdated": (int(days) >= int(obj.thresholds["AGE"])),
                            "topKw": keyword_str, "vol": volkw,
                            "hasVolume": volkw >= int(obj.thresholds["VOLUME"]),
                            "clusterInKw": clusterInKw, "clusterInTitle": clusterInTitle, "wordCount": int(words),
                            "inDepthContent": int(words) >= int(obj.thresholds["WORD COUNT"]),
                            "seoTraffic": avgTraffic,
                            "meaningfulSeoTraffic": (float(avgTraffic) >= float(obj.thresholds["ORGANIC TRAFFIC"])/periodNumber),
                            "nonSeoTraffic": nonAvgTraffic,
                            "meaningfulNonSeoTraffic": (float(nonAvgTraffic) >= float(obj.thresholds["TRAFFIC"])/periodNumber),
                            "backLinks": backlinks,
                            "sufficientBacklinks": (int(backlinks) >= float(obj.thresholds["BACKLINKS"])),
                            "decay": round(decay, 4),
                            "recomendationCode": recomendation_code, "recomendationText": recomendation_text }
                        pd_entries.append(pd_entry)

        # insert into table
        result = google_utils.insertUrlsTable(google_big, objview.project, pk, organic_urls)
        if not result:
            setErrorStatus(obj, "ERROR_INSERT_BIGTABLE")
            return False

        result = google_utils.insertBigTable(google_big, table_report_id, pd_entries)
        if not result:
            setErrorStatus(obj, "ERROR_INSERT_BIGTABLE")
            return False

        # calculate dashboard entries
        dashboard = calculateDashboard(objview.project, pk, pd_entries)
        # update as completed with path
        setStatusComplete(obj, json.dumps(dashboard, cls=DjangoJSONEncoder))

        sendReportCompletedEmail(obj, url)
    else:
        print("Report not pending")
        return False

    return True
