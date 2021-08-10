from django.forms import ModelForm, DateInput, CharField, Select, ChoiceField
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
from django.core.validators import URLValidator
from urllib.parse import urlparse
from sodp.views.models import view

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

        input_url = urlparse(cleaned_data.get("sitemap"))
        project_selected = view.objects.get(id = cleaned_data.get("project"))
        project_url = urlparse(project_selected.url)

        #Url validations
        validate = URLValidator()
        try:
            validate(cleaned_data.get("sitemap"))
        except:
            self.add_error('sitemap', _("Please enter a valid url"))
 
        if (input_url.netloc != project_url.netloc or input_url.scheme != project_url.scheme):
            self.add_error('sitemap', _("The url entered does not correspond to the selected project"))

        if (date_from >= date.today()):
            self.add_error('dateFrom', _("The start date has to be lower than today"))

        if date_to >= date.today():
            self.add_error('dateTo', _("The end date has to be lower than today"))

        if date_to < date_from :
            self.add_error('dateTo',_("The end date has to be greater than or equal to the start date")) 

        time_difference = relativedelta(date_to, date_from)
        difference_in_years = time_difference.years
        if difference_in_years > 1:
            self.add_error('dateTo',_("The report does can't last more than one year")) 


            
    class Meta(object):
        model = report
        fields = ('project', 'sitemap', 'thresholds', 'dateFrom' ,'dateTo')
        widgets = { 'dateFrom' : DatePickerInput(format='%Y-%m-%d') ,
                    'dateTo' : DatePickerInput(format='%Y-%m-%d'), 'project': Select}