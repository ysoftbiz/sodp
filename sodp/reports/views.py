from django.shortcuts import render
from django.views import generic
from sodp.reports.models import report
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from reports.forms import ReportCreateForm

class ReportListView(generic.ListView):
    model = report
    context_object_name = 'reportsList'
    template_name = 'reports/reportslist.html'

    
report_list_view = ReportListView.as_view()

class ReportCreateView(CreateView):
    template_name = 'reports/reportscreate.html'
    form_class = ReportCreateForm
    success_url = '../../reportslist'

    def get_initial(self):
        super(ReportCreateView, self).get_initial()


        auxDateTo = date.today() - timedelta(1)

        n = 1
        auxDateFrom = auxDateTo - relativedelta(months=n)

        self.initial = {"dateFrom":auxDateFrom, "dateTo":auxDateTo}
        return self.initial

    def post(self, request, *args, **kwargs):
        form = ReportCreateForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            report.save()
            
        return super(ReportCreateView,self).form_valid(form)



