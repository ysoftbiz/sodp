from django.db import models
from sodp.provider.models import provider
from sodp.users.models import User

class report(models.Model):
    fechaCreacion = models.DateTimeField()
    url = models.CharField(max_length=100)
    fechaDesde = models.DateTimeField()
    fechaHasta = models.DateTimeField()
    user = models.ForeignKey(provider, on_delete=models.CASCADE, verbose_name="user", related_name="user")
    providers = models.ManyToManyField('provider.provider')