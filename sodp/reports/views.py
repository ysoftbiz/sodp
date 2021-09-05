from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Column, Row

from django.core.files.storage import default_storage
from django.shortcuts import render
from django.views import generic, View
from sodp.reports.models import report
from sodp.views.models import view as viewmodel
from sodp.tresholds.models import treshold

from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.core.files.base import ContentFile
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from sodp.reports.forms import ReportCreateForm
from django.urls import reverse
from django.core import serializers

from sodp.utils import google_utils, pandas_utils
from sodp.reports import tasks

from datetime import date
from django.core.exceptions import ValidationError

import json
import pandas as pd
from django.core.exceptions import ValidationError

from sodp.views.models import view

RECOMENDATIONS = {"100": _("Manually review"), "200": _("Leave as is"), "301": _("Redirect or update"), "404": _("Delete")}

class ReportListView(generic.ListView, LoginRequiredMixin):
    model = report
    context_object_name = 'reportsList'
    template_name = 'reports/reportslist.html'

    def get_queryset(self):
        return report.objects.filter(user=self.request.user).order_by('-creationDate')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['no_credentials'] = True
        try:
            if self.request.user.google_api_token and self.request.user.google_refresh_token:
                credentials = google_utils.getOfflineCredentials(self.request.user.google_api_token, self.request.user.google_refresh_token)
                if credentials:
                    # try to use them
                    projects = google_utils.getProjectsFromCredentials(credentials)
                    if projects:
                        context['no_credentials'] = False
        except Exception as e:
            pass

        return context
    
report_list_view = ReportListView.as_view()

class ReportCreateView(CreateView, LoginRequiredMixin):
    template_name = 'reports/reportscreate.html'
    form_class = ReportCreateForm
    success_url = '/reportcreatedsucessfully'

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(ReportCreateView, self).get_form_kwargs(**kwargs)
        form_kwargs["request"] = self.request
        return form_kwargs

    def get_form(self, form_class=None):
       form = super().get_form(form_class)
       form.helper = FormHelper()
       form.helper.layout = Layout(
            Row(Column('project')),
            Row(Column('dateFrom', css_class='form-group col-md-6 mb-0'), Column('dateTo', css_class='form-group col-md-6 mb-0')),
            Row(Column('allowedCsv', css_class='form-group col-md-6 mb-0'), Column('bannedCsv', css_class='form-group col-md-6 mb-0'))
        )

       return form        

    def get_initial(self):
        super(ReportCreateView, self).get_initial()

        auxDateTo = date.today() - timedelta(1)
        n = 1
        auxDateFrom = auxDateTo - relativedelta(months=n)

        self.initial = {"dateFrom":auxDateFrom, "dateTo":auxDateTo}
        return self.initial


class ReportCreateViewAjax(CreateView, LoginRequiredMixin):
    model = report
    form_class = ReportCreateForm
    success_url = '/reportcreatedsucessfully'
    template_name = 'reports/reportscreate.html'

    # upload the csv file to AWS
    def uploadCsvFile(self, report, file, name):    
        file_directory_within_bucket = 'reports/{username}'.format(username=report.user.pk)
        dt_string = datetime.now().strftime("%Y%m%d%H%M%S")
        file_path = "{name}_{report_id}_{timestamp}.csv".format(name=name, report_id=report.pk, timestamp=dt_string)
        final_path = file_directory_within_bucket+"/"+file_path

        if not default_storage.exists(final_path): # avoid overwriting existing file
            default_storage.save(final_path, ContentFile(file.read()))
            return file_path

        return False           

    def form_invalid(self, form):
        response = super().form_invalid(form)
        return JsonResponse(form.errors, status=400)

    def form_valid(self, form):
        self.object = form.save(commit=False)   
        if form.is_valid():
            self.object.user = self.request.user

            # get thresholds
            if self.request.user.thresholds is not None:
                self.object.thresholds = self.request.user.thresholds
            else:
                # get from default
                objs = {}
                for obj in treshold.objects.all():
                    objs[obj.title] = obj.default_value
                self.object.thresholds = objs

            super(ReportCreateViewAjax, self).form_valid(form)
            self.object.save()

            # if there are files, process them
            if "allowedCsv" in self.request.FILES:
                allowedCsvPath = self.uploadCsvFile(self.object, self.request.FILES["allowedCsv"], "allowedCsv")
                self.object.allowedUrlsPath = allowedCsvPath
            if "bannedCsv" in self.request.FILES:
                bannedCsvPath = self.uploadCsvFile(self.object, self.request.FILES["bannedCsv"], "bannedCsv")
                self.object.bannedUrlsPath = bannedCsvPath

            self.object.save()

            tasks.processReport.apply_async(args=[self.object.pk], countdown=30)
            return JsonResponse({}, status=200)


