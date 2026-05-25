from django import forms

from .models import Role, User


class UserAdminForm(forms.ModelForm):
    """Single form for creating or editing a parent or a kid.

    Credentials work like this:
    - On create, the credential matching the role is required.
    - On edit, the credential is optional — blank means "keep current".
    """

    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Parent only. Leave blank to keep current.",
    )
    pin = forms.CharField(
        required=False,
        min_length=4,
        max_length=4,
        widget=forms.PasswordInput(render_value=False, attrs={
            "inputmode": "numeric", "pattern": "[0-9]{4}",
        }),
        help_text="Kid only. 4 digits. Leave blank to keep current.",
    )

    class Meta:
        model = User
        fields = ["name", "role", "avatar", "username"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].required = False
        self.fields["username"].help_text = "Parent login. Lowercase, no spaces."

    def clean_pin(self):
        pin = self.cleaned_data.get("pin", "")
        if pin and not pin.isdigit():
            raise forms.ValidationError("PIN must be 4 digits.")
        return pin

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        username = (cleaned.get("username") or "").strip().lower() or None
        password = cleaned.get("password") or ""
        pin = cleaned.get("pin") or ""
        is_create = self.instance.pk is None

        if role == Role.PARENT:
            if not username:
                self.add_error("username", "Parents need a username.")
            if is_create and not password:
                self.add_error("password", "Set a password for new parents.")
            cleaned["username"] = username
        elif role == Role.KID:
            if is_create and not pin:
                self.add_error("pin", "Set a 4-digit PIN for new kids.")
            cleaned["username"] = None
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password") or ""
        pin = self.cleaned_data.get("pin") or ""
        if user.role == Role.PARENT and password:
            user.set_password(password)
        elif user.role == Role.KID and pin:
            user.set_password(pin)
        if commit:
            user.save()
        return user
