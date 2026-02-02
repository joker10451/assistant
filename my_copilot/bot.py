import os
import asyncio
import logging
import tempfile
import json
import datetime
from dotenv import load_dotenv, find_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from faster_whisper import WhisperModel
import edge_tts
import chromadb
from sentence_transformers import SentenceTransformer
from utils.skills import SkillManager, OPENCLAW_TOOLS
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

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

# 2.5 Хранилище пользователей (для проактивности)
USER_DATA_FILE = "user_data.json"
def save_user(chat_id):
    users = []
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f: users = json.load(f)
    if chat_id not in users:
        users.append(chat_id)
        with open(USER_DATA_FILE, "w") as f: json.dump(users, f)

def get_users():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f: return json.load(f)
    return []

# Хранилище истории диалогов (в памяти)
user_histories = {}

# Сервер для поддержания активности (Heartbeat)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Alex Audi CoPilot is alive and running!")

    def log_message(self, format, *args):
        return # Отключаем логирование запросов, чтобы не засорять консоль

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    logging.info(f"Запуск Heartbeat сервера на порту {port}...")
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# Подключение к ChromaDB
db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
db_client = chromadb.PersistentClient(path=db_path)
try:
    collection = db_client.get_collection(name="audi_manual")
except:
    collection = None

# 3.5 Личная история в ChromaDB
try:
    user_history_col = db_client.get_or_create_collection(name="user_history")
except:
    user_history_col = None

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
    save_user(update.effective_chat.id)
    await update.message.reply_text("Привет! Я Алекс, твой второй пилот Audi A3. Я поумнел: теперь ты можешь прислать мне фото чека из сервиса, и я запомню его. Для полного отчета по машине напиши /report.")

