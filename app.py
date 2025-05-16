import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
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
async def analyze(images: List[UploadFile] = File(...)):
    if len(images) == 0:
        raise HTTPException(status_code=400, detail="No images received.")
    if len(images) > 3:
        raise HTTPException(status_code=400, detail="You can upload up to 3 images only.")

    image_payloads = []
    for image in images:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        content = await image.read()
        temp_file.write(content)
        temp_file.close()

        with open(temp_file.name, "rb") as f:
            encoded = b64encode(f.read()).decode("utf-8")
            image_payloads.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded}"
                }
            })

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
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
