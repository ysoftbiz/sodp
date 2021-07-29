from django.urls import path

from sodp.users.views import (
    user_detail_view,
    user_redirect_view,
    user_update_view,
    user_credentials_view,
    user_google_credentials_view,
    user_google_logout_view
)

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("~googlecredentials/", view=user_google_credentials_view, name="google_credentials"),
    path("google_logout/", view=user_google_logout_view, name="google_logout"),
    path("~/", view=user_credentials_view, name="credentials"),
    path("<str:username>/", view=user_detail_view, name="detail"),
]
