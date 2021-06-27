from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column

class DemoForm(forms.Form):
    email = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'E-mail address'}))

def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('Email', css_class='form-group col-md-6 mb-0'),
            )
        )
