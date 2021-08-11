from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max
from django.shortcuts import render

from django.http import JsonResponse
from django.views.generic import View

from sodp.views.models import view as viewmodel
from sodp.reports.models import report
from django.views import generic

class ViewDetailView(generic.DetailView):
    model = viewmodel
    template_name = 'views/viewdetailview.html'

    def get_context_data(self, **kwargs):
        ctx = super(ViewDetailView, self).get_context_data(**kwargs)

        # retrieve all reports from view
        ctx['reports'] = report.objects.filter(project=kwargs['object'].pk).order_by('-creationDate')
        return ctx

    def get_queryset(self):
        query = super(ViewDetailView, self).get_queryset()
        return query.filter(user=self.request.user)