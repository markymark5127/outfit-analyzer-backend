from fastapi import FastAPI, UploadFile, File
import openai
import base64

openai.api_key = "YOUR_OPENAI_API_KEY"

app = FastAPI()

def encode_image_to_base64(image_file: UploadFile):
    return base64.b64encode(image_file.file.read()).decode("utf-8")

@app.post("/analyze-outfit")
async def analyze_outfit(images: list[UploadFile] = File(...)):
    base64_images = [encode_image_to_base64(img) for img in images]

    # Compose image parts
    vision_inputs = [
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}} for img in base64_images
    ]

    # Compose prompt
    user_prompt = {
        "type": "text",
        "text": (
            "Please analyze the clothing in these photo(s). "
            "Do the pieces match in terms of style, color coordination, and overall outfit cohesion? "
            "If not, suggest one or two specific ways to improve the look. Keep your answer to 2-3 sentences."
        )
    }

    messages = [
        {"role": "system", "content": "You are a fashion assistant that gives kind, concise advice about clothing style."},
        {"role": "user", "content": vision_inputs + [user_prompt]}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=150,
        temperature=0.7
    )

    return {"result": response['choices'][0]['message']['content']}
