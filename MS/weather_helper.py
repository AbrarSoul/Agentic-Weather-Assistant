"""
Weather Helper Module
Pre-processes weather queries and fetches data before sending to agent
"""
import re
from typing import Optional, Dict, Any, Tuple
from weather_service import WeatherService
from preferences_manager import PreferencesManager


class WeatherHelper:
    """Helper class to process weather queries and fetch data"""
    
    def __init__(self, weather_service: WeatherService, preferences_manager: PreferencesManager):
        self.weather_service = weather_service
        self.preferences_manager = preferences_manager
        
        # Common city names that might appear in queries
        self.city_patterns = [
            r'\b(dhaka|helsinki|tampere|tampere|stockholm|copenhagen|oslo|reykjavik)\b',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'  # Capitalized city names
        ]
    
    def extract_city_from_query(self, query: str) -> Optional[str]:
        """Extract city name from user query"""
        query_lower = query.lower()
        
        # Check for common cities
        common_cities = {
            'dhaka': 'Dhaka',
            'helsinki': 'Helsinki',
            'tampere': 'Tampere',
            'stockholm': 'Stockholm',
            'copenhagen': 'Copenhagen',
            'oslo': 'Oslo',
            'reykjavik': 'Reykjavik',
            'oulu': 'Oulu'
        }
        
        for city_key, city_name in common_cities.items():
            if city_key in query_lower:
                return city_name
        
        # Try to extract capitalized words (potential city names)
        # Look for patterns like "in [City]", "at [City]", "[City] today", or "[City] on [day]"
        patterns = [
            r'in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(today|tomorrow|this week|on\s+\w+)',
            r'weather\s+(?:in\s+|at\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                potential_city = match.group(1)
                # Basic validation - if it looks like a city name
                if len(potential_city.split()) <= 3:  # Most city names are 1-3 words
                    return potential_city
        
        return None
    
    def is_weather_query(self, query: str) -> bool:
        """Check if query is weather-related"""
        weather_keywords = [
            'weather', 'temperature', 'temp', 'humidity', 'forecast',
            'rain', 'rainy', 'sunny', 'wind', 'windy', 'snow', 'cloud',
            'umbrella', 'jacket', 'outdoor', 'outdoors', 'indoor', 'indoors',
            'today', 'tomorrow', 'week', 'sunday', 'monday', 'tuesday',
            'wednesday', 'thursday', 'friday', 'saturday'
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in weather_keywords)
    
    def process_weather_query(self, query: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Process weather query and fetch relevant data
        
        Returns:
            Tuple of (enhanced_query, weather_data)
            enhanced_query: Query with weather data context added
            weather_data: Fetched weather data (if any)
        """
        if not self.is_weather_query(query):
            return query, None
        
        city = self.extract_city_from_query(query)
        if not city:
            # No city found, return original query
            return query, None
        
        query_lower = query.lower()
        weather_data = None
        enhanced_query = query
        
        try:
            # Check if it's a forecast query
            is_forecast = any(word in query_lower for word in ['tomorrow', 'forecast', 'week', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'next'])
            
            if is_forecast:
                # Get forecast
                days = 5
                if 'tomorrow' in query_lower:
                    days = 2
                elif 'week' in query_lower:
                    days = 5
                
                forecast_data = self.weather_service.get_forecast(city, days)
                weather_data = forecast_data
                
                # Create context for agent
                daily_summaries = forecast_data.get('daily_summaries', [])
                context = f"\n\n[WEATHER DATA FOR {city.upper()}]\n"
                context += "Forecast Summary:\n"
                for day in daily_summaries[:days]:
                    context += f"- {day['date']}: {day['main_condition']}, {day['min_temp']:.1f}°C to {day['max_temp']:.1f}°C"
                    if day.get('max_precipitation_probability', 0) > 30:
                        context += f", {day['max_precipitation_probability']:.0f}% chance of precipitation"
                    context += "\n"
                
                enhanced_query = query + context
            else:
                # Get current weather
                current_data = self.weather_service.get_current_weather(city)
                interpretation = self.weather_service.interpret_weather(current_data)
                
                # Apply preferences
                prefs_rec = self.preferences_manager.apply_preferences_to_recommendation(
                    current_data, interpretation["recommendations"]
                )
                
                weather_data = {
                    'current': current_data,
                    'interpretation': interpretation,
                    'preferences': prefs_rec
                }
                
                # Create context for agent
                context = f"\n\n[WEATHER DATA FOR {city.upper()}]\n"
                context += f"Current Conditions:\n"
                context += f"- Temperature: {current_data['temperature']:.1f}°C (feels like {current_data['feels_like']:.1f}°C)\n"
                context += f"- Condition: {current_data['description']} ({current_data['main_condition']})\n"
                context += f"- Humidity: {current_data['humidity']}%\n"
                context += f"- Wind Speed: {current_data['wind_speed']:.1f} m/s\n"
                context += f"- Recommendations: {', '.join(prefs_rec['recommendations'])}\n"
                if prefs_rec.get('preference_notes'):
                    context += f"- Note: {' '.join(prefs_rec['preference_notes'])}\n"
                
                enhanced_query = query + context
            
            # Add user preferences context
            prefs_summary = self.preferences_manager.get_preferences_summary()
            if prefs_summary != "no specific preferences learned yet":
                enhanced_query += f"\n[USER PREFERENCES: {prefs_summary}]\n"
            
        except Exception as e:
            # If weather fetch fails, return original query with error context
            enhanced_query = query + f"\n\n[Note: Could not fetch weather data: {str(e)}. Please provide a helpful response anyway.]\n"
        
        return enhanced_query, weather_data

