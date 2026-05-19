from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from .models import Post, ContentPrompt, Platform

# ------------------------------------------
# ✅ User Registration Form
# ------------------------------------------
class RegisterForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    role = forms.ChoiceField(
        choices=get_user_model().ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'role', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('register', 'Register'))


# ------------------------------------------
# ✅ Post Creation / Editing Form
# ------------------------------------------
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['platform', 'content', 'image', 'scheduled_time', 'status']
        widgets = {
            'platform': forms.Select(attrs={'class': 'form-select'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'scheduled_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Save Post'))


# ------------------------------------------
# ✅ Platform OAuth Token Management Form
# ------------------------------------------
class PlatformForm(forms.ModelForm):
    class Meta:
        model = Platform
        fields = ['name', 'access_token', 'refresh_token', 'expires_in']
        widgets = {
            'name': forms.Select(attrs={'class': 'form-select'}),
            'access_token': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'refresh_token': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'expires_in': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(PlatformForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('save', 'Save Platform'))


# ------------------------------------------
# ✅ Content Prompt Form (for AI generation)
# ------------------------------------------
class ContentPromptForm(forms.ModelForm):
    class Meta:
        model = ContentPrompt
        fields = ['prompt', 'platform', 'tone']
        widgets = {
            'prompt': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'platform': forms.Select(attrs={'class': 'form-select'}),
            'tone': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super(ContentPromptForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('generate', 'Generate Content'))
