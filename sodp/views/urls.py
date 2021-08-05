from django.urls import path

from sodp.views.views import (
    ViewDetailView,
)

app_name = "views"

urlpatterns = [
    path('<int:pk>/', ViewDetailView.as_view(), name = 'detailview'),

]

