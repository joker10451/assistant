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

    client = Groq(api_key=api_key)
    
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
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.6,
            max_tokens=256,
            top_p=0.8,
            stream=False,
            stop=None,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ Произошла ошибка при обращении к ИИ: {str(e)}"
