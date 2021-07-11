from django.forms import ModelForm
from sodp.reports.models import report
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column

class ReportForm(ModelForm): 
    class Meta:
        model = report
        fields = ['name','project','dateFrom','dateTo']