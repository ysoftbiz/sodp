from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import JsonResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView, View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from oauth2client import client
from pprint import pprint

import json, tempfile

User = get_user_model()


class UserDetailView(LoginRequiredMixin, DetailView):

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

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
        ctx['show_google_login'] = not self.request.user.google_token
        return ctx

    def get_object(self,queryset = None):
        return self.request.user
    
user_credentials_view = UserUpdateCredentialsView.as_view()

@method_decorator(csrf_exempt, name='dispatch')
class  UserGoogleCredentialsView(LoginRequiredMixin, View):
    def  post(self, request):
        try:
            authCode = request.POST.get('authCode')
            if not request.is_ajax():
                abort(403)

            # write json creds to temporary file
            with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tfile:
                json.dump(json.loads(settings.GOOGLE_CLIENT_SECRET), tfile)
                tfile.flush()

                # Exchange auth code for access token, refresh token, and ID token
                credentials = client.credentials_from_clientsecrets_and_code(
                    tfile.name,
                    ['https://www.googleapis.com/auth/analytics.readonly'],
                    authCode)

                # Retrieve refresh token and store it
                refresh_token = credentials.refresh_token
                if refresh_token:
                    # store it
                    self.request.user.google_token = refresh_token
                    self.request.user.save(update_fields=['google_token'])

                return JsonResponse(
                    {
                        'success': True,
                    }
                )
        except Exception as e:
            print(str(e))
            return JsonResponse(
                {
                    'success': False,
                }
            )

user_google_credentials_view = UserGoogleCredentialsView.as_view()
