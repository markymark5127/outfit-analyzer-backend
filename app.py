from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
from base64 import b64encode
import openai
import os
import re
from urllib.parse import quote_plus, urlparse, parse_qs, urlencode, urlunparse

app = FastAPI()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai.api_key = os.getenv("OPENAI_API_KEY")

def build_affiliate_search_url(query_text: str) -> str:
    encoded = quote_plus(query_text)
    return f"https://www.amazon.com/s?k={encoded}&tag=stylesyncapp-20"

def extract_suggested_item_text(sentence: str) -> str:
    # Extracts core item from sentence like "Try adding a light gray blazer..."
    match = re.search(r"(add(?:ing)?|replace(?:ing)?)(.*)", sentence, re.IGNORECASE)
    return match.group(2).strip() if match else sentence.strip()

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
        # GPT request with clear structure
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an outfit stylist. Respond in exactly 3 lines:\n"
                        "1. 'Match' or 'Doesn't Match'\n"
                        "2. A short sentence suggesting a clothing item to improve the outfit\n"
                        "3. A plain Amazon search URL that searches for the item suggested in line 2. Do not use markdown. Do not add any extra commentary or explanation."
                    )
                },
                {
                    "role": "user",
                    "content": image_payloads
                }
            ],
            max_tokens=300
        )

        result_text = response.choices[0].message.content.strip()
        print("[AI Response]\n" + result_text)

        lines = result_text.splitlines()
        if len(lines) < 3:
            return JSONResponse(status_code=500, content={"result": "Incomplete response from AI."})

        match_line = lines[0].strip()
        sentence_line = lines[1].strip()
        affiliate_url_raw = "\n".join(lines[2:]).strip()

        match_status = "matched" if "match" in match_line.lower() and "doesn't" not in match_line.lower() else "not matched"

        # Extract clean item suggestion and build affiliate URL
        suggested_item = extract_suggested_item_text(sentence_line)
        if affiliate_url_raw.startswith("https://www.amazon.com/"):
            affiliate_url = add_affiliate_tag(affiliate_url_raw)
        else:
            affiliate_url = build_affiliate_search_url(suggested_item)

        return {
            "result": sentence_line,
            "matchStatus": match_status,
            "highlightedItem": suggested_item,
            "affiliateUrl": affiliate_url
        }

    except Exception as e:
        print(f"[ERROR] Analysis failed: {e}")
        return JSONResponse(status_code=500, content={"result": "Internal error during analysis."})
