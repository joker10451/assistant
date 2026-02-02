from dotenv import load_dotenv, find_dotenv
# 1. Загрузка переменных (делаем сразу)
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
import chromadb
from sentence_transformers import SentenceTransformer

# --- Настройка страницы ---
st.set_page_config(page_title="Мой Второй Пилот", page_icon="🚗", layout="centered", initial_sidebar_state="expanded")

# 2. Настройка клиентов ИИ
deepseek_key = os.getenv("DEEPSEEK_API_KEY")
hf_token = os.getenv("HF_TOKEN")

if not deepseek_key:
    st.warning("⚠️ Не найден DEEPSEEK_API_KEY в .env")

if deepseek_key:
    client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")

if hf_token:
    client_vision = InferenceClient(token=hf_token)

# --- Инициализация Whisper (STT) ---
@st.cache_resource
def load_whisper():
    if "HF_TOKEN" in os.environ: del os.environ["HF_TOKEN"]
    if "HUGGINGFACE_HUB_TOKEN" in os.environ: del os.environ["HUGGINGFACE_HUB_TOKEN"]
    try:
        return WhisperModel("base", device="cpu", compute_type="int8")
    except Exception as e:
        st.warning(f"⚠️ Ошибка загрузки Whisper: {e}")
        return WhisperModel("base", device="cpu", compute_type="int8", local_files_only=False)

whisper_model = load_whisper()

# --- Инициализация Базы Знаний (RAG) ---
@st.cache_resource
def load_rag():
    try:
        # Модель для поиска по смыслам
        embed_model = SentenceTransformer('all-MiniLM-L6-v2')
        # Подключение к базе
        db_client = chromadb.PersistentClient(path="chroma_db")
        collection = db_client.get_collection(name="audi_manual")
        return embed_model, collection
    except Exception as e:
        st.info("ℹ️ База знаний (manual.pdf) не найдена или не создана. Алекс будет отвечать из общих знаний.")
        return None, None

embedding_model, rag_collection = load_rag()

# --- Функции ---
async def text_to_speech(text):
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
        await communicate.save(tmp_path)
    return tmp_path

