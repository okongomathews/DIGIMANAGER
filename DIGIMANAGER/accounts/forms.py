from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['phone_number', 'department', 'bio', 'avatar']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254 7XX XXX XXX'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Marketing'}),
            'bio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'A short line about you'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('save', 'Save changes', css_class='btn btn-primary'))
