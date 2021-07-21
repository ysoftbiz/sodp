from django.db import models
from sodp.users.models import User
from django.db.models import CharField
from django.utils.translation import gettext_lazy as _


class report(models.Model):
    creationDate = models.DateTimeField(auto_now_add=True)
    name = CharField(_("Report name"), blank=True, max_length=100)
    project = CharField(_("project"), blank=True, max_length=255)
    dateFrom = models.DateField() 
    dateTo = models.DateField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="user", related_name="user")
 
    STATUS = (
        ('pending', _('pending')),
        ('canceled', _('canceled')),
        ('created', _('created')),
        ('failed', _('failed')),
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

    def __str__(self):
        return "%s %s %s %s %s %s" % (self.creationDate, self.name, self.project, self.dateFrom, self.dateTo, self.user)


