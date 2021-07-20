from django.forms import ModelForm
from django.forms import DateInput
from sodp.reports.models import report


class DateInput(DateInput):
    input_type = 'date'

class ReportCreateForm(ModelForm):
    class Meta(object):
        model = report
        fields = ('name','project', 'sitemap', 'thresholds', 'dateFrom' ,'dateTo')
        widgets = {'dateFrom' : DateInput() ,'dateTo' : DateInput()}