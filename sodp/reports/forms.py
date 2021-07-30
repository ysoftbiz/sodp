from django.forms import ModelForm, DateInput, CharField, Select, ChoiceField
from django.utils.translation import ugettext_lazy as _
from sodp.reports.models import report
from sodp.views.models import view

from bootstrap_datepicker_plus import DatePickerInput
from pprint import pprint

from sodp.utils import google_utils
import datetime

class ReportCreateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super(ReportCreateForm, self).__init__(*args, **kwargs)
        if request:
            choices = [(choice.pk, choice) for choice in view.objects.filter(user=request.user)]
            self.fields['project'] = CharField(required=True, widget=Select(choices=choices))

    def getProjects(self, request):
        choices = []
        choices.append(("", _("Select project")))

        credentials = google_utils.getOfflineCredentials(request.user.google_api_token, request.user.google_refresh_token)
        if not credentials:
            request.user.disableGoogleCredential()
        else:
            # get list of projects from user
            google_projects = google_utils.getProjectsFromCredentials(credentials)

            if google_projects:
                project_tuples = list(item for item in google_projects.items())
                choices = choices + list(project_tuples)

                # add projects to session
                request.session['projects'] = google_projects
        return choices

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("dateFrom")
        date_to = cleaned_data.get("dateTo")

        if date_from >= date.today():
            self.add_error('dateFrom', _("The start date has to be lower than today"))

        if date_to >= date.today():
            self.add_error('dateTo', _("The end date has to be lower than today"))

        if date_to < date_from :
            self.add_error('dateTo',_("The end date has to be greater than or equal to the start date")) 
            
    class Meta(object):
        model = report
        fields = ('project', 'sitemap', 'thresholds', 'dateFrom' ,'dateTo')
        widgets = { 'dateFrom' : DatePickerInput(format='%Y-%m-%d') ,
                    'dateTo' : DatePickerInput(format='%Y-%m-%d'), 'project': Select}