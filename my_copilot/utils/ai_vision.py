import os
import streamlit as st
import requests
import base64
import io
from PIL import Image

def analyze_dashboard(image_file):
    """
    Analyzes an image using Hugging Face Inference API (LLaVA-1.5-7b).
    Args:
        image_file: Streamlit UploadedFile object.
    Returns:
        String description from AI.
    """
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token and "HF_TOKEN" in st.secrets:
        hf_token = st.secrets["HF_TOKEN"]
        
    if not hf_token:
        return "⚠️ Ошибка: Не найден Hugging Face Token. Пожалуйста, добавьте его в .env или secrets.toml."

    API_URL = "https://api-inference.huggingface.co/models/llava-hf/llava-1.5-7b-hf"
    headers = {"Authorization": f"Bearer {hf_token}"}

    try:
        # Convert uploaded file to base64
        image = Image.open(image_file)
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # Construct payload for LLaVA
        # The prompt format is specific to LLaVA: USER: <image>\nPrompt\nASSISTANT:
        prompt_text = "USER: <image>\nТы — помощник водителя. На этом изображении приборная панель автомобиля. Назови цвет и значение горящих индикаторов. Если есть красный значок — напиши 'СТОП' и объясни почему.\nASSISTANT:"
        
        payload = {
            "inputs": prompt_text,
            "parameters": {
                "max_new_tokens": 200,
                "do_sample": False
            },
            # Some HF endpoints auto-handle base64 in specific fields, 
            # but often we need to check the specific model pipeline type.
            # For "image-text-to-text", providing "image" as a separate key often works in HF Inference API.
            "image": img_str
        }

        response = requests.post(API_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            # Fallback or specific error handling
            if "loading" in response.text.lower():
                return "❄️ Модель загружается (холодный старт). Попробуйте через 30 секунд."
            return f"Ошибка API ({response.status_code}): {response.text}"
            
        result = response.json()
        
        # Parse response
        if isinstance(result, list) and len(result) > 0 and "generated_text" in result[0]:
            full_text = result[0]["generated_text"]
            # Extract just the assistant part
            if "ASSISTANT:" in full_text:
                return full_text.split("ASSISTANT:")[-1].strip()
            return full_text
        elif "error" in result:
             return f"Ошибка API: {result['error']}"
        else:
            return f"Непонятный ответ API: {result}"

    except Exception as e:
        return f"⚠️ Ошибка Vision AI: {str(e)}"
