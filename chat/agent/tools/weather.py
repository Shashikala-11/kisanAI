"""
Real-time weather via OpenWeatherMap API.
Enriched with farming-relevant context (sowing/irrigation advice based on conditions).
"""
import os
import requests
from langchain_core.tools import tool


def get_weather(location: str) -> dict:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {"error": "OPENWEATHER_API_KEY not set"}
    try:
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": location, "appid": api_key, "units": "metric"},
            timeout=6,
        )
        resp.raise_for_status()
        d = resp.json()
        return {
            "location": d.get("name", location),
            "temp_c": d["main"]["temp"],
            "feels_like": d["main"]["feels_like"],
            "humidity": d["main"]["humidity"],
            "description": d["weather"][0]["description"],
            "wind_speed": d["wind"]["speed"],
            "rain_1h": d.get("rain", {}).get("1h", 0),
            "clouds": d["clouds"]["all"],
        }
    except requests.exceptions.HTTPError as e:
        return {"error": f"Location '{location}' not found. Try a city name like 'Ludhiana'."}
    except Exception as e:
        return {"error": str(e)}


@tool
def weather_tool(location: str) -> str:
    """
    Get current real-time weather for a farming location in Punjab.
    Use this for questions about weather, rain, temperature, irrigation needs, or sowing conditions.
    Provide city name e.g. 'Ludhiana', 'Amritsar', 'Patiala', 'Bathinda'.
    """
    d = get_weather(location)
    if "error" in d:
        return f"Weather error: {d['error']}"

    # Farming context hints for the LLM
    hints = []
    if d["rain_1h"] > 0:
        hints.append(f"rainfall of {d['rain_1h']}mm in last hour — skip irrigation today")
    if d["humidity"] > 80:
        hints.append("high humidity — watch for fungal diseases")
    if d["temp_c"] > 40:
        hints.append("extreme heat — avoid spraying pesticides, irrigate in evening")
    if d["wind_speed"] > 5:
        hints.append("windy — avoid spraying today")

    result = (
        f"Weather in {d['location']}: {d['description']}, "
        f"Temp {d['temp_c']}°C (feels {d['feels_like']}°C), "
        f"Humidity {d['humidity']}%, Wind {d['wind_speed']} m/s, "
        f"Cloud cover {d['clouds']}%"
    )
    if hints:
        result += f"\nFarming notes: {'; '.join(hints)}"
    return result
