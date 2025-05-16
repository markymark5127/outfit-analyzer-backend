import os
import tempfile
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from typing import List
from base64 import b64encode

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.post("/analyze")
async def analyze(request: Request):
    form = await request.form()
    image_payloads = []

    for key in form:
        file = form[key]
        if isinstance(file, UploadFile):
            content = await file.read()
            encoded = b64encode(content).decode("utf-8")
            image_payloads.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded}"
                }
            })

    if len(image_payloads) == 0:
        return {"result": "No images received."}, 400
    elif len(image_payloads) > 3:
        return {"result": "You can upload up to 3 images only."}, 400

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Do these clothes match? Be brief and concise."}
                    ] + image_payloads
                }
            ],
            max_tokens=150
        )
        return {"result": response.choices[0].message.content}
    except Exception as e:
        return {"result": f"Error: {str(e)}"}, 500