import requests
import urllib.parse
import logging
import time

# База артикулов для Audi A3 (1.6 BSE)
VAG_PARTS = {
    "масло": {"vag": "G 052 167 M4", "analog": "Castrol EDGE 5W-40", "desc": "502.00/505.00"},
    "масляный фильтр": {"vag": "06A 115 561 B", "analog": "MANN-FILTER W 719/30", "desc": "Стандарт для 1.6 BSE"},
    "воздушный фильтр": {"vag": "1K0 129 620 D", "analog": "MANN-FILTER C 30 139", "desc": "Прямоугольный"},
    "свечи": {"vag": "101 000 033 AA", "analog": "NGK BKUR6ET-10", "desc": "3-контактные, оригинал для BSE"},
    "салонный фильтр": {"vag": "1K1 819 653 B", "analog": "MANN-FILTER CUK 2939", "desc": "Угольный"},
    "грм": {"vag": "06A 198 119", "analog": "CONTITECH CT908K1", "desc": "Ремкомплект ГРМ с роликом"},
    "помпа": {"vag": "06B 121 011 H", "analog": "HEPU P547", "desc": "Водяной насос"}
}

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

    @staticmethod
    def get_part_numbers(part_name: str):
        """Навык: Получить артикул запчасти и аналоги для Audi A3 1.6 BSE"""
        query = part_name.lower()
        found_key = next((k for k in VAG_PARTS if k in query or query in k), None)
        
        if found_key:
            p = VAG_PARTS[found_key]
            res = (f"🛠 <b>Подбор для {found_key}:</b>\n"
                   f"🔹 Оригинал VAG: <code>{p['vag']}</code>\n"
                   f"🔹 Надежный аналог: <code>{p['analog']}</code>\n"
                   f"ℹ️ Примечание: {p['desc']}")
            return res
        else:
            return f"К сожалению, у меня нет артикула для '{part_name}' в базе BSE. Могу поискать общую информацию в сети."

    @staticmethod
    def sos_help(situation_type: str = "авария"):
        """Навык: Инструкции при ДТП или поломке (Crash Assistant)"""
        if "авари" in situation_type.lower() or "дтп" in situation_type.lower():
            res = (
                "🚨 <b>АЛЕКС: РЕЖИМ ЭКСТРЕННОЙ ПОМОЩИ (ДТП)</b>\n\n"
                "1. <b>Безопасность:</b> Остановитесь, включите аварийку, выставьте знак (15м в городе, 30м на трассе).\n"
                "2. <b>Люди:</b> Если есть пострадавшие — немедленно звоните <b>112</b>!\n"
                "3. <b>Фиксация:</b> Сделайте фото положения машин с 4-х сторон, следов торможения и повреждений.\n"
                "4. <b>Европротокол:</b> Если нет пострадавших, участвуют 2 машины и ущерб до 400к — оформляйте без ГИБДД.\n"
                "5. <b>Документы:</b> Сфотографируйте полис ОСАГО и СТС другого участника.\n\n"
                "<i>Я готов помочь с анализом фото повреждений или прислать контакты эвакуатора. Ты в порядке?</i>"
            )
        else:
            res = (
                "⚠️ <b>ПОЛОМКА В ПУТИ</b>\n\n"
                "1. Прижмитесь к обочине и включите аварийку.\n"
                "2. Выставьте знак аварийной остановки.\n"
                "3. Проверьте: нет ли течи жидкостей под капотом.\n"
                "4. <b>Телефон эвакуатора:</b> 8 (800) 222-33-44 (пример).\n\n"
                "Опишите симптомы, и я попробую провести диагностику по мануалу."
            )
        return res

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
    },
    {
        "type": "function",
        "function": {
            "name": "get_part_numbers",
            "description": "Получить оригинальные артикулы (VAG) и проверенные аналоги запчастей для двигателя 1.6 BSE Audi A3",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_name": {"type": "string", "description": "Название запчасти (например, свечи, фильтр)"}
                },
                "required": ["part_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sos_help",
            "description": "Получить экстренные инструкции при ДТП (аварии) или технической поломке в пути",
            "parameters": {
                "type": "object",
                "properties": {
                    "situation_type": {"type": "string", "description": "Тип ситуации: 'авария' или 'поломка'"}
                }
            }
        }
    }
]
