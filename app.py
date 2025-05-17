from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
from base64 import b64encode
import openai
import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import re

app = FastAPI()

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai.api_key = os.getenv("OPENAI_API_KEY")

import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def extract_amazon_url(text: str) -> str:
    # Match an Amazon URL and exclude common trailing punctuation like ).]}
    pattern = r"https:\/\/www\.amazon\.com\/[^\s\)\]\}\.]+"
    match = re.search(pattern, text)
    return match.group(0).strip() if match else ""

def add_affiliate_tag(url: str) -> str:
    try:
        parsed = urlparse(url)
        if "amazon.com" not in parsed.netloc:
            return url  # Not an Amazon link

        query = parse_qs(parsed.query)
        query["tag"] = ["stylesyncapp-20"]
        new_query = urlencode(query, doseq=True)
        return urlunparse(parsed._replace(query=new_query))
    except Exception:
        return url

    
def remove_urls(text: str) -> str:
    # Remove entire markdown links like [Amazon Link](https://...)
    text = re.sub(r'\[.*?\]\((https?://[^\s)]+)\)', '', text)

    # Remove any remaining raw URLs
    text = re.sub(r'https?://[^\s\)\]\}]+', '', text)

    # Remove leftover punctuation like ": " or "- " at the end of the sentence
    text = re.sub(r'[:\-–—]+\s*$', '', text.strip())

    # Ensure text ends with a single period
    text = text.rstrip('.')
    return text.strip() + '.'



@app.get("/")
def root():
    return {"message": "StyleSync backend is running 🚀"}
    
@app.get("/ping")
def ping():
    return {"message": "pong"}

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
        # Step 1: Outfit analysis
        analysis_response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Do these clothes match? Give an Amazon Search link with a suggested item to add or replace(if the outfit doesnt match) ito the outfit. Give a one sentence response with an amazon link no other text."}
                    ] + image_payloads
                }
            ],
            max_tokens=300
        )

        result_text = analysis_response.choices[0].message.content.strip()
        match_status = "matched" if "match" in result_text.lower() and "don’t" not in result_text.lower() else "not matched"
        print(result_text)

        # Step 2: Extract item keyword
        keywords = ["blazer", "shoes", "jeans", "jacket", "dress", "hat", "shirt", "coat", "sneakers", "turtleneck"]
        highlighted_item = next((kw for kw in keywords if kw in result_text.lower()), "jacket")
        
        extracted_url = extract_amazon_url(result_text)

        if extracted_url.startswith("https://www.amazon.com/"):
            affiliate_url = add_affiliate_tag(extracted_url)
        else:
            affiliate_url = f"https://www.amazon.com/s?k={highlighted_item.replace(' ', '+')}&tag=stylesyncapp-20"

        return {
            "result": remove_urls(result_text),
            "matchStatus": match_status,
            "highlightedItem": highlighted_item,
            "affiliateUrl": affiliate_url
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"result": f"Error: {str(e)}"})
