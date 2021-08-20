from django.forms import ModelForm, DateInput, CharField, Select, ChoiceField, FileField
from django.utils.translation import ugettext_lazy as _
from sodp.reports.models import report
from sodp.views.models import view

from bootstrap_datepicker_plus import DatePickerInput
from pprint import pprint

from sodp.utils import google_utils
from datetime import date
from datetime import datetime
from dateutil.relativedelta import relativedelta

#url validation
from django.conf import settings
from urllib.parse import urlparse
from sodp.views.models import view

class ReportCreateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super(ReportCreateForm, self).__init__(*args, **kwargs)
        self.fields['allowedCsv'] = FileField(label=_("CSV with allowed URLS"), required=False)
        self.fields['bannedCsv'] = FileField(label=_("CSV with banned URLS"), required=False)
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

        allowed_csv = cleaned_data.get("allowedCsv")
        if allowed_csv is not None and len(allowed_csv.name)>0 and not allowed_csv.name.endswith(".csv"):
            self.add_error("allowedCsv", _("The uploaded file needs to be in CSV format"))

        if allowed_csv is not None and allowed_csv.size > settings.MAX_UPLOAD_SIZE:
            self.add_error("allowedCsv", _("The uploaded file cannot be larger than 5mb"))

        banned_csv = cleaned_data.get("bannedCsv")
        if banned_csv is not None and len(banned_csv.name)>0 and not banned_csv.name.endswith(".csv"):
            self.add_error("bannedCsv", _("The uploaded file needs to be in CSV format"))
        if banned_csv is not None and banned_csv.size > settings.MAX_UPLOAD_SIZE:
            self.add_error("bannedCsv", _("The uploaded file cannot be larger than 5mb"))

        project_selected = view.objects.get(id = cleaned_data.get("project"))
        project_url = urlparse(project_selected.url)

        if (date_from >= date.today()):
            self.add_error('dateFrom', _("The start date has to be lower than today"))

        if date_to >= date.today():
            self.add_error('dateTo', _("The end date has to be lower than today"))

        if date_to < date_from :
            self.add_error('dateTo',_("The end date has to be greater than or equal to the start date")) 

        time_difference = relativedelta(date_to, date_from)
        difference_in_years = time_difference.years
        if difference_in_years > 1:
            self.add_error('dateTo',_("The report can't last more than one year")) 

        print("after clean")
        return cleaned_data

            
    class Meta(object):
        model = report
        fields = ('project', 'thresholds', 'dateFrom' ,'dateTo')
        widgets = { 'dateFrom' : DatePickerInput(format='%Y-%m-%d') ,
                    'dateTo' : DatePickerInput(format='%Y-%m-%d'), 'project': Select}
        labels = {
            'dateFrom': _("Report start date"),
            'dateTo': _("Report end date")
        }
        