from django.urls import path

from sodp.views.views import (
    ViewsDecayView,
    StatsView,
    ViewDetailView,
)

app_name = "views"

urlpatterns = [
    path('decay/<int:pk>/', ViewsDecayView.as_view(), name = 'decayview'),
    path('stats/<int:pk>/', StatsView.as_view(), name = 'statsview'),
    path('<int:pk>/', ViewDetailView.as_view(), name = 'detailview'),

]

