from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
from base64 import b64encode
import openai
import os
import json

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

@app.get("/")
def root():
    return {"message": "StyleSync backend is running 🚀"}

@app.post("/analyze")
async def analyze(images: List[UploadFile] = File(...)):
    print("📸 Received analyze request")

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
        # Step 1: Ask GPT-4o to analyze the outfit
        analysis_response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Do these clothes match? If they do, say so. If they don’t, suggest one item to add or replace and why."}
                    ] + image_payloads
                }
            ],
            max_tokens=300
        )

        result_text = analysis_response.choices[0].message.content
        print("🧠 GPT Analysis:", result_text)

        match_status = "matched" if "match" in result_text.lower() and "don’t" not in result_text.lower() else "not matched"

        # Attempt to identify an item to build a product link around
        keywords = ["blazer", "shoes", "jeans", "jacket", "dress", "hat", "shirt", "coat", "sneakers", "turtleneck"]
        highlighted_item = next((kw for kw in keywords if kw in result_text.lower()), "jacket")

        # Step 2: Ask GPT-4o for an affiliate product
        product_prompt = (
            f"Give me a stylish Amazon product suggestion for a {highlighted_item}. "
            f"Respond ONLY in this exact JSON format:\n"
            "{\n"
            "  \"name\": \"Product Name\",\n"
            "  \"imageUrl\": \"Image URL\",\n"
            "  \"affiliateUrl\": \"https://www.amazon.com/your-product-url?tag=stylesyncapp-20\"\n"
            "}\n"
            "Make sure the affiliateUrl includes the tag 'stylesyncapp-20'."
        )

        product_response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": product_prompt}
            ],
            max_tokens=300
        )

        product_text = product_response.choices[0].message.content.strip()
        print("🛒 GPT Product Suggestion:", product_text)

        try:
            suggested_product = json.loads(product_text)
        except json.JSONDecodeError:
            suggested_product = {
                "name": f"Suggested {highlighted_item.title()}",
                "imageUrl": "",
                "affiliateUrl": f"https://www.amazon.com/s?k={highlighted_item.replace(' ', '+')}&tag=stylesyncapp-20"
            }

        return {
            "result": result_text,
            "matchStatus": match_status,
            "highlightedItem": highlighted_item,
            "suggestedProduct": suggested_product
        }

    except Exception as e:
        print("❌ Error:", e)
        return JSONResponse(status_code=500, content={"result": f"Error: {str(e)}"})
