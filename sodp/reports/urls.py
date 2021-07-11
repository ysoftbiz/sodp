from django.urls import path
from sodp.reports.views import ReportFormView



from sodp.reports.views import (
    report_list_view,
    report_list_view,
)

app_name = "reports"

urlpatterns = [
    path("", view=report_list_view, name="reportslist"),
]


#urlpatterns = [
#    path( "", view=report_list_view, name = 'creatingNewReportmo') 
#]