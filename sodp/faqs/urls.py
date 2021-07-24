from django.urls import path
from sodp.faqs.views import faqs_list_view

app_name = "faqs"

urlpatterns = [
    path("faqslist/", view=faqs_list_view, name="faqslist"),

]
