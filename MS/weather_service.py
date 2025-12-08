"""
Weather Service Module
Handles OpenWeather API integration for current weather and forecasts
"""
import os
import requests
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta


class WeatherService:
    """Service for fetching weather data from OpenWeather API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Weather Service
        
        Args:
            api_key: OpenWeather API key. If not provided, reads from OPENWEATHER_API_KEY env var
        """
        self.api_key = api_key or os.getenv('OPENWEATHER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENWEATHER_API_KEY environment variable is not set")
        
        self.base_url = "https://api.openweathermap.org/data/2.5"
    
    def get_current_weather(self, city: str, units: str = "metric") -> Dict[str, Any]:
        """
        Get current weather for a city
        
        Args:
            city: City name (e.g., "Dhaka", "Helsinki")
            units: Temperature units - "metric" (Celsius), "imperial" (Fahrenheit), or "kelvin"
        
        Returns:
            Dictionary containing current weather data
        """
        url = f"{self.base_url}/weather"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": units
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                "city": data["name"],
                "country": data["sys"].get("country", ""),
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "pressure": data["main"]["pressure"],
                "description": data["weather"][0]["description"],
                "main_condition": data["weather"][0]["main"].lower(),
                "wind_speed": data.get("wind", {}).get("speed", 0),
                "wind_direction": data.get("wind", {}).get("deg"),
                "cloudiness": data.get("clouds", {}).get("all", 0),
                "visibility": data.get("visibility", 0),
                "timestamp": datetime.now().isoformat()
            }
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch weather data: {str(e)}")
    
    def get_forecast(self, city: str, days: int = 5, units: str = "metric") -> Dict[str, Any]:
        """
        Get weather forecast for a city
        
        Args:
            city: City name
            days: Number of days to forecast (up to 5 days)
            units: Temperature units
        
        Returns:
            Dictionary containing forecast data organized by date
        """
        url = f"{self.base_url}/forecast"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": units
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Organize forecast by date
            forecast_by_date = {}
            current_date = None
            
            for item in data["list"]:
                forecast_time = datetime.fromtimestamp(item["dt"])
                date_key = forecast_time.date()
                
                if date_key not in forecast_by_date:
                    forecast_by_date[date_key] = {
                        "date": date_key.isoformat(),
                        "forecasts": []
                    }
                
                forecast_by_date[date_key]["forecasts"].append({
                    "time": forecast_time.isoformat(),
                    "temperature": item["main"]["temp"],
                    "feels_like": item["main"]["feels_like"],
                    "humidity": item["main"]["humidity"],
                    "description": item["weather"][0]["description"],
                    "main_condition": item["weather"][0]["main"].lower(),
                    "wind_speed": item.get("wind", {}).get("speed", 0),
                    "cloudiness": item.get("clouds", {}).get("all", 0),
                    "precipitation_probability": item.get("pop", 0) * 100  # Convert to percentage
                })
            
            # Get daily summaries (min/max temps, most common condition)
            daily_summaries = []
            for date_key in sorted(forecast_by_date.keys())[:days]:
                day_data = forecast_by_date[date_key]
                forecasts = day_data["forecasts"]
                
                temps = [f["temperature"] for f in forecasts]
                conditions = [f["main_condition"] for f in forecasts]
                humidities = [f["humidity"] for f in forecasts]
                wind_speeds = [f["wind_speed"] for f in forecasts]
                precip_probs = [f["precipitation_probability"] for f in forecasts]
                
                # Most common condition
                most_common_condition = max(set(conditions), key=conditions.count)
                
                daily_summaries.append({
                    "date": day_data["date"],
                    "min_temp": min(temps),
                    "max_temp": max(temps),
                    "avg_humidity": sum(humidities) / len(humidities),
                    "avg_wind_speed": sum(wind_speeds) / len(wind_speeds),
                    "max_precipitation_probability": max(precip_probs),
                    "main_condition": most_common_condition,
                    "description": forecasts[0]["description"]  # Use first forecast's description
                })
            
            return {
                "city": data["city"]["name"],
                "country": data["city"].get("country", ""),
                "daily_summaries": daily_summaries,
                "detailed_forecast": forecast_by_date
            }
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch forecast data: {str(e)}")
    
    def interpret_weather(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Interpret weather data and provide human-readable insights
        
        Args:
            weather_data: Weather data from get_current_weather or forecast
        
        Returns:
            Dictionary with interpretations and recommendations
        """
        interpretations = {
            "condition": weather_data.get("main_condition", "unknown"),
            "temperature_category": self._categorize_temperature(weather_data.get("temperature", 0)),
            "humidity_category": self._categorize_humidity(weather_data.get("humidity", 0)),
            "wind_category": self._categorize_wind(weather_data.get("wind_speed", 0)),
            "recommendations": []
        }
        
        # Generate recommendations
        temp = weather_data.get("temperature", 0)
        condition = weather_data.get("main_condition", "")
        wind_speed = weather_data.get("wind_speed", 0)
        humidity = weather_data.get("humidity", 0)
        
        if "rain" in condition or "drizzle" in condition:
            interpretations["recommendations"].append("umbrella")
        if temp < 10:
            interpretations["recommendations"].append("warm_jacket")
        elif temp < 15:
            interpretations["recommendations"].append("light_jacket")
        if wind_speed > 7:  # m/s
            interpretations["recommendations"].append("windy_conditions")
        if humidity > 70:
            interpretations["recommendations"].append("high_humidity")
        
        # Outdoor activity assessment
        if "rain" in condition or "storm" in condition:
            interpretations["outdoor_activity"] = "not_recommended"
        elif temp < 5 or temp > 35:
            interpretations["outdoor_activity"] = "not_recommended"
        elif wind_speed > 10:
            interpretations["outdoor_activity"] = "caution"
        else:
            interpretations["outdoor_activity"] = "good"
        
        return interpretations
    
    def _categorize_temperature(self, temp: float) -> str:
        """Categorize temperature"""
        if temp < 0:
            return "freezing"
        elif temp < 10:
            return "cold"
        elif temp < 20:
            return "cool"
        elif temp < 25:
            return "mild"
        elif temp < 30:
            return "warm"
        else:
            return "hot"
    
    def _categorize_humidity(self, humidity: float) -> str:
        """Categorize humidity"""
        if humidity < 30:
            return "dry"
        elif humidity < 50:
            return "comfortable"
        elif humidity < 70:
            return "moderate"
        else:
            return "humid"
    
    def _categorize_wind(self, wind_speed: float) -> str:
        """Categorize wind speed"""
        if wind_speed < 3:
            return "calm"
        elif wind_speed < 7:
            return "light"
        elif wind_speed < 12:
            return "moderate"
        else:
            return "strong"

