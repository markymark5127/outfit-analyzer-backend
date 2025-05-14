import os
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from base64 import b64encode

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route('/analyze', methods=['POST'])
def analyze():
    images = []

    for key in request.files:
        file = request.files[key]
        temp_path = tempfile.mktemp(suffix='.jpg')
        file.save(temp_path)
        with open(temp_path, "rb") as f:
            encoded = b64encode(f.read()).decode('utf-8')
            images.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}})

    if len(images) == 0:
        return jsonify({"result": "No images received."}), 400
    elif len(images) > 5:
        return jsonify({"result": "You can upload up to 5 images only."}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "Do these clothes match? Be brief."}] + images
                }
            ],
            max_tokens=200
        )
        return jsonify({"result": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"result": f"Error: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
