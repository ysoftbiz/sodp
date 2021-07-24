from django.db import models 
from django.db.models import CharField
from django.utils.translation import gettext_lazy as _

class faqs(models.Model):
    question =  CharField(_("question"), blank=True, null=True, max_length=255)
    answer =  CharField(_("answer"), blank=True, null=True, max_length=255)

def __str__(self):
        return "%s %s" % (self.question, self.answer)