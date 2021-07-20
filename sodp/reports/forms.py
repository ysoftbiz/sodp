from django.forms import ModelForm
from sodp.reports.models import report

class ReportCreateForm(ModelForm):
    class Meta(object):
        model = report
        fields = ('name','project', 'sitemap', 'dateFrom','dateTo')
