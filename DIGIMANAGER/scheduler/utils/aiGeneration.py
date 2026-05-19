import base64
import os
import uuid
from django.conf import settings
from openai import OpenAI
from diffusers import StableDiffusionPipeline
import torch
from PIL import Image
import requests

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def save_base64_image(base64_data, filename=None):
    if not filename:
        filename = f"{uuid.uuid4().hex}.png"
    path = os.path.join(settings.MEDIA_ROOT, "ai_generated", filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(base64.b64decode(base64_data))
    return path, f"ai_generated/{filename}"  # Returns file path & relative path

def generate_dalle_image(prompt):
    response = client.images.generate(
        model="dall-e-3",  # or "dall-e-2"
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1
    )

    image_url = response.data[0].url

    # Download and save locally
    filename = f"{uuid.uuid4().hex}.png"
    path = os.path.join(settings.MEDIA_ROOT, "ai_generated", filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    img_data = requests.get(image_url).content
    with open(path, 'wb') as f:
        f.write(img_data)

    return path  # full path to saved image


def refine_image_gpt4(post, image_call_id, prompt):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            },
            {"type": "image_generation_call", "id": image_call_id},
        ],
        tools=[{"type": "image_generation"}],
    )

    for output in response.output:
        if output.type == "image_generation_call":
            return save_base64_image(output.result)


def generate_image_sd(prompt):
    model_id = "stabilityai/stable-diffusion-2-1"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        cache_dir=settings.HUGGINGFACE_CACHE_DIR
    ).to(device)
    img = pipe(prompt, num_inference_steps=50).images[0]
    filename = f"{uuid.uuid4()}.png"
    img_dir = os.path.join(settings.MEDIA_ROOT, "generated")
    os.makedirs(img_dir, exist_ok=True)
    img_path = os.path.join(img_dir, filename)
    img.save(img_path)
    return img_path