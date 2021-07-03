from django.db import models

class requestdemo(models.Model):
    mail = models.CharField(max_length=100)
    date = models.DateTimeField(auto_now_add=True)