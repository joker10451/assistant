import os
import asyncio
import logging
import tempfile
import json
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from faster_whisper import WhisperModel
import edge_tts
import chromadb
from sentence_transformers import SentenceTransformer

# 1. Загрузка переменных
load_dotenv(find_dotenv())
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")

# 2. Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 3. Инициализация моделей (STT, RAG, Клиенты)
print("Загрузка моделей...")
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
embed_model = SentenceTransformer('all-MiniLM-L6-v2')
client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# Хранилище истории диалогов (в памяти)
user_histories = {}

# Подключение к ChromaDB
db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
db_client = chromadb.PersistentClient(path=db_path)
try:
    collection = db_client.get_collection(name="audi_manual")
except:
    collection = None

# Загрузка истории ТО
HISTORY_FILE = "service_history.json"
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f: return json.load(f)
    return {"oil_change": {"mileage": 145000, "date": "2024-01-01"}}

# 4. Функции
async def text_to_speech(text):
    communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
        await communicate.save(tmp_path)
    return tmp_path

# 5. Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я Алекс, твой второй пилот Audi A3. Присылай голосовые сообщения — я подскажу, что делать с машиной или отвечу на вопросы из инструкции.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hist = load_history()
    last = hist["oil_change"]
    await update.message.reply_text(f"📊 Текущий статус ТО:\nПоследняя замена масла: {last['date']} ({last['mileage']} км).")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_histories:
        user_histories[user_id] = []

    # Если пришло голосовое сообщение
    text_prompt = None
    if update.message.voice:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_ogg:
            voice_file = await update.message.voice.get_file()
            await voice_file.download_to_drive(tmp_ogg.name)
            
            # STT
            with st.spinner("Слушаю..."):
                segments, _ = whisper_model.transcribe(tmp_ogg.name, beam_size=5)
                text_prompt = " ".join([segment.text for segment in segments])
            if text_prompt:
                await update.message.reply_text(f"🎤 Понял: \"{text_prompt}\"")
    else:
        text_prompt = update.message.text

    # Ответ от Алекса
    if text_prompt:
        hist = load_history()
        last_oil = hist["oil_change"]
        
        # Поиск в RAG
        rag_context = ""
        if collection:
            query_vector = embed_model.encode(text_prompt).tolist()
            results = collection.query(query_embeddings=[query_vector], n_results=2)
            rag_context = "\nИНФОРМАЦИЯ ИЗ ИНСТРУКЦИИ:\n" + "\n".join(results['documents'][0])

        service_info = f"Последняя замена масла: {last_oil['date']} на {last_oil['mileage']} км."
        system_prompt = f"Ты — Алекс, спокойный автоинструктор Audi. {service_info} {rag_context}\nОтвечай кратко, помогай водителю не нервничать."
        
        # Добавляем сообщение пользователя в историю
        user_histories[user_id].append({"role": "user", "content": text_prompt})
        # Держим только последние 10 сообщений
        user_histories[user_id] = user_histories[user_id][-10:]

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": system_prompt}] + user_histories[user_id]
            )
            answer = response.choices[0].message.content
            
            # Добавляем ответ в историю
            user_histories[user_id].append({"role": "assistant", "content": answer})
            
            # Отправка текста
            await update.message.reply_text(answer)
            
            # Отправка аудио (TTS)
            try:
                audio_path = await text_to_speech(answer)
                with open(audio_path, "rb") as audio:
                    await update.message.reply_voice(audio)
                os.remove(audio_path)
            except Exception as tts_err:
                logging.error(f"TTS Error: {tts_err}")
            
        except Exception as e:
            await update.message.reply_text(f"Упс, ошибка связи: {e}")

# 6. Запуск
if __name__ == "__main__":
    if not TG_TOKEN:
        print("Ошибка: TELEGRAM_BOT_TOKEN не найден в .env")
    else:
        app = Application.builder().token(TG_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("status", status))
        app.add_handler(MessageHandler(filters.TEXT | filters.VOICE, handle_message))
        
        print("Алекс в Телеграме запущен!")
        app.run_polling()
