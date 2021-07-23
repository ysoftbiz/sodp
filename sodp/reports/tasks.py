from config import celery_app
from celery import shared_task
from celery.contrib import rdb
from pprint import pprint

from sodp.reports.models import report
from sodp.utils import google_utils

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

        # get credentials from use
        try:
            credentials = google_utils.getOfflineCredentials(obj.user.google_api_token, obj.user.google_refresh_token)
            if credentials:
                google_export = google_utils.getStatsFromView(credentials, obj.project, obj.dateFrom, obj.dateTo)
        except Exception as e:
            print(str(e))

    else:
        print("Report not pending")
        return False

    return True