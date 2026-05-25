from django import forms

from families.models import Role, User


class AwardForm(forms.Form):
    kid = forms.ModelChoiceField(
        queryset=User.objects.filter(role=Role.KID, is_active=True),
        empty_label="Choose a kid...",
    )
    amount = forms.IntegerField(min_value=1, max_value=1000)
    reason = forms.CharField(max_length=200)
