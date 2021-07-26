from django.urls import path

from sodp.reports.views import (
    report_list_view,
    ReportCreateView,
    ReportDetailView,
)

app_name = "reports"

urlpatterns = [
    path("reportslist/", view=report_list_view, name="reportslist"),
    path('reportscreate/', ReportCreateView.as_view(), name="reportscreate"),
    path('<int:pk>/', ReportDetailView.as_view(), name = 'detailview'),
]

