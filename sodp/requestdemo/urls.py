from django.urls import path
from sodp.requestdemo.views import DemoFormView

urlpatterns = [
     path( "", DemoFormView.as_view(), name = 'demo') 
]
