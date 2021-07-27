from django.core.files.storage import default_storage
from django.shortcuts import render
from django.views import generic, View
from sodp.reports.models import report
from sodp.tresholds.models import treshold

from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from sodp.reports.forms import ReportCreateForm
from django.urls import reverse
from django.core import serializers

from sodp.utils import google_utils, pandas_utils
from sodp.reports import tasks

#Detail view
from django.shortcuts import get_object_or_404
from django.views.generic.detail import DetailView

import pandas as pd
from django.core.exceptions import ValidationError

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
    success_url = '/reportcreatedsucessfully'

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
      
    def form_valid(self, form):
        self.object = form.save(commit=False)
        if self.object.dateFrom < date.today():
            raise ValidationError(_("The start date has to be lower than today"))  

        if self.object.dateTo < date.today():
            raise ValidationError(_("The end date has to be lower than today"))
        else: 
            if self.object.dateTo < self.object.dateFrom:
                raise ValidationError(_("The end date has to be greater than or equal to the start date"))

        self.object.user = self.request.user
        super(ReportCreateView, self).form_valid(form)
        self.object.save()

        # trigger generation task
        tasks.processReport.apply_async(args=[self.object.pk])

        return HttpResponseRedirect(self.get_success_url())

      
class ReportDetailView(generic.DetailView):
    model = report
    template_name = 'reports/detailview.html'

    def report_detail_view(request, primary_key):
        try:
            report = report.objects.get(pk=primary_key)
        except report.DoesNotExist:
            raise Http404('Book does not exist')

        return render(request, 'detailview.html', context={'report': report})

class ReportFrameView(generic.DetailView):
    model = report
    template_name = 'reports/frameview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['id'] = self.kwargs['pk']

        obj = report.objects.get(pk=context['id'], user=self.request.user)
        if obj.path:
            # open from aws storage
            report_path = "reports/{user_id}/{report_name}".format(user_id=self.request.user.pk, report_name=obj.path)
            if (default_storage.exists(report_path)):
                # read object
                context['report_url'] = default_storage.url(report_path)

        return context

class AjaxView(View):
    def get(self, request, **kwargs):
        pk = kwargs['pk']
        
        data = []
        try:
            obj = report.objects.get(pk=kwargs['pk'], user=self.request.user)
            if obj.path:
                # open from aws storage
                report_path = "reports/{user_id}/{report_name}".format(user_id=self.request.user.pk, report_name=obj.path)
                if (default_storage.exists(report_path)):
                    # read object
                    with default_storage.open(report_path) as handle:
                        df = pd.read_excel(handle, sheet_name=0) 
                        if not df.empty:
                            data = pandas_utils.convert_excel_to_json(df)
                            return JsonResponse({"data": data}, status=200, safe=False)                                    
        except Exception as e:
            pass

        return JsonResponse(data, status=500, safe=False)        