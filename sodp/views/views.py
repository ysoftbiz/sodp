from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max
from django.shortcuts import render
from django.views.generic import View

from sodp.views.models import view as viewmodel, stats as statsmodel

# Create your views here.
class ViewsDecayView(LoginRequiredMixin, View):
    model = viewmodel
    template_name = 'views/decayview.html'

    def get(self, request, *args, **kwargs):
        view_id = kwargs['pk']

        view = viewmodel.objects.get(user=request.user, id=view_id)
        if view:
            # get max date from stat
            args = statsmodel.objects.filter(view_id=view_id)
            maxDate = args.aggregate(Max('dateTo'))

            if maxDate:
                # retrieve all stats for that period
                stats = statsmodel.objects.filter(view_id=view_id, dateTo=maxDate["dateTo__max"]).order_by('-sessions')
        else:
            traffic = []
        return render(request, self.template_name, {'name': view.name, 'date': maxDate["dateTo__max"], 'stats': stats})   

        return HttpResponse(status=500)