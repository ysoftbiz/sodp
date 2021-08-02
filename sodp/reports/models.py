from django.db import models
from sodp.users.models import User
from django.db.models import CharField, IntegerField
from django.utils.translation import gettext_lazy as _
import datetime
from sodp.views.models import view

class report(models.Model):
    class Meta:
            indexes = (
                models.Index(
                    name='reports_user_index',
                    fields=('user',),
                ),
                models.Index(
                    name='reports_project_index',
                    fields=('user', 'project'),
                )
            )

    creationDate = models.DateTimeField(auto_now_add=True)
    name = CharField(_("Report name"), blank=True, max_length=100)
    project = CharField(_("project"), max_length=255)
    dateFrom = models.DateField() 
    dateTo = models.DateField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="user", related_name="user")

    STATUS = (
        ('pending', _('Pending')),
        ('process', _('Processing')),
        ('canceled', _('Canceled')),
        ('created', _('Created')),
        ('failed', _('Failed')),
        ('complete', _('Completed')) 
    )

    status = models.CharField(
        max_length=8,
        choices=STATUS,
        blank=True,
        default='pending',
        help_text='Report status',
    )

    thresholds = models.JSONField(blank=True, null = True)
    sitemap =  CharField(_("sitemap"), blank=True, null=True, max_length=255)
    processingStartDate = models.DateTimeField(null=True, blank=True)
    processingEndDate = models.DateTimeField(null=True, blank=True)
    numRetries = IntegerField(null = True)
    errorDescription = CharField(_("error description"), blank=True, null=True, max_length=255)
    path = CharField(_("path"), blank=True, null=True, max_length=255)
    key = CharField(_("key"), blank=True, null=True, max_length=255)

    def __str__(self):
        return "%s %s %s %s %s %s" % (self.creationDate, self.name, self.project, self.dateFrom, self.dateTo, self.user)

    @property
    def viewName(self):
        return view.objects.filter(pk = self.project)[0]