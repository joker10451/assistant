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
    Получает реальный прогноз погоды через wttr.in и дает советы по вождению.
    """
    try:
        # Используем wttr.in для получения погоды в формате JSON
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        current = data['current_condition'][0]
        temp = current['temp_C']
        desc = current['lang_ru'][0]['value'] if 'lang_ru' in current else current['weatherDesc'][0]['value']
        
        advice = f"Сейчас в г. {city} {temp}°C, {desc}. "
        
        temp_val = int(temp)
        if temp_val < 3:
            advice += "❄️ Внимание: возможен гололед. Двигайся плавно, избегай резких торможений."
        elif "rain" in desc.lower() or "дождь" in desc.lower():
            advice += "🌧️ Дорога мокрая. Увеличь дистанцию и проверь работу дворников."
        elif temp_val > 25:
            advice += "☀️ Жарко. Следи за температурой двигателя и не забывай пить воду."
        else:
            advice += "🟢 Погода благоприятная для поездки. Счастливого пути!"
            
        return advice
    except Exception as e:
        return f"Не удалось получить точный прогноз для {city}, но помни: на дороге всегда важна бдительность! (Ошибка: {e})"

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
