from django.forms import ModelForm, DateInput, CharField, Select, ChoiceField
from django.utils.translation import ugettext_lazy as _
from sodp.reports.models import report

from bootstrap_datepicker_plus import DatePickerInput

from sodp.utils import google_utils

class ReportCreateForm(ModelForm):
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super(ReportCreateForm, self).__init__(*args, **kwargs)
        if request:
            self.fields['project'] =  CharField(required=True, widget=Select(choices = self.getProjects(request)))

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

    class Meta(object):
        model = report
        fields = ('project', 'sitemap', 'thresholds', 'dateFrom' ,'dateTo')
        widgets = { 'dateFrom' : DatePickerInput(format='%m-%d-%Y') ,
                    'dateTo' : DatePickerInput(format='%m-%d-%Y'), 'project': Select}