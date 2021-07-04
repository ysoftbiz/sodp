from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from sodp.provider.models import provider

from django import forms

class providerAdmin(admin.ModelAdmin):
    list_display = ['name']


admin.site.register(provider, providerAdmin)
