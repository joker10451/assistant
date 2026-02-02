import os
import streamlit as st
from groq import Groq

def get_text_advice(prompt, history=[]):
    """
    Generates advice using Groq API.
    Args:
        prompt: User input string.
        history: List of dicts [{"role": "user", "content": "..."}].
    Returns:
        String response from AI.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key and "GROQ_API_KEY" in st.secrets:
        api_key = st.secrets["GROQ_API_KEY"]
        
    if not api_key:
        return "⚠️ Ошибка: Не найден Groq API Key. Пожалуйста, добавьте его в .env или secrets.toml."

    client = Groq(api_key=api_key.strip())
    
    # System prompt for "Alex"
    system_prompt = {
        "role": "system",
        "content": (
            "Ты — спокойный и опытный автоинструктор по имени Алекс. "
            "Ты объясняешь вещи девушке-новичку простым языком, без сложных терминов (ПДД, КБМ и т.д.). "
            "Твои ответы должны быть короткими (1-3 предложения). "
            "Если ситуация опасная, используй caps lock только для важного действия (например: ВКЛЮЧИ АВАРИЙКУ). "
            "Будь поддерживающим и вежливым."
        )
    }

    messages = [system_prompt] + history + [{"role": "user", "content": prompt}]

    try:
        completion = client.chat.completions.create(
            model="mixtral-8x7b-32768", # Fallback model
            messages=messages,
            temperature=0.6,
            max_tokens=256,
            top_p=0.8,
            stream=False,
            stop=None,
        )
        return completion.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg or "Forbidden" in error_msg:
            # Fallback to Hugging Face if Groq is blocked
            hf_token = os.getenv("HF_TOKEN")
            if hf_token:
                try:
                    import requests
                    API_URL = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"
                    headers = {"Authorization": f"Bearer {hf_token}"}
                    
                    # Simple prompt construction for fallback
                    full_prompt = f"<s>[INST] {system_prompt['content']} \n\n {prompt} [/INST]"
                    
                    response = requests.post(API_URL, headers=headers, json={"inputs": full_prompt})
                    if response.status_code == 200:
                         return response.json()[0]['generated_text'].split("[/INST]")[-1].strip()
                    else:
                        return f"⚠️ Groq 403 (блокировка?). HF Fallback тоже не сработал: {response.status_code}"
                except Exception as hf_e:
                    return f"⚠️ Groq недоступен (403). Попытка через HF не удалась: {hf_e}"
            
            return "⚠️ Ошибка 403 (Groq): Доступ запрещен. Если вы в РФ, нужен VPN. Или проверьте ключ."
            
        return f"⚠️ Произошла ошибка при обращении к ИИ: {error_msg}"
