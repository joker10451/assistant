import requests
import os
import urllib.parse

def get_part_price(part_name: str):
    """
    Ищет примерную цену запчасти и дает ссылку на поиск.
    """
    query = f"купить {part_name} для Audi A3 2006 1.6 BSE"
    link = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    return f"Я нашел информацию по запросу '{part_name}'. Цены можно посмотреть здесь: {link}. Для Audi A3 2006 (1.6 BSE) рекомендую выбирать бренды Sachs, Lemforder или VAG."

def get_weather_advice(city: str = "Москва"):
    """
    Получает реальный прогноз погоды через wttr.in (простой формат) и дает советы.
    """
    try:
        # Используем более легкий формат 3 (одна строка)
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=3"
        response = requests.get(url, timeout=5)
        weather_text = response.text.strip()
        
        advice = f"Прогноз: {weather_text}. "
        
        # Простая проверка на опасные условия в тексте
        wttr_lower = weather_text.lower()
        if any(word in wttr_lower for word in ["snow", "ice", "frost", "снег", "лед", "заморозки"]):
            advice += "❄️ Внимание: скользко! Двигайся плавно."
        elif any(word in wttr_lower for word in ["rain", "drizzle", "дождь", "морось"]):
            advice += "🌧️ Видимость снижена, дорога мокрая. Соблюдай дистанцию."
        else:
            advice += "🟢 Условия для вождения хорошие."
            
        return advice
    except Exception as e:
        return f"Пока не могу связаться с метеослужбой, но будь бдителен! (Ошибка связи)"

# Список инструментов для DeepSeek API
tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "get_part_price",
            "description": "Поиск цены и информации о запчасти для Audi A3 2006",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_name": {"type": "string", "description": "Название запчасти (например, масляный фильтр)"}
                },
                "required": ["part_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_advice",
            "description": "Получить совет по вождению исходя из погоды",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Город для прогноза"}
                }
            }
        }
    }
]
