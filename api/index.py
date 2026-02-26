from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import PyPDF2
import random
import os

app = Flask(__name__)
CORS(app)

# We will securely set this token in Vercel's dashboard later
HF_TOKEN = os.environ.get("HF_TOKEN") 

def query_gemma(prompt):
    # The correct URL (My typo is gone!)
    API_URL = "https://router.huggingface.co/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "Qwen/Qwen2.5-72B-Instruct", 
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150,
        "temperature": 0.3
    }
    
    print("-> Pinging Universal AI Router...")
    response = requests.post(API_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        print("-> Brain Awake! Response Received.")
        return response.json()['choices'][0]['message']['content'].strip()
    else:
        print(f"-> HF ERROR: {response.status_code} - {response.text}")
        return "API Overloaded. Please try again."

@app.route('/api/analyze', methods=['POST'])
def analyze():
    mode = request.form.get("query", "DEMO")
    lang_code = request.form.get("lang", "en")
    
    lang_map = {
        "en": "English", "hi": "Hindi", "te": "Telugu",
        "es": "Spanish", "fr": "French", "ar": "Arabic",
        "zh": "Chinese", "ru": "Russian"
    }
    lang_name = lang_map.get(lang_code, "English")
    
    file = request.files.get("file")
    if mode != "PATIENT_CHAT" and not file:
        return jsonify({"status": "error", "analysis": "No file detected."})
    
    filename = file.filename if file else "No File"
    extracted_text = ""
    
    # Process PDF locally on Vercel
    if file and file.filename.endswith('.pdf') and mode == "PATIENT_REPORT":
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in range(min(2, len(pdf_reader.pages))):
                extracted_text += pdf_reader.pages[page].extract_text() + " "
            extracted_text = extracted_text[:1000]
        except Exception:
            extracted_text = "Data unreadable."

    # Build the Prompt
    if mode == "PATIENT_CHAT":
        user_text = request.form.get("text", "")
        prompt = f"You are a medical assistant. A patient asks: '{user_text}'. Give empathetic advice. You MUST write your entire response ONLY in {lang_name}."
    elif mode == "PATIENT_REPORT":
        if extracted_text and extracted_text != "Data unreadable.":
            prompt = f"Act as a helpful doctor. Read this extracted lab report text: '{extracted_text}'. Summarize the key findings in 3 simple bullet points. You MUST write your entire response ONLY in {lang_name}."
        else:
            prompt = f"Act as a helpful doctor. Give a generic 3-bullet-point explanation of common high White Blood Cell counts. You MUST write your response ONLY in {lang_name}."
    elif mode == "PATIENT_SCAN":
        prompt = f"Act as a helpful doctor. The patient uploaded a scan. Explain in simple terms that an abnormal density was found and they should consult a specialist. You MUST write your entire response ONLY in {lang_name}."
    elif mode == "DOCTOR_FULL":
        prompt = f"You are a neurosurgeon's AI assistant. The doctor uploaded a brain scan named '{filename}'. Write a concise, highly clinical, 4-sentence surgical risk assessment mentioning the Superior Sagittal Sinus."
    else:
        return jsonify({"status": "error", "analysis": "Unknown Mode."})

    # Call the Cloud AI
    ai_response = query_gemma(prompt)

    # Generate Mock 3D Coordinates
    t_x = round(random.uniform(0.5, 1.5) * random.choice([1, -1]), 2)
    t_y = round(random.uniform(-0.5, 0.8), 2)
    t_z = round(random.uniform(-1.0, 1.2), 2)

    return jsonify({
        "status": "success",
        "tumor_pos": {"x": t_x, "y": t_y, "z": t_z}, 
        "analysis": f"<b>[Neurolens Cloud Inference]</b><br><br>{ai_response}"
    })

# Vercel needs the app exposed like this
if __name__ == '__main__':
    app.run()