from django import forms
from .models import ContentPrompt

class ContentPromptForm(forms.ModelForm):
    class Meta:
        model = ContentPrompt
        fields = ['platform', 'prompt', 'tone']
        widgets = {
            'prompt': forms.Textarea(attrs={'rows': 4}),
        }