import requests
import urllib.parse
import logging
import time

class SkillManager:
    """Управление навыками (Skills) в стиле OpenClaw"""
    
    @staticmethod
    def get_weather(city: str = "Москва"):
        """Навык: Прогноз погоды с авто-ретритами"""
        urls = [
            f"https://wttr.in/{urllib.parse.quote(city)}?format=3",
            f"https://v2.wttr.in/{urllib.parse.quote(city)}?format=3" # Резервный сервер
        ]
        
        for url in urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    weather = response.text.strip()
                    advice = f"🌤 Погода: {weather}. "
                    
                    lower_w = weather.lower()
                    if any(x in lower_w for x in ["rain", "🌧", "дождь"]):
                        advice += "Дорога мокрая, держи дистанцию."
                    elif any(x in lower_w for x in ["snow", "❄️", "снег", "ice"]):
                        advice += "Скользко! Двигайся плавно."
                    else:
                        advice += "Условия для вождения в норме."
                    return advice
            except Exception as e:
                logging.error(f"Ошибка погоды на {url}: {e}")
                time.sleep(1)
        
        return "Не удалось достучаться до метеослужбы. Но Алекс советует: на дороге всегда будь начеку!"

    @staticmethod
    def get_part_info(part_name: str):
        """Навык: Поиск запчастей"""
        query = f"Audi A3 2006 1.6 BSE {part_name}"
        search_link = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        return f"🔍 Поиск запчасти '{part_name}': рекомендуемые бренды для Audi — VAG, Sachs, Lemförder. Подробнее тут: {search_link}"

    @staticmethod
    def generate_service_report(history_file="service_history.json"):
        """Навык: Генерация текстового отчета по истории ТО"""
        import json
        import os
        if not os.path.exists(history_file):
            return "История обслуживания пока пуста."
        
        with open(history_file, "r") as f:
            data = json.load(f)
        
        report = "📋 <b>ОТЧЕТ ПО ОБСЛУЖИВАНИЮ AUDI A3</b>\n\n"
        if "oil_change" in data:
            oc = data["oil_change"]
            report += f"🛢 <b>Замена масла:</b>\n- Дата: {oc.get('date', 'Неизвестно')}\n- Пробег: {oc.get('mileage', '0')} км\n\n"
        
        if "history" in data and data["history"]:
            report += "🛠 <b>История последних работ:</b>\n"
            for item in data["history"][-5:]: # Последние 5 записей
                report += f"- {item['date']}: {item['work']} ({item['mileage']} км)\n"
        else:
            report += "Дополнительных записей о работах не найдено."
        
        return report

    @staticmethod
    def get_proactive_briefing(city: str = "Калуга"):
        """Навык: Генерация утреннего брифинга (Погода + Состояние авто)"""
        weather = SkillManager.get_weather(city)
        
        # Загружаем ТО
        import json
        import os
        history_file = "service_history.json"
        oil_msg = ""
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                data = json.load(f)
                if "oil_change" in data:
                    # Предположим текущий пробег 150000 для примера, 
                    # в идеале нужно брать последний известный
                    last_mileage = data["oil_change"].get("mileage", 0)
                    oil_msg = f"\n🔧 Напоминание по маслу: последняя замена была на {last_mileage} км. Не забывай поглядывать на одометр!"

        brief = f"Доброе утро! ☕️\n\n{weather}{oil_msg}\n\nУдачного дня за рулем Audi!"
        return brief

    @staticmethod
    def log_car_event(event_description: str, mileage: int = 150000):
        """Навык: Сохранить любое событие по машине (поломка, замена, наблюдение)"""
        import json
        import os
        import datetime
        history_file = "service_history.json"
        
        # 1. Сохраняем в JSON (структура)
        data = {"oil_change": {"mileage": 145000, "date": "2024-01-01"}, "history": []}
        if os.path.exists(history_file):
            with open(history_file, "r") as f: data = json.load(f)
        
        now = datetime.datetime.now()
        new_event = {
            "date": now.strftime("%d.%m.%Y"),
            "work": event_description,
            "mileage": mileage
        }
        data.setdefault("history", []).append(new_event)
        
        with open(history_file, "w") as f:
            json.dump(data, f, indent=4)
        
        # 2. Сообщаем о сохранении (ChromaDB обновим через bot.py)
        return f"Запомнил событие: '{event_description}' на пробеге {mileage} км. Это сохранено в твою базу знаний."

    @staticmethod
    def remove_last_event():
        """Навык: Удалить последнюю запись из истории (если ошибся)"""
        import json
        import os
        history_file = "service_history.json"
        if not os.path.exists(history_file):
            return "История пуста, удалять нечего."
        
        with open(history_file, "r") as f:
            data = json.load(f)
        
        if "history" in data and data["history"]:
            removed = data["history"].pop()
            with open(history_file, "w") as f:
                json.dump(data, f, indent=4)
            return f"Удалил последнюю запись: '{removed['work']}' за {removed['date']}."
        else:
            return "В списке дополнительных работ нет записей для удаления."

# Описание для ИИ
OPENCLAW_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Узнать реальную погоду и получить совет по вождению",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Город (например, Калуга)"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_part_info",
            "description": "Найти информацию о запчасти или её цену",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_name": {"type": "string", "description": "Название детали"}
                },
                "required": ["part_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_car_event",
            "description": "Записать событие, поломку или замену детали в историю машины",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_description": {"type": "string", "description": "Что произошло (например, заскрипели колодки или поменял свечи)"},
                    "mileage": {"type": "integer", "description": "Текущий пробег"}
                },
                "required": ["event_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_last_event",
            "description": "Удалить последнюю добавленную запись из истории обслуживания, если пользователь совершил ошибку",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]
