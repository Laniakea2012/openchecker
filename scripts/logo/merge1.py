import requests
import io
from PIL import Image, ImageDraw, ImageFont
import os

API_URL = "https://api-inference.huggingface.co/models/artificialguybr/LogoRedmond-LogoLoraForSDXL-V2"
headers = {"Authorization": "Bearer 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"}

org_name = "OpenHarmony TPC"

font_path = "fonts/HowdyLemon-5yBlz.ttf"
font_size = 80
font = ImageFont.truetype(font_path, font_size)
projects = []
finished_job = []

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.content

for file in os.listdir("./imgs/dall-e/"):
    if file.endswith(".png"):
        projects.append(os.path.splitext(file)[0])
        
for file in os.listdir("./imgs/logoredmond/"):
    if file.endswith(".png"):
        finished_job.append(os.path.splitext(file)[0])        

for project_name in projects:
    if project_name in finished_job:
        continue
    inputs = f"Colorful trademark for '{project_name}'"
    image_bytes = query({
        "inputs": inputs,
    })

    # Load the image using PIL.Image
    image = Image.open(io.BytesIO(image_bytes))

    # Add text overlay
    draw = ImageDraw.Draw(image)

    text1_width, text1_height = draw.textsize(project_name, font=font)
    text1_x = image.width // 2 - text1_width // 2
    text1_y = image.height * 0.8 - text1_height // 2

    draw.text((text1_x, text1_y), project_name, font=font, fill=(3, 168, 158))

    text2_width, text2_height = draw.textsize(org_name, font=font)
    text2_x = image.width // 2 - text2_width // 2
    text2_y = image.height * 0.8 - text2_height // 2 + text1_height + 30

    draw.text((text2_x, text2_y), org_name, font=font, fill=(173, 216, 230))

    image.save(f"./imgs/logoredmond/{project_name}.png")

    print(f"{project_name} done!")
