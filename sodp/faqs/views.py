from django.shortcuts import render
from django.views import generic
from sodp.faqs.models import faqs


class FaqsListView(generic.ListView):
    model = faqs
    context_object_name = 'faqs'
    template_name = 'faqs/faqslist.html'
    
    def get_queryset(self):
        return faqs.objects.all()
    
faqs_list_view = FaqsListView.as_view()