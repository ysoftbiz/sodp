from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView, View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from oauth2client import client
from pprint import pprint

import json, tempfile, pprint
from sodp.utils import google_utils
from sodp.reports.models import report as reportmodel
from sodp.views.models import view as viewmodel
from sodp.users.forms import ThresholdsForm


User = get_user_model()

def getDashboardData(user):
    data = {}

    # retrieve latest 5 reports for that user
    reports = reportmodel.objects.filter(user=user).filter(status="complete").order_by('-creationDate')[:5]
    data["reports"] = reports

    return data

class UserDetailView(LoginRequiredMixin, DetailView):

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_context_data(self, **kwargs):
        ctx = super(UserDetailView, self).get_context_data(**kwargs)
        reportData = getDashboardData(self.request.user)

        return  {**ctx, **reportData}

    def get_object(self,queryset = None):
        return self.request.user

user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self):
        return self.request.user.get_absolute_url()  # type: ignore [union-attr]

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()


class UserUpdateCredentialsView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["ahrefs_token"]
    template_name_suffix = 'credentials'
    success_message = _("Credentials successfully updated")

    def get_context_data(self, **kwargs):
        ctx = super(UserUpdateCredentialsView, self).get_context_data(**kwargs)
        ctx['show_google_login'] = True

        if self.request.user.google_api_token and self.request.user.google_refresh_token:
            credentials = google_utils.getOfflineCredentials(self.request.user.google_api_token, self.request.user.google_refresh_token)
            if credentials:
                # try to use them
                projects = google_utils.getProjectsFromCredentials(credentials)
                if projects:
                    ctx['show_google_login'] = False

        if ctx['show_google_login']:
            ctx['google_auth_url'] = google_utils.generateGoogleURL(self.request)
        else:
            ctx['google_auth_url'] = "" 
        return ctx

    def get_object(self,queryset = None):
        return self.request.user
user_credentials_view = UserUpdateCredentialsView.as_view()

class  UserGoogleCredentialsView(LoginRequiredMixin, View):

    def  get(self, request):
        try:
            credentials = google_utils.getUserCredentials(request)
        except Exception as e:
            print(str(e))
            return HttpResponse(status=500)

        if credentials:
            # store credentials
            auth_token = credentials.token
            refresh_token = credentials.refresh_token
            if auth_token and refresh_token: 
                # store it
                self.request.user.google_api_token = auth_token
                self.request.user.google_refresh_token = refresh_token
                self.request.user.save(update_fields=['google_api_token', 'google_refresh_token'])

                # and generate views
                projects = google_utils.getProjectsFromCredentials(credentials)
                if projects:
                    # fill views
                    google_utils.fillViews(projects, self.request.user)

                return redirect(request.build_absolute_uri('/')+"users/~/")                    

        return HttpResponse(status=500) 

user_google_credentials_view = UserGoogleCredentialsView.as_view()

class  UserGoogleLogoutView(LoginRequiredMixin, View):
    def  get(self, request):
        # just remove google credentials
        request.user.disableGoogleCredential()
        return JsonResponse({}, status=200)        


user_google_logout_view = UserGoogleLogoutView.as_view()

class UserThresholdsView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ThresholdsForm
    template_name_suffix = 'thresholds'
    success_message = _("Thresholds successfully updated")

    def get_object(self,queryset = None):
        return self.request.user

    def form_valid(self, form):
        form.instance.thresholds = form.cleaned_data
        form.instance.save(update_fields=['thresholds'])
        return redirect(self.request.build_absolute_uri('/')+"users/"+self.request.user.username)                    

user_thresholds_view = UserThresholdsView.as_view()
