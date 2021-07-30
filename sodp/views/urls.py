from django.urls import path

from sodp.views.views import (
    ViewsDecayView,
    StatsView
)

app_name = "views"

urlpatterns = [
    path('decay/<int:pk>/', ViewsDecayView.as_view(), name = 'decayview'),
    path('stats/<int:pk>/', StatsView.as_view(), name = 'statsview'),
]

