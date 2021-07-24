from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from sodp.reports.models import report

from django import forms

class reportsAdmin(admin.ModelAdmin):
    list_display = ['user','creationDate']
    exclude = ("key", )

 
admin.site.register(report, reportsAdmin)