# Custom CSS
st.markdown("""
<style>
    .stButton>button { width: 100%; height: 60px; border-radius: 15px; font-size: 20px; font-weight: bold; margin-top: 10px; margin-bottom: 10px; }
    h1 { text-align: center; font-size: 2.5rem; margin-bottom: 20px; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

import json
from datetime import datetime

# --- Состояние авто: Загрузка/Сохранение истории ---
HISTORY_FILE = "service_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {"oil_change": {"mileage": 145000, "date": "2024-01-01"}}

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

history = load_history()

st.title("🚗 Мой Второй Пилот")

# --- Блок Состояния ---
st.markdown("### 📊 Состояние авто")
mileage = st.number_input("Текущий пробег (км):", value=150000, step=1000, key="main_mileage")

last_oil = history["oil_change"]
oil_rem = 10000 - (mileage - last_oil["mileage"])
belt_rem = 60000 - (mileage % 60000)

col1, col2 = st.columns(2)
with col1:
    st.info(f"🔧 Масло через: **{oil_rem} км**")
    st.caption(f"Последняя замена: {last_oil['date']} ({last_oil['mileage']} км)")
    if st.button("🧼 Я поменял масло!", use_container_width=True):
        history["oil_change"] = {"mileage": mileage, "date": datetime.now().strftime("%d.%m.%Y")}
        save_history(history)
        st.success("Данные обновлены!")
        st.rerun()

with col2:
    if belt_rem < 5000:
        st.warning(f"⚠️ ГРМ: {belt_rem} км")
    else:
        st.success(f"⛓️ ГРМ: {belt_rem} км")

# --- Блок Быстрых Функций (SOS и Парковка) ---
st.markdown("---")
col_sos, col_park = st.columns(2)

with col_sos:
    if st.button("🚨 SOS Помощь", type="primary", use_container_width=True):
        st.session_state.show_sos = not st.session_state.get("show_sos", False)

with col_park:
    if "parking_pos" not in st.session_state:
        st.session_state.parking_pos = None
    
    park_btn_label = "📍 Где машина?" if st.session_state.parking_pos else "🅿️ Припарковался"
    if st.button(park_btn_label, use_container_width=True):
        if not st.session_state.parking_pos:
            st.session_state.parking_pos = "saved"
            st.toast("📍 Место парковки сохранено!")
        else:
            # Открываем ссылку
            st.session_state.show_park_link = True

# Логика SOS
if st.session_state.get("show_sos"):
    st.error("🚨 РЕЖИМ SOS: Соблюдай спокойствие!")
    st.markdown(f"""
    1. **Аварийка** и жилет. 
    2. **Знак** (30м). 
    3. **Координаты**: `55.75, 37.62`. 
    4. **Авто**: Audi A3 2006, {mileage} км.
    """)
    if st.button("✅ Закрыть SOS", use_container_width=True):
        st.session_state.show_sos = False
        st.rerun()

# Логика Парковки (ссылка)
if st.session_state.get("show_park_link"):
    st.success("Нажми кнопку ниже, чтобы найти авто:")
    st.link_button("🏃 Найти на карте", "https://yandex.ru/maps/?text=Мое+местоположение", use_container_width=True)
    if st.button("❌ Сбросить место"):
        st.session_state.parking_pos = None
        st.session_state.show_park_link = False
        st.rerun()

st.markdown("---")

# --- Навигация через Вкладки (Tabs) ---
tab_chat, tab_cam, tab_map = st.tabs(["🧠 Советчик", "👁️ Камера", "🧘 Маршрут"])

# --- БЛОК 1: Советчик (DeepSeek + RAG + Voice) ---
with tab_chat:
    st.header("Умный Советчик")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Голосовой ввод
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
                    audio_p = asyncio.run(text_to_speech(message["content"]))
                    st.audio(audio_p, format="audio/mp3", autoplay=True)

    # Ввод
    prompt = st.chat_input("Опиши ситуацию:")
    if voice_prompt: prompt = voice_prompt

    if prompt:
        if not deepseek_key:
            st.error("Добавьте DEEPSEEK_API_KEY в файл .env")
        else:
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("assistant"):
                with st.spinner("Ищу в инструкции и думаю..."):
                    context = ""
                    # Добавляем инфо об истории ТО в контекст Алекса
                    service_context = f"\nИСТОРИЯ ТО: Последняя замена масла была {last_oil['date']} на пробеге {last_oil['mileage']} км. Сейчас пробег {mileage} км. До следующей замены {oil_rem} км."
                    
                    if rag_collection and embedding_model:
                        # Поиск по базе знаний
                        query_vector = embedding_model.encode(prompt).tolist()
                        results = rag_collection.query(query_embeddings=[query_vector], n_results=3)
                        context = "\nИНФОРМАЦИЯ ИЗ ИНСТРУКЦИИ МАШИНЫ:\n" + "\n".join(results['documents'][0])

                    try:
                        response = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[
                                {"role": "system", "content": f"Ты — Алекс, спокойный автоинструктор. Твоя цель — снизить стресс. {service_context} {context} \nОтвечай кратко (1-3 предложения)."},
                            ] + st.session_state.messages
                        )
                        answer = response.choices[0].message.content
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                        
                        # АВТО-ОЗВУЧКА для любого типа ввода (голос или текст)
                        with st.spinner("Озвучиваю..."):
                            audio_p = asyncio.run(text_to_speech(answer))
                            st.audio(audio_p, format="audio/mp3", autoplay=True)
                    except Exception as e:
                        st.error(f"Ошибка DeepSeek: {e}")

# --- БЛОК 2: Камера (Hugging Face) ---
with tab_cam:
    st.header("Зоркий Глаз")
    picture = st.camera_input("Сделай фото приборной панели")
    if picture:
        st.image(picture, caption="Анализирую...", width=300)
        with st.spinner("Смотрю... Проверка индикаторов..."):
            try:
                if "HF_TOKEN" in os.environ: del os.environ["HF_TOKEN"]
                image_bytes = picture.getvalue()
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                completion = client_vision.chat.completions.create(
                    model="Qwen/Qwen2-VL-7B-Instruct",
                    messages=[{"role": "user", "content": [{"type": "text", "text": "Это фото приборной панели. Назови горящие значки. Опасно ли ехать? Будь краток."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
                    max_tokens=300
                )
                answer = completion.choices[0].message.content
                st.success(answer)
                
                # Авто-озвучка результата анализа фото
                with st.spinner("Озвучиваю результат..."):
                    audio_p = asyncio.run(text_to_speech(answer))
                    st.audio(audio_p, format="audio/mp3", autoplay=True)
            except Exception as e:
                st.error(f"Ошибка фото-модуля: {e}")

# --- БЛОК 3: Маршрут ---
with tab_map:
    st.header("Спокойный путь")
    start = st.text_input("Откуда:")
    end = st.text_input("Куда:")
    if st.button("Построить"):
        if start and end:
            with st.spinner("Ищу безопасный путь..."):
                try:
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role": "user", "content": f"Я новичок, еду из {start} в {end}. Подскажи спокойный путь."}])
                    ans = res.choices[0].message.content
                    st.markdown(ans)
                    audio_p = asyncio.run(text_to_speech(ans))
                    st.audio(audio_p, format="audio/mp3", autoplay=True)
                    link = f"https://yandex.ru/maps/?rtext={urllib.parse.quote(start)}~{urllib.parse.quote(end)}&rtm=auto"
                    st.link_button("🗺️ Яндекс Карты", link)
                except Exception as e: st.error(f"Ошибка: {e}")
