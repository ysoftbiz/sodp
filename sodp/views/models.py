from django.db import models
from django.db.models import CharField
from django.utils.translation import gettext_lazy as _
from sodp.users.models import User


class view(models.Model):
    class Meta:
            indexes = (
                models.Index(
                    name='views_user_index',
                    fields=('user',),
                ),
            )

    id = CharField(_("id"), blank=True, max_length=25, primary_key=True)
    name = CharField(_("name"), blank=True, max_length=100)
    url = CharField(_("url"), blank=True, max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="viewUser", related_name="viewUser")

    def __str__(self):
        return "%s - %s" % (self.name, self.url)

class stats(models.Model):
    class Meta:
            indexes = (
                models.Index(
                    name='stats_view_index',
                    fields=('view_id',),
                ),
                models.Index(
                    name='stats_url_index',
                    fields=('view_id', 'url'),
                ),
            )

    view = models.ForeignKey(view, on_delete=models.CASCADE, verbose_name="statsReport", related_name="statsReport")
    url = CharField(_("url"), max_length=255)
    dateFrom = models.DateField() 
    dateTo = models.DateField()
    sessions =  models.IntegerField()

    def __str__(self):
        return "%s %s %s %s" % (self.view, self.url, self.dateFrom, self.dateTo)
