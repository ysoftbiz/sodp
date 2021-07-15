from django.urls import path

from sodp.reports.views import (
    report_list_view,
    ReportCreateView
)

app_name = "reports"

urlpatterns = [
    path("", view=report_list_view, name="reportslist"),
    path('createReport/', ReportCreateView.as_view(),  name='createReport'),
]

