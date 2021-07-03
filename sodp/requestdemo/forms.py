from django.forms import ModelForm
from sodp.requestdemo.models import requestdemo
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column

class DemoForm(ModelForm): 
    class Meta:
        model = requestdemo
        fields = ['mail']

