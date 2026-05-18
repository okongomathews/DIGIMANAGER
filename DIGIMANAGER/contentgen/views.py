from django.shortcuts import render, redirect
from .forms import ContentPromptForm
from .models import ContentPrompt
from transformers import pipeline
from django.contrib.auth.decorators import login_required



captionGenerator = pipeline('text-generation', model='gpt2')

@login_required
def generateCaption(request):
    if request.method == 'POST':
        form = ContentPromptForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            # Tone hint
            tone_prefix = f"Make this {obj.tone}: "
            generated = captionGenerator(tone_prefix + obj.prompt, max_length=50, num_return_sequences=1)
            obj.generated_caption = generated[0]['generated_text']
            obj.save()
            return redirect('captionDetail', obj.id)
    else:
        form = ContentPromptForm()
    return render(request, 'contentgen/generateCaption.html', {'form': form})

@login_required
def captionDetail(request, pk):
    prompt = ContentPrompt.objects.get(pk=pk, user=request.user)
    return render(request, 'contentgen/captionDetail.html', {'prompt': prompt})
