from django.contrib import admin
from sodp.faqs.models import faqs

class faqsAdmin(admin.ModelAdmin):
    list_display = ['question']
 
admin.site.register(faqs, faqsAdmin)
