from django.shortcuts import render
from django.views import generic
from sodp.reports.models import report
from sodp.tresholds.models import treshold

from django.shortcuts import redirect
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from sodp.reports.forms import ReportCreateForm
from django.urls import reverse
from django.core import serializers

from sodp.utils import google_utils
from sodp.reports import tasks

#Detail view
from django.shortcuts import get_object_or_404
from django.views.generic.detail import DetailView

class ReportListView(generic.ListView):
    model = report
    context_object_name = 'reportsList'
    template_name = 'reports/reportslist.html'

    def get_queryset(self):
        return report.objects.filter(user=self.request.user)
    
report_list_view = ReportListView.as_view()

class ReportCreateView(CreateView):
    template_name = 'reports/reportscreate.html'
    form_class = ReportCreateForm
    success_url = '/reportcreatedsucessfully/'

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(ReportCreateView, self).get_form_kwargs(**kwargs)
        form_kwargs["request"] = self.request
        return form_kwargs

    def get_initial(self):
        super(ReportCreateView, self).get_initial()

        auxDateTo = date.today() - timedelta(1)
        n = 1
        auxDateFrom = auxDateTo - relativedelta(months=n)
        tresholds_list = serializers.serialize("json", treshold.objects.all())

        first_list = treshold.objects.all()
        tresholds_list = {}
        
        for item in first_list:
            tresholds_list.setdefault(item.title, item.default_value)

        self.initial = {"dateFrom":auxDateFrom, "dateTo":auxDateTo, "thresholds" : tresholds_list}
        return self.initial

    #def clean_dateFrom(self):
    #    if self.dateFrom < self.creationDate:
    #        raise ValidationError("The start date has to be greater than or equal to the current date")

    #def clean_dateTo(self):
    #    if self.dateTo < self.creationDate:
    #        raise ValidationError("The end date has to be greater than or equal to the current date")
    #    else: 
    #        if self.dateTo < self.clean_dateFrom:
    #            raise ValidationError( "The end date has to be greater than or equal to the start date")

    def post(self, request, *args, **kwargs):
        form = ReportCreateForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            report.save()

            # trigger generation task
            tasks.processReport(report.pk)
            
        return super(ReportCreateView,self).form_valid(form)

class ReportDetailView(generic.DetailView):
    model = report
    template_name = 'reports/detailview.html'


    def report_detail_view(request, primary_key):
        try:
            report = report.objects.get(pk=primary_key)
        except report.DoesNotExist:
            raise Http404('Book does not exist')

        return render(request, 'detailview.html', context={'report': report})



