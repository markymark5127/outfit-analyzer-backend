import os
import tempfile
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
from typing import List
from base64 import b64encode

app = FastAPI()

# Allow requests from all origins (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.get("/")
def root():
    return {"message": "StyleSync backend is running 🚀"}

@app.post("/analyze")
async def analyze(images: List[UploadFile] = File(...)):
    if not images:
        return JSONResponse(status_code=400, content={"result": "No images received."})
    if len(images) > 3:
        return JSONResponse(status_code=400, content={"result": "You can upload up to 3 images only."})

    image_payloads = []
    for image in images:
        content = await image.read()
        encoded = b64encode(content).decode("utf-8")
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
        return JSONResponse(status_code=500, content={"result": f"Error: {str(e)}"})
