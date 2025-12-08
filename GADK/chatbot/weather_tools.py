"""Weather tools for the Personal Weather Assistant using OpenWeather API."""

import os
import requests
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
BASE_URL = "http://api.openweathermap.org/data/2.5"

# Thread-local storage for user_id
_thread_local = threading.local()


def set_user_id(user_id: str):
    """Set the current user_id for this thread."""
    _thread_local.user_id = user_id


def get_user_id() -> Optional[str]:
    """Get the current user_id for this thread."""
    return getattr(_thread_local, 'user_id', None)


def get_current_weather(city: str, tool_context=None) -> Dict[str, Any]:
    """Get current weather data for a specific city.
    
    Args:
        city: The name of the city (e.g., "Dhaka", "Helsinki", "Tampere").
        tool_context: Optional tool context (not used but required by ADK).
    
    Returns:
        A dictionary containing current weather information including:
        - temperature (Celsius)
        - humidity (%)
        - weather description
        - wind speed (m/s)
        - feels_like temperature
        - city name
        - timestamp
    """
    if not OPENWEATHER_API_KEY:
        return {
            "error": "OpenWeather API key is not configured. Please set OPENWEATHER_API_KEY in your .env file."
        }
    
    try:
        url = f"{BASE_URL}/weather"
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"  # Get temperature in Celsius
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "city": data["name"],
            "country": data["sys"].get("country", ""),
            "temperature": round(data["main"]["temp"], 1),
            "feels_like": round(data["main"]["feels_like"], 1),
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "weather_description": data["weather"][0]["description"],
            "weather_main": data["weather"][0]["main"],
            "wind_speed": round(data["wind"].get("speed", 0), 1),
            "wind_direction": data["wind"].get("deg"),
            "cloudiness": data["clouds"].get("all", 0),
            "visibility": data.get("visibility", 0) / 1000 if data.get("visibility") else None,  # Convert to km
            "timestamp": datetime.fromtimestamp(data["dt"]).isoformat(),
            "sunrise": datetime.fromtimestamp(data["sys"]["sunrise"]).strftime("%H:%M"),
            "sunset": datetime.fromtimestamp(data["sys"]["sunset"]).strftime("%H:%M"),
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Failed to fetch weather data: {str(e)}"
        }
    except KeyError as e:
        return {
            "error": f"Unexpected API response format: {str(e)}"
        }
    except Exception as e:
        return {
            "error": f"An error occurred: {str(e)}"
        }


def get_weather_forecast(city: str, days: int = 5, tool_context=None) -> Dict[str, Any]:
    """Get weather forecast for a specific city.
    
    Args:
        city: The name of the city (e.g., "Dhaka", "Helsinki", "Tampere").
        days: Number of days to forecast (1-5, default is 5).
        tool_context: Optional tool context (not used but required by ADK).
    
    Returns:
        A dictionary containing forecast information with:
        - city name
        - list of forecast entries for each day/time period
        - Each entry includes temperature, humidity, weather description, wind, etc.
    """
    if not OPENWEATHER_API_KEY:
        return {
            "error": "OpenWeather API key is not configured. Please set OPENWEATHER_API_KEY in your .env file."
        }
    
    try:
        # Limit days to 5 (OpenWeather free tier limit)
        days = min(max(1, days), 5)
        
        url = f"{BASE_URL}/forecast"
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        forecast_list = []
        current_date = None
        daily_forecast = {}
        
        # Group forecasts by day
        for item in data["list"]:
            forecast_time = datetime.fromtimestamp(item["dt"])
            date_key = forecast_time.date()
            
            if date_key not in daily_forecast:
                daily_forecast[date_key] = {
                    "date": date_key.isoformat(),
                    "day_name": forecast_time.strftime("%A"),
                    "forecasts": []
                }
            
            forecast_entry = {
                "time": forecast_time.strftime("%H:%M"),
                "temperature": round(item["main"]["temp"], 1),
                "feels_like": round(item["main"]["feels_like"], 1),
                "humidity": item["main"]["humidity"],
                "weather_description": item["weather"][0]["description"],
                "weather_main": item["weather"][0]["main"],
                "wind_speed": round(item["wind"].get("speed", 0), 1),
                "cloudiness": item["clouds"].get("all", 0),
                "precipitation_probability": item.get("pop", 0) * 100,  # Convert to percentage
            }
            
            daily_forecast[date_key]["forecasts"].append(forecast_entry)
        
        # Convert to list and limit to requested days
        forecast_list = list(daily_forecast.values())[:days]
        
        # Calculate daily summaries (min/max temp, etc.)
        for day_forecast in forecast_list:
            temps = [f["temperature"] for f in day_forecast["forecasts"]]
            day_forecast["min_temp"] = min(temps)
            day_forecast["max_temp"] = max(temps)
            day_forecast["avg_humidity"] = round(
                sum(f["humidity"] for f in day_forecast["forecasts"]) / len(day_forecast["forecasts"]), 1
            )
            # Get most common weather condition
            weather_conditions = [f["weather_main"] for f in day_forecast["forecasts"]]
            day_forecast["primary_weather"] = max(set(weather_conditions), key=weather_conditions.count)
            # Check if rain is expected
            day_forecast["rain_expected"] = any(
                f["precipitation_probability"] > 30 or f["weather_main"].lower() in ["rain", "drizzle", "thunderstorm"]
                for f in day_forecast["forecasts"]
            )
        
        return {
            "city": data["city"]["name"],
            "country": data["city"].get("country", ""),
            "forecast_days": len(forecast_list),
            "forecast": forecast_list
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Failed to fetch forecast data: {str(e)}"
        }
    except KeyError as e:
        return {
            "error": f"Unexpected API response format: {str(e)}"
        }
    except Exception as e:
        return {
            "error": f"An error occurred: {str(e)}"
        }

