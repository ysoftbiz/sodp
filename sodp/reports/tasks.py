import io
import os
import pandas as pd
import xlsxwriter 

from celery import shared_task
from celery.contrib import rdb
from pprint import pprint

from sodp.reports.models import report
from sodp.views.models import stats as statsmodel, view as viewmodel
from sodp.utils import google_utils, ahrefs
from sodp.utils import sitemap as sm

from datetime import datetime
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.template.loader import get_template
from django.utils.translation import gettext as _

SUFFIXES = ( '.xml', '.pdf', '.doc', '.docx' )

RECOMENDATION_TEXTS = {
    "100": "Manually review",
    "200": "Leave as is",
    "301": "Redirect or update",
    "404": "Delete"
}

MAX_PAGES = 5000

def setErrorStatus(report, error_code):
    report.status = "error"
    report.errorDescription = error_code

def setStatusComplete(report, path):
    report.path = path
    report.status = 'complete'
    report.processingEndDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report.save(update_fields=["path", "status", "processingEndDate"])

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
def calculateRecomendation(row, thresholds, period):

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
    if (int(row["pageViews"])>=threshold_volume):
        if (int(row["organicSessions"])>=threshold_traffic):
            return "200"
        else:
            # filter by backlinks
            if (int(row["backLinks"])>=threshold_backlinks):
                return "200"
            else:
                return "100"    # manually review
    else:
        if int(row["backLinks"])>=threshold_backlinks:
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
        if change >= float(thresholds["CONTENT_DECAY"]):
            return change

    return 0

@shared_task(name="sodp.reports.tasks.processReport")
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
        pd_sitemap = sm.parseSitemap(obj.sitemap)
        if pd_sitemap.empty or len(pd_sitemap.index)<=0:
            setErrorStatus(obj, "WRONG_SITEMAP")
            return False

        # get domain from sitemap url
        domain = urlparse(obj.sitemap).netloc

        # calculate period
        diff_months = (obj.dateTo.year - obj.dateFrom.year) * 12 + obj.dateTo.month - obj.dateFrom.month
        if diff_months>=6:
            period = "ga:yearmonth"
        elif diff_months>=3:
            period = "ga:yearweek"
        else:
            period = "ga:date"

        # iterate over all rows in sitemap and get google stats from it
        google_traffic = {}
        google_organic_traffic = {}

        organic_urls = []

        # from original sitemap, remove xml, pdf and doc files
        pd_filtered_sm = pd_sitemap.loc[~pd_sitemap['loc'].str.endswith(SUFFIXES)]
        pd_filtered_sm["pageViews"] = 0
        pd_filtered_sm["organicSessions"] = 0
        pd_filtered_sm["backLinks"] = 0
        pd_filtered_sm["recomendationCode"] = ""
        pd_filtered_sm["recomendationText"] = ""

        # create table if it does not exist, and truncate their values
        table_id = google_utils.createTable(google_big, "stats", obj.project, pk)
        try:
            credentials = google_utils.getOfflineCredentials(obj.user.google_api_token, obj.user.google_refresh_token)
        except Exception as e:
            print(str(e))
            setErrorStatus(obj, "WRONG_ANALYTICS")
            return False

        processedEntries = 0
        for index, row in pd_filtered_sm.iterrows():
            path = urlparse(row["loc"]).path

            # get stats for the expected google view id
            if credentials:
                firstPageViews, firstOrganicViews, lastPageViews, lastOrganicViews, totalEntries = google_utils.getStatsFromView(
                    credentials, google_big, obj.project, pk, path, obj.dateFrom, obj.dateTo, table_id, period)

                google_traffic[path] = lastPageViews
                google_organic_traffic[path] = lastOrganicViews

                # calculate decay
                decay = calculateContentDecay(float(firstOrganicViews), float(lastOrganicViews), obj.thresholds)

                # add to urls
                organic_urls.append({"page_path": path, "startViews": int(firstOrganicViews), "endViews": int(lastOrganicViews), "decay": round(decay, 5)})

                if totalEntries > 0:
                    processedEntries +=1
                if processedEntries >= MAX_PAGES:
                    break    

        # insert into table
        google_utils.insertUrlsTable(google_big, obj.project, pk, organic_urls)

        # retrieve ahrefs info
        ah = ahrefs.getAhrefsInfo(obj.user.ahrefs_token, domain)
        if len(ah)<0:
            setErrorStatus(obj, "WRONG_AHREFS")
            return False

        # iterate over all rows in sitemap and try to find the matching index in google one
        for index, row in pd_filtered_sm.iterrows():
            path = urlparse(row["loc"]).path
            
            # in the google dataframe, search for this path and 'All users' row
            pageViews = google_traffic.get(path, None)
            if pageViews is not None:
                pd_filtered_sm.at[index, "pageViews"] = pageViews

            # now do the same for organic traffic
            organicViews = google_organic_traffic.get(path, None)
            if organicViews is not None:
                pd_filtered_sm.at[index, "organicSessions"] = organicViews

            # now search for the url in ahrefs and retrieve the dofollow number
            ahrefs_row = ah.loc[ah['url'] == row["loc"]]
            if len(ahrefs_row)>0:
                pd_filtered_sm.at[index, "backLinks"] = ahrefs_row.iloc[0]['dofollow']

            # finally execute the calculation
            recomendation_code = calculateRecomendation(pd_filtered_sm.iloc[index], obj.thresholds, period)
            recomendation_text = RECOMENDATION_TEXTS[recomendation_code]

            pd_filtered_sm.at[index, "recomendationCode"] = recomendation_code
            pd_filtered_sm.at[index, "recomendationText"] = recomendation_text

        # upload dataframe to storage
        path, url = uploadExcelFile(obj, pd_filtered_sm)
        if path and url:
            sendReportCompletedEmail(obj, url)

            # update as completed with path
            setStatusComplete(obj, path)
        else:
            setErrorStatus(obj, "ERROR_SAVING")
           
    else:
        print("Report not pending")
        return False

    return True