import streamlit as st
import os
from dotenv import load_dotenv, find_dotenv
import google.genai as genai
from PIL import Image

# 1. Загрузка переменных
load_dotenv(find_dotenv())

# --- Настройка страницы (должна быть первой командой Streamlit) ---
st.set_page_config(page_title="Мой Второй Пилот", page_icon="🚗", layout="centered", initial_sidebar_state="collapsed")

# 2. Настройка НОВОГО клиента Google AI
try:
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
except Exception as e:
    st.error(f"Ошибка настройки ключа Google: {e}")
    st.stop()

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

# --- БЛОК 1: Советчик ---
if page == "🧠 Советчик":
    st.header("Умный Советчик")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    # React to user input
    if prompt := st.chat_input("Опиши ситуацию или задай вопрос:"):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            with st.spinner("Думаю..."):
                try:
                    # Construct context
                    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                    full_prompt = f"Ты — спокойный и опытный автоинструктор по имени Алекс. Твоя цель — снизить стресс. Отвечай кратко и дружелюбно.\nИстория диалога:\n{history_text}\nОтвет Алекса:"
                    
                    response = client.models.generate_content(
                        model='gemini-1.5-flash',
                        contents=full_prompt
                    )
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"Ошибка запроса: {e}")

# --- БЛОК 2: Камера (Зрение) ---
elif page == "👁️ Камера":
    st.header("Зоркий Глаз")
    st.write("Что показывают приборы?")
    picture = st.camera_input("Сделай фото приборной панели")
    
    if picture:
        st.image(picture, caption="Анализирую...", width=300)
        with st.spinner("Смотрю..."):
            try:
                # Получаем байты картинки (как в примере пользователя)
                img_data = picture.getvalue()
                
                # Отправляем картинку и текст ИИ
                prompt = "Посмотри на это фото приборной панели автомобиля. Назови горящие индикаторы. Если есть красные значки — объясни опасность и дай совет. Будь краток."
                
                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=[prompt, img_data]
                )
                
                text = response.text
                if text and ("СТОП" in text.upper() or "ОПАСНО" in text.upper()):
                    st.error(text)
                else:
                    st.success(text)
            except Exception as e:
                st.error(f"Ошибка распознавания: {e}")

# --- БЛОК 3: Маршрут ---
elif page == "🧘 Маршрут":
    st.header("Спокойный путь")
    st.write("Здесь ИИ посоветует спокойную дорогу.")
    start = st.text_input("Откуда:", placeholder="Дом")
    end = st.text_input("Куда:", placeholder="Работа")
    
    if st.button("Построить маршрут"):
        if start and end:
            with st.spinner("Ищу путь..."):
                try:
                    prompt = f"Я новичок, еду из {start} в {end}. Подскажи, через какие районы или улицы лучше проехать, чтобы избежать пробок и хаоса, или советуй избегать центры города. Пожелай удачи в конце."
                    response = client.models.generate_content(
                        model='gemini-1.5-flash',
                        contents=prompt
                    )
                    st.markdown(response.text)
                    
                    # Generate deep link
                    import urllib.parse
                    encoded_start = urllib.parse.quote(start)
                    encoded_end = urllib.parse.quote(end)
                    link = f"https://www.google.com/maps/dir/?api=1&origin={encoded_start}&destination={encoded_end}&travelmode=driving"
                    st.link_button("🗺️ Открыть в Google Картах", link)
                except Exception as e:
                    st.error(f"Ошибка: {e}")
        else:
            st.warning("Введите точки маршрута")
