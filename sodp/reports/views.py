from django.shortcuts import render
from django.views import generic
from sodp.reports.models import report
from django.views.generic.edit import FormView
from .forms import ReportForm

class ReportListView(generic.ListView):
    model = report
    context_object_name = 'reportsList'
    #template_name_suffix = 'reportslist'
    template_name = 'reports/reportslist.html'
    success_url = '/reportscreate/'



report_list_view = ReportListView.as_view()


class ReportFormView(FormView):
    template_name_suffix = 'create'
    template_name = 'reports/reportscreate.html'
    #form_class = ReportForm
    success_url = '/home/'

    def form_valid(self, form):
        comment = form.save(commit=False)
        comment.save()

report_form_view = ReportFormView.as_view()





















#from django.http import HttpRequest
#from reports.models import report

#class reportsView(HttpRequest):
#    def get_queryset(self):
#        return report.objects.filter(user=self.request.User)

#class reportsCreateView(CreateView):
#    model = report
#    fields = ['name', 'project' , 'dateFrom', 'dateTo', 'user' ]
#reportreportslist


    #queryset=report.objects.filter(user=self.request.User)
    #template_name_suffix = 'reportslist'