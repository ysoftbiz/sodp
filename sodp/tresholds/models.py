from django.db import models

class treshold(models.Model):
    title = models.CharField(max_length=255)
    question = models.CharField(max_length=255)
    default_value = models.CharField(max_length=255)

