import streamlit as st
import os
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI
from huggingface_hub import InferenceClient
import urllib.parse

# 1. Загрузка переменных
load_dotenv(find_dotenv())

# --- Настройка страницы (должна быть первой командой Streamlit) ---
st.set_page_config(page_title="Мой Второй Пилот", page_icon="🚗", layout="centered", initial_sidebar_state="collapsed")

# 2. Настройка клиента DeepSeek
deepseek_key = os.getenv("DEEPSEEK_API_KEY")
hf_token = os.getenv("HF_TOKEN")

# Проверка ключей
if not deepseek_key:
    st.warning("⚠️ Не найден DEEPSEEK_API_KEY в .env")
if not hf_token:
    st.warning("⚠️ Не найден HF_TOKEN в .env (нужен для камеры)")

# Инициализация клиентов
if deepseek_key:
    client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")

if hf_token:
    client_vision = InferenceClient(token=hf_token)

# Custom CSS for mobile-like feel
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        height: 60px;
        border-radius: 15px;
        font-size: 20px;
        font-weight: bold;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    h1 {
        text-align: center;
        font-size: 2.5rem;
        margin-bottom: 20px;
    }
    .stChatInputContainer {
        padding-bottom: 20px;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("🚗 Мой Второй Пилот")

# --- Навигация ---
page = st.sidebar.radio("Выбери режим", ["🧠 Советчик", "👁️ Камера", "🧘 Маршрут"])

# --- БЛОК 1: Советчик (DeepSeek) ---
if page == "🧠 Советчик":
    st.header("Умный Советчик")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Вывод истории
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    # Реакция на ввод
    if prompt := st.chat_input("Опиши ситуацию:"):
        if not deepseek_key:
            st.error("Добавьте DEEPSEEK_API_KEY в файл .env")
        else:
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("assistant"):
                with st.spinner("Думаю..."):
                    try:
                        response = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[
                                {"role": "system", "content": "Ты — спокойный и опытный автоинструктор по имени Алекс. Твоя цель — снизить стресс. Отвечай кратко и дружелюбно."},
                            ] + st.session_state.messages
                        )
                        answer = response.choices[0].message.content
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    except Exception as e:
                        st.error(f"Ошибка DeepSeek: {e}")

# --- БЛОК 2: Камера (Hugging Face) ---
elif page == "👁️ Камера":
    st.header("Зоркий Глаз")
    st.warning("Для анализа фото используем HuggingFace (Qwen2-VL).")
    picture = st.camera_input("Сделай фото приборной панели")
    
    if picture:
        st.image(picture, caption="Анализирую...", width=300)
        if not hf_token:
            st.error("Добавьте HF_TOKEN в файл .env")
        else:
                try:
                    # Модель Qwen2-VL-7B-Instruct
                    import base64
                    image_bytes = picture.getvalue()
                    base64_image = base64.b64encode(image_bytes).decode('utf-8')
                    
                    # Отправляем через InferenceClient.chat.completions
                    completion = client_vision.chat.completions.create(
                        model="Qwen/Qwen2-VL-7B-Instruct",
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Это фото приборной панели автомобиля. Назови горящие индикаторы. Опасно ли ехать? Будь краток."},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ]
                        }],
                        max_tokens=500
                    )
                    
                    # Note: InferenceClient might return different format, adjusting
                    answer = completion.choices[0].message.content
                    st.success(answer)
                except Exception as e:
                    # Fallback or detailed error
                    st.error(f"Ошибка фото-модуля: {e}")

# --- БЛОК 3: Маршрут ---
elif page == "🧘 Маршрут":
    st.header("Спокойный путь")
    start = st.text_input("Откуда:", placeholder="Дом")
    end = st.text_input("Куда:", placeholder="Работа")
    
    if st.button("Построить маршрут"):
        if not deepseek_key:
            st.error("Добавьте DEEPSEEK_API_KEY в файл .env")
        elif start and end:
            with st.spinner("Ищу путь..."):
                try:
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": "Ты спокойный автоинструктор. Подскажи новичку безопасный и спокойный маршрут."},
                            {"role": "user", "content": f"Из {start} в {end}."}
                        ]
                    )
                    st.markdown(response.choices[0].message.content)
                    
                    # Яндекс.Карты Link
                    link = f"https://yandex.ru/maps/?rtext={urllib.parse.quote(start)}~{urllib.parse.quote(end)}&rtm=auto"
                    st.link_button("🗺️ Открыть в Яндекс Картах", link)
                except Exception as e:
                    st.error(f"Ошибка: {e}")
        else:
            st.warning("Введите точки маршрута")
