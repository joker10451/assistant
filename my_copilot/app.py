from dotenv import load_dotenv, find_dotenv
# 1. Загрузка переменных (делаем сразу, чтобы все библиотеки видели ключи)
load_dotenv(find_dotenv())

import streamlit as st
import os
import asyncio
import tempfile
import base64
import urllib.parse
from openai import OpenAI
from huggingface_hub import InferenceClient
from faster_whisper import WhisperModel
import edge_tts

# --- Настройка страницы (должна быть первой командой Streamlit) ---
st.set_page_config(page_title="Мой Второй Пилот", page_icon="🚗", layout="centered", initial_sidebar_state="collapsed")

# 2. Настройка клиентов ИИ
deepseek_key = os.getenv("DEEPSEEK_API_KEY")
hf_token = os.getenv("HF_TOKEN")

if not deepseek_key:
    st.warning("⚠️ Не найден DEEPSEEK_API_KEY в .env")
if not hf_token:
    st.warning("⚠️ Не найден HF_TOKEN в .env (нужен для камеры)")

if deepseek_key:
    client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")

if hf_token:
    client_vision = InferenceClient(token=hf_token)

# --- Инициализация Whisper (STT) ---
@st.cache_resource
def load_whisper():
    # Удаляем токены из процесса, чтобы избежать ошибки 401 (Unauthorized)
    if "HF_TOKEN" in os.environ:
        del os.environ["HF_TOKEN"]
    if "HUGGINGFACE_HUB_TOKEN" in os.environ:
        del os.environ["HUGGINGFACE_HUB_TOKEN"]
    
    try:
        return WhisperModel("base", device="cpu", compute_type="int8")
    except Exception as e:
        st.warning(f"⚠️ Ошибка загрузки Whisper: {e}. Пробую публичный доступ...")
        return WhisperModel("base", device="cpu", compute_type="int8", local_files_only=False)

whisper_model = load_whisper()

# --- Функция для озвучивания (TTS) ---
async def text_to_speech(text):
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
        await communicate.save(tmp_path)
    return tmp_path

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
    h1 { text-align: center; font-size: 2.5rem; margin-bottom: 20px; }
    .stChatInputContainer { padding-bottom: 20px; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("🚗 Мой Второй Пилот")

# --- Навигация ---
page = st.sidebar.radio("Выбери режим", ["🧠 Советчик", "👁️ Камера", "🧘 Маршрут"])

# --- БЛОК 1: Советчик (DeepSeek + Voice) ---
if page == "🧠 Советчик":
    st.header("Умный Советчик")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Обработка голосового ввода
    st.write("🎤 Можно спросить голосом:")
    audio_inp = st.audio_input("Записать голос", key="voice_input")

    voice_prompt = None
    if audio_inp:
        with st.spinner("Распознаю речь..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
                    tmp_audio.write(audio_inp.getvalue())
                    temp_audio_path = tmp_audio.name
                
                segments, _ = whisper_model.transcribe(temp_audio_path, beam_size=5)
                voice_prompt = " ".join([segment.text for segment in segments])
                st.info(f"Распознано: {voice_prompt}")
            except Exception as e:
                st.error(f"Ошибка STT: {e}")

    # Вывод истории
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                if st.button("🔊 Озвучить", key=f"audio_{i}"):
                    with st.spinner("Генерирую голос..."):
                        audio_p = asyncio.run(text_to_speech(message["content"]))
                        st.audio(audio_p, format="audio/mp3")

    # Реакция на ввод (текст или голос)
    prompt = st.chat_input("Опиши ситуацию:")
    if voice_prompt: # Если есть голос, используем его
        prompt = voice_prompt

    if prompt:
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
                                {"role": "system", "content": "Ты — спокойный и опытный автоинструктор по имени Алекс. Твоя цель — снизить стресс. Отвечай кратко (1-3 предложения)."},
                            ] + st.session_state.messages
                        )
                        answer = response.choices[0].message.content
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                        
                        # Автоматическая озвучка последнего сообщения если был голосовой ввод
                        if voice_prompt:
                            audio_p = asyncio.run(text_to_speech(answer))
                            st.audio(audio_p, format="audio/mp3", autoplay=True)
                    except Exception as e:
                        st.error(f"Ошибка DeepSeek: {e}")

# --- БЛОК 2: Камера (Hugging Face) ---
elif page == "👁️ Камера":
    st.header("Зоркий Глаз")
    st.warning("Анализ фото через HuggingFace (Qwen2-VL).")
    picture = st.camera_input("Сделай фото приборной панели")
    
    if picture:
        st.image(picture, caption="Анализирую...", width=300)
        if not hf_token:
            st.error("Добавьте HF_TOKEN в файл .env")
        else:
            with st.spinner("Смотрю..."):
                try:
                    image_bytes = picture.getvalue()
                    base64_image = base64.b64encode(image_bytes).decode('utf-8')
                    
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
                    answer = completion.choices[0].message.content
                    st.success(answer)
                    
                    # Озвучка результата
                    if st.button("🔊 Озвучить результат"):
                        audio_p = asyncio.run(text_to_speech(answer))
                        st.audio(audio_p, format="audio/mp3")
                except Exception as e:
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
                    answer = response.choices[0].message.content
                    st.markdown(answer)
                    
                    # Озвучка
                    audio_p = asyncio.run(text_to_speech(answer))
                    st.audio(audio_p, format="audio/mp3")

                    link = f"https://yandex.ru/maps/?rtext={urllib.parse.quote(start)}~{urllib.parse.quote(end)}&rtm=auto"
                    st.link_button("🗺️ Открыть в Яндекс Картах", link)
                except Exception as e:
                    st.error(f"Ошибка: {e}")
        else:
            st.warning("Введите точки маршрута")
