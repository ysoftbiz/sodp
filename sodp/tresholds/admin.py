from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from sodp.tresholds.models import treshold

class tresholdsAdmin(admin.ModelAdmin):
    list_display = ['title', 'default_value']

admin.site.register(treshold, tresholdsAdmin)