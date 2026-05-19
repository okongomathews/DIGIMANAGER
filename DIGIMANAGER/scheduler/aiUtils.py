from transformers import pipeline, set_seed

generator = pipeline('text-generation', model='gpt2')
set_seed(42)

def tonePromptEnhancer(prompt, tone):
    prefix = {
        'formal': "Please provide a professional and well-structured caption: ",
        'humorous': "Write a funny, witty, and engaging caption: ",
        'promotional': "Generate a persuasive marketing caption: ",
        'informative': "Write a clear and informative caption: ",
    }.get(tone, "")

    return prefix + prompt

def generateCaptionAi(prompt, tone):
    enhanced_prompt = tonePromptEnhancer(prompt, tone)
    result = generator(enhanced_prompt, max_length=50, num_return_sequences=1)
    return result[0]['generated_text'].strip()