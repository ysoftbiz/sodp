from django.core.files.storage import default_storage
from django.shortcuts import render
from django.views import generic, View
from sodp.reports.models import report
from sodp.views.models import view as viewmodel
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

from datetime import date
from django.core.exceptions import ValidationError

import pandas as pd
from django.core.exceptions import ValidationError

from sodp.views.models import view


class ReportListView(generic.ListView, LoginRequiredMixin):
    model = report
    context_object_name = 'reportsList'
    template_name = 'reports/reportslist.html'

    def get_queryset(self):
        return report.objects.filter(user=self.request.user)


    
report_list_view = ReportListView.as_view()

class ReportCreateView(CreateView, LoginRequiredMixin):
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
        if form.is_valid():
            self.object.user = self.request.user
            super(ReportCreateView, self).form_valid(form)
            self.object.save()

            tasks.processReport.apply_async(args=[self.object.pk])
        return HttpResponseRedirect(self.get_success_url())

      
class ReportDetailView(generic.DetailView, LoginRequiredMixin):
    model = report
    template_name = 'reports/detailview.html'

    def get_queryset(self):
        query = super(ReportDetailView, self).get_queryset()
        return query.filter(user=self.request.user)

class ReportFrameView(generic.DetailView, LoginRequiredMixin):
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

class AjaxView(View, LoginRequiredMixin):
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

class ReportDecayView(LoginRequiredMixin, View):
    model = report
    template_name = 'reports/decayview.html'

    def get(self, request, *args, **kwargs):
        report_id = kwargs['pk']

        stats = []
        report_obj = report.objects.get(user=request.user, id=report_id)
        if report_obj:
            # retrieve view
            view_obj = viewmodel.objects.get(id=report_obj.project, user=request.user)
            if view_obj:
                # retrieve stats from google big query
                stats = google_utils.getStoredStats(report_obj.project, report_id)

        return render(request, self.template_name, {'id': report_obj.id, 'name': view_obj.name, 'dateFrom': report_obj.dateFrom, 
                        'dateTo': report_obj.dateTo, 'stats': stats})   

        return HttpResponse(status=500)

class StatsView(LoginRequiredMixin, View):
    def get(self, request, **kwargs):
        pk = kwargs['pk']
        url = request.GET.get('url', '')
        
        data = {"labels":[], "data": { "sessions": []}}
        try:
            report_obj = report.objects.get(user=request.user, id=pk)
            if report_obj:
                # extract detail for a single url
                stats = google_utils.getStatsFromURL(report_obj.project, pk, url)
                for obj in stats.iterrows():
                    data["labels"].append(obj[1].date)
                    data["data"]["sessions"].append(obj[1].pageViews)

                if len(data['labels'])>0:
                    return JsonResponse({"data": data}, status=200, safe=False)                                    
        except Exception as e:
            pass

        return JsonResponse(data, status=500, safe=False)        