# 5.5 Проактивные задачи (Jobs)
async def morning_job(context: ContextTypes.DEFAULT_TYPE):
    users = get_users()
    brief = SkillManager.get_proactive_briefing("Калуга")
    for chat_id in users:
        try:
            await context.bot.send_message(chat_id=chat_id, text=brief, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Не удалось отправить бриф {chat_id}: {e}")

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report_text = SkillManager.generate_service_report()
    await update.message.reply_text(report_text, parse_mode="HTML")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
        await photo_file.download_to_drive(tmp_img.name)
        
        await update.message.reply_text("👁 Вижу документ. Анализирую содержимое...")
        
        # Используем Hugging Face для 'зрения' (как в Streamlit)
        hf_token = os.getenv("HUGGINGFACE_API_KEY")
        if not hf_token:
            await update.message.reply_text("Ошибка: Не настроен ключ HuggingFace для зрения.")
            return

        from huggingface_hub import InferenceClient
        hf_client = InferenceClient(token=hf_token)
        
        try:
            with open(tmp_img.name, "rb") as f:
                img_bytes = f.read()
            
            # Базовое описание изображения (для чеков лучше использовать OCR, но начнем с описания)
            description = hf_client.image_to_text(img_bytes, model="Salesforce/blip-image-captioning-large")
            text_desc = description[0]["generated_text"] if isinstance(description, list) else description
            
            # Передаем описание Алексу, чтобы он понял, что на фото
            system_prompt = "Ты — Алекс. Тебе прислали фото документа. Описание фото: " + text_desc + ". Если это похоже на заказ-наряд или чек, выдели важную информацию (что чинили, какой пробег). Если нет — просто скажи, что видишь."
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": "Что на этом фото?"}]
            )
            answer = response.choices[0].message.content
            await update.message.reply_text(f"📝 Мой анализ:\n{answer}")
            
        except Exception as e:
            await update.message.reply_text(f"Не удалось распознать фото: {e}")
        finally:
            os.remove(tmp_img.name)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hist = load_history()
    last = hist["oil_change"]
    await update.message.reply_text(f"📊 <b>Текущий статус ТО:</b>\nПоследняя замена масла: {last['date']} ({last['mileage']} км).", parse_mode="HTML")

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
        
        # Поиск в RAG (Два источника: Инструкция + Личная история)
        combined_context = ""
        query_vector = embed_model.encode(text_prompt).tolist()
        
        # 1. Из инструкции
        if collection:
            res_manual = collection.query(query_embeddings=[query_vector], n_results=2)
            combined_context += "\nИНФОРМАЦИЯ ИЗ ИНСТРУКЦИИ:\n" + "\n".join(res_manual['documents'][0])
        
        # 2. Из истории машины
        if user_history_col:
            res_user = user_history_col.query(query_embeddings=[query_vector], n_results=3)
            if res_user['documents'][0]:
                combined_context += "\nИЗ ИСТОРИИ ЭТОЙ МАШИНЫ:\n" + "\n".join(res_user['documents'][0])

        service_info = f"Последняя замена масла: {last_oil['date']} на {last_oil['mileage']} км."
        system_prompt = (
            f"Ты — Алекс, автономный ассистент водителя Audi A3. {service_info}\n"
            "У тебя есть доступ к инструкции и К ИСТОРИИ ОБСЛУЖИВАНИЯ этой машины.\n"
            "Твоя задача — находить связи между прошлыми событиями и текущими жалобами (диагностика).\n"
            f"Контекст: {combined_context}\n"
            "ВАЖНО: Для выделения текста используй ТОЛЬКО HTML-теги (например, <b>жирный</b>, <i>курсив</i>). "
            "НЕ используй Markdown (звездочки). Отвечай кратко, профессионально и спокойно."
        )
        
        # Добавляем сообщение пользователя в историю
        user_histories[user_id].append({"role": "user", "content": text_prompt})
        # Держим только последние 10 сообщений
        user_histories[user_id] = user_histories[user_id][-10:]

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": system_prompt}] + user_histories[user_id],
                tools=OPENCLAW_TOOLS,
                tool_choice="auto"
            )
            
            msg = response.choices[0].message
            
            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    func_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    logging.info(f"Агент вызывает навык: {func_name}")
                    
                    if func_name == "get_weather":
                        result = SkillManager.get_weather(**args)
                    elif func_name == "get_part_info":
                        result = SkillManager.get_part_info(**args)
                    elif func_name == "log_car_event":
                        result = SkillManager.log_car_event(**args)
                        # Синхронизируем с ChromaDB для семантического поиска
                        if user_history_col:
                            now = datetime.datetime.now()
                            user_history_col.add(
                                ids=[str(now.timestamp())],
                                documents=[f"Событие {now.strftime('%d.%m.%Y')}: {args['event_description']} (Пробег: {args.get('mileage', 0)} км)"],
                                embeddings=[embed_model.encode(args['event_description']).tolist()]
                            )
                    elif func_name == "remove_last_event":
                        result = SkillManager.remove_last_event()
                        # В идеале тут нужно удаление из ChromaDB, но пока ограничимся JSON
                        # чтобы не усложнять логику ID.
                    else:
                        result = "Навык не найден."
                    
                    user_histories[user_id].append(msg)
                    user_histories[user_id].append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": func_name,
                        "content": result
                    })
                    
                    final_res = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "system", "content": system_prompt}] + user_histories[user_id]
                    )
                    answer = final_res.choices[0].message.content
            else:
                answer = msg.content
            
            # Добавляем ответ в историю
            user_histories[user_id].append({"role": "assistant", "content": answer})
            
            # Отправка текста с поддержкой HTML
            await update.message.reply_text(answer, parse_mode="HTML")
            
            # Отправка аудио (TTS) ПРИОСТАНОВЛЕНА ПО ПРОСЬБЕ ПОЛЬЗОВАТЕЛЯ
            # try:
            #     audio_path = await text_to_speech(answer)
            #     if os.path.exists(audio_path):
            #         with open(audio_path, "rb") as audio:
            #             await update.message.reply_voice(audio)
            #         await asyncio.sleep(0.5)
            #         os.remove(audio_path)
            # except Exception as tts_err:
            #     logging.error(f"TTS Error: {tts_err}")
            
        except Exception as e:
            await update.message.reply_text(f"Упс, ошибка связи: {e}")

# 6. Запуск
if __name__ == "__main__":
    if not TG_TOKEN:
        print("Ошибка: TELEGRAM_BOT_TOKEN не найден в .env")
    else:
        app = Application.builder().token(TG_TOKEN).build()
        
        # Настройка планировщика (Jobs)
        job_queue = app.job_queue
        # Утренний бриф каждый день в 08:00 (по UTC/серверному времени, можно настроить pytz)
        # Утренний бриф каждый день в 08:00
        job_queue.run_daily(morning_job, time=datetime.time(hour=8, minute=0))
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("status", status))
        app.add_handler(CommandHandler("report", report_command))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.TEXT | filters.VOICE, handle_message))
        
        print("Алекс в Телеграме запущен!")
        
        # Запускаем Heartbeat сервер в отдельном потоке
        health_thread = threading.Thread(target=run_health_server, daemon=True)
        health_thread.start()
        
        app.run_polling()
