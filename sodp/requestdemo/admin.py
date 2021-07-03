from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from sodp.requestdemo.models import requestdemo

from django import forms

class DemoRequestAdmin(admin.ModelAdmin):
    list_display = ['mail', 'date']
    ordering = ['-date']

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

admin.site.register(requestdemo, DemoRequestAdmin)
admin.site.disable_action('delete_selected')
