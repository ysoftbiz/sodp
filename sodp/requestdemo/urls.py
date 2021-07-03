from django.urls import path
from requestdemo.views import DemoFormView

urlpatterns = [
     path( "", DemoFormView.as_view(), name = 'demo') 
]
