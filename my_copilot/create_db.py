import pypdf
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import os

# НАСТРОЙКИ
MANUAL_FILE = "manual.pdf"  # <-- Имя вашего файла с инструкцией Audi
CHROMA_PATH = "chroma_db"   # Папка, где сохранится база знаний

from dotenv import load_dotenv, find_dotenv

# 0. Загрузка переменных
load_dotenv(find_dotenv())

# ПРИНУДИТЕЛЬНЫЙ ХАК: Если ваш токен в .env или в системе невалиден (ошибка 401),
# мы удаляем его из текущего процесса, чтобы библиотеки работали в анонимном режиме.
# Модели Whisper и Sentence-Transformers — публичные, им токен не обязателен.
if "HF_TOKEN" in os.environ:
    del os.environ["HF_TOKEN"]
if "HUGGINGFACE_HUB_TOKEN" in os.environ:
    del os.environ["HUGGINGFACE_HUB_TOKEN"]

# 1. Инициализация модели (скачается при первом запуске ~100Мб)
print("Загрузка модели для поиска смысловых связей...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# 2. Чтение PDF
print(f"Читаю файл {MANUAL_FILE}...")
if not os.path.exists(MANUAL_FILE):
    print(f"❌ Ошибка: Файл {MANUAL_FILE} не найден! Положите его в эту же папку.")
    exit()

reader = pypdf.PdfReader(MANUAL_FILE)
text_data = ""

for page in reader.pages:
    text_data += page.extract_text() + "\n"

# 3. Разбивка на куски (Chunks)
chunks = []
chunk_size = 1000
overlap = 100

for i in range(0, len(text_data), chunk_size - overlap):
    chunk = text_data[i:i + chunk_size]
    chunks.append(chunk)

print(f"Текст разбит на {len(chunks)} кусочков.")

# 4. Создание базы данных ChromaDB
print("Создаю базу данных (это займет пару минут)...")
client = chromadb.PersistentClient(path=CHROMA_PATH)

# Вместо очистки через delete(where={}), просто удаляем и создаем коллекцию заново
try:
    client.delete_collection(name="audi_manual")
except Exception:
    pass # Если коллекции еще нет

collection = client.create_collection(name="audi_manual")

# Добавление данных
ids = [str(i) for i in range(len(chunks))]
# Разбиваем на батчи, если данных много (Chroma любит порции до 40000)
collection.add(
    documents=chunks,
    ids=ids,
    embeddings=[embedding_model.encode(chunk).tolist() for chunk in chunks]
)

print("✅ Готово! База знаний создана в папке 'chroma_db'. Теперь можно запускать app.py")
