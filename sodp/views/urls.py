from django.urls import path

from sodp.views.views import (
    ViewsDecayView
)

app_name = "views"

urlpatterns = [
    path('decay/<int:pk>/', ViewsDecayView.as_view(), name = 'decayview'),
]

