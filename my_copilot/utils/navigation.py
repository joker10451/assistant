import os
import streamlit as st
from groq import Groq
import urllib.parse

def get_calm_route_advice(start, end):
    """
    Generates advice for a calm route using Groq API.
    Args:
        start: Starting point.
        end: Destination.
    Returns:
        String advice from AI and a Google Maps link.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key and "GROQ_API_KEY" in st.secrets:
        api_key = st.secrets["GROQ_API_KEY"]
        
    if not api_key:
        return "⚠️ Ошибка: Не найден Groq API Key.", ""

    client = Groq(api_key=api_key)
    
    prompt = f"""
    Пользователь-новичок хочет проехать от "{start}" до "{end}".
    Дай краткий совет (2-3 предложения), как ехать максимально спокойно (избегая сложных развязок, если возможно, или просто успокой).
    Не придумывай несуществующие улицы. Лучше дай общие советы по ориентирам или времени выезда.
    В конце пожелай удачи.
    """

    system_prompt = {
        "role": "system",
        "content": "Ты — спокойный автоинструктор. Твоя цель — снизить стресс водителя перед поездкой."
    }

    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[system_prompt, {"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
        )
        advice = completion.choices[0].message.content
        
        # Generate Google Maps Link (Deep Link)
        # Avoid highways, ferries if possible? Google Maps URL params: 
        # dirflg=h (avoid highways - good for strict finding, but maybe too much)
        # For now just standard directions.
        encoded_start = urllib.parse.quote(start)
        encoded_end = urllib.parse.quote(end)
        maps_link = f"https://www.google.com/maps/dir/?api=1&origin={encoded_start}&destination={encoded_end}&travelmode=driving"
        
        return advice, maps_link
        
    except Exception as e:
        return f"⚠️ Ошибка навигации: {str(e)}", ""