class ReportDetailView(generic.DetailView, LoginRequiredMixin):
    model = report
    template_name = 'reports/detailview.html'

    def get_queryset(self):
        query = super(ReportDetailView, self).get_queryset()
        return query.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['id'] = self.kwargs['pk']

        obj = report.objects.get(pk=context['id'], user=self.request.user)
        if obj.thresholds:
            context['thresholds'] = obj.thresholds
            context['threshold_decay'] = obj.thresholds['CONTENT DECAY']
        else:
            context['thresholds'] = {}
            context['threshold_decay'] = 0

        # now retrieve data from bigquery
        context["stats"] = []
        if obj.project:
            # retrieve view
            view_obj = viewmodel.objects.get(id=obj.project, user=self.request.user)
            if view_obj and obj.status == "complete":
                # retrieve stats from google big query
                stats = google_utils.getReportStats(view_obj.project, obj.pk)
                context["stats"] = stats

        return context
        

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
                stats = google_utils.getStoredStats(view_obj.project, report_id)

        return render(request, self.template_name, {'id': report_obj.id, 'name': view_obj.name, 'dateFrom': report_obj.dateFrom, 
                        'dateTo': report_obj.dateTo, 'stats': stats})   

        return HttpResponse(status=500)

class StatsView(LoginRequiredMixin, View):
    def get(self, request, **kwargs):
        pk = kwargs['pk']
        url = request.GET.get('url', '')
        
        data = {"labels":[], "data": { "sessions": []}}
        try:
            # retrieve view
            report_obj = report.objects.get(id=pk)
            view_obj = viewmodel.objects.get(user=request.user, id=report_obj.project)
            if view_obj:
                # extract detail for a single url
                stats = google_utils.getStatsFromURL(view_obj.project, pk, url)
                for obj in stats.iterrows():
                    data["labels"].append(obj[1].date)
                    data["data"]["sessions"].append(obj[1].pageViews)

                if len(data['labels'])>0:
                    return JsonResponse({"data": data}, status=200, safe=False)                                    
        except Exception as e:
            print(str(e))
            pass

        return JsonResponse(data, status=500, safe=False)        

class DashboardAjaxView(LoginRequiredMixin, View):
    def get(self, request, **kwargs):
        pk = kwargs['pk']
        
        # first retrieve data for linechart
        data = {"labels":[], "datasets": []}
        report_obj = report.objects.get(id=pk, user=request.user)
        i = 0
        stats = json.loads(report_obj.dashboard)
        for stat in stats['urls']:
            # extract detail for a single url
            url = stat[0]
            dates = stat[1]
            dataset = {
                "label": url,
                "data": [],
                "fill": False,
                "yAxisId": "y%d" % i
            }

            for obj in dates:
                if i == 0:
                    # fill labels just once
                    data["labels"].append(obj['date'])

                # fill dataset
                dataset["data"].append(obj['pageViews'])

            # append dataset
            data['datasets'].append(dataset)
            i+=1

        # retrieve data for piechart
        piedata = {"labels":[], "datasets": [{"label": _("Distribution per recomendation"), "data": []}]}
        for key, value in stats["percentage"]["percentage_"].items():            
            piedata["labels"].append(RECOMENDATIONS.get(key, ""))
            piedata["datasets"][0]["data"].append(round(value, 2))

        # retrieve the url
        urldata = []
        for item in stats['top']:
            urldata.append((item['url'], item['seoTraffic'], item['backLinks'], RECOMENDATIONS.get(item['recomendationCode'], '')))

        return JsonResponse({"linedata": data, "piedata": piedata, "urldata": urldata}, status=200, safe=False)