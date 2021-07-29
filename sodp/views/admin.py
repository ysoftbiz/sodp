from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from sodp.views.models import view

from django import forms

class viewsAdmin(admin.ModelAdmin):
    list_display = ['id','name']
 
admin.site.register(view, viewsAdmin)