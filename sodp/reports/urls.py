from django.urls import path

from sodp.reports.views import (
    report_list_view,
    ReportCreateView,
    ReportDetailView,
    ReportFrameView,
    AjaxView,
)

app_name = "reports"

urlpatterns = [
    path("reportslist/", view=report_list_view, name="reportslist"),
    path('reportscreate/', ReportCreateView.as_view(), name = "reportscreate"),
    path('detail/<int:pk>/', ReportFrameView.as_view(), name = "reportsdetail"),
    path('ajax/<int:pk>/', AjaxView.as_view(), name = "reportsajax"),
   path('<int:pk>/', ReportDetailView.as_view(), name = 'detailview'),
]

