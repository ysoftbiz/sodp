from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django import forms

from django.utils.translation import gettext_lazy as _

from sodp.tresholds.models import treshold as threshold_model

User = get_user_model()


class UserChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User


class UserCreationForm(admin_forms.UserCreationForm):
    class Meta(admin_forms.UserCreationForm.Meta):
        model = User

        error_messages = {
            "username": {"unique": _("This username has already been taken.")}
        }

class ThresholdsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['thresholds']

    def __init__(self, *args, **kwargs):
        super(ThresholdsForm, self).__init__(*args, **kwargs)
        self.fields = {}
        self.initial = {}

        # read all the entries for thresholds
        thresholds = threshold_model.objects.all().order_by('pk')
        for obj in thresholds:
            newfield = forms.CharField(max_length=255, label=obj.question, required=True)
            newfield.widget.attrs={'id': obj.title, 'name': obj.title}
            self.fields[obj.title] = newfield

        user_thresholds = self.instance.thresholds

        if user_thresholds is not None:
            initial_thresholds = user_thresholds
            for key, val in initial_thresholds.items():
                self.initial[key] = val
        else:
            for obj in thresholds:
                self.initial[obj.title] = obj.default_value
        
