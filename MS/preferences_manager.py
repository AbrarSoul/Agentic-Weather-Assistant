"""
Preference Learning System
Stores and retrieves user preferences from conversations
"""
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime


class PreferencesManager:
    """Manages user preferences learned from conversations"""
    
    def __init__(self, storage_file: str = "user_preferences.json"):
        """
        Initialize the Preferences Manager
        
        Args:
            storage_file: Path to JSON file storing preferences
        """
        self.storage_file = storage_file
        self.preferences = self._load_preferences()
    
    def _load_preferences(self) -> Dict[str, Any]:
        """Load preferences from storage file"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._default_preferences()
        return self._default_preferences()
    
    def _default_preferences(self) -> Dict[str, Any]:
        """Return default preferences structure"""
        return {
            "temperature_preferences": {
                "prefers_warm": None,
                "prefers_cool": None,
                "comfortable_range": {"min": None, "max": None}
            },
            "weather_conditions": {
                "dislikes_cold": False,
                "dislikes_wind": False,
                "dislikes_rain": False,
                "prefers_sunny": False
            },
            "activity_preferences": {
                "prefers_indoor": False,
                "prefers_outdoor": None
            },
            "conversation_history": [],
            "last_updated": None
        }
    
    def _save_preferences(self):
        """Save preferences to storage file"""
        self.preferences["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.preferences, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Could not save preferences: {e}")
    
    def learn_from_conversation(self, user_message: str, weather_data: Optional[Dict] = None, 
                                response: Optional[str] = None):
        """
        Learn from a conversation turn
        
        Args:
            user_message: User's message
            weather_data: Weather data that was used (if any)
            response: Assistant's response
        """
        # Store conversation history
        self.preferences["conversation_history"].append({
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "response": response
        })
        
        # Keep only last 50 conversations to avoid file bloat
        if len(self.preferences["conversation_history"]) > 50:
            self.preferences["conversation_history"] = \
                self.preferences["conversation_history"][-50:]
        
        # Extract preferences from user message (simple keyword-based learning)
        message_lower = user_message.lower()
        
        # Temperature preferences
        if any(word in message_lower for word in ["cold", "freezing", "too cold", "hate cold"]):
            self.preferences["weather_conditions"]["dislikes_cold"] = True
        if any(word in message_lower for word in ["warm", "love warm", "prefer warm", "like warm"]):
            self.preferences["temperature_preferences"]["prefers_warm"] = True
        if any(word in message_lower for word in ["cool", "prefer cool", "like cool"]):
            self.preferences["temperature_preferences"]["prefers_cool"] = True
        
        # Wind preferences
        if any(word in message_lower for word in ["windy", "hate wind", "dislike wind", "too windy"]):
            self.preferences["weather_conditions"]["dislikes_wind"] = True
        
        # Rain preferences
        if any(word in message_lower for word in ["hate rain", "dislike rain", "don't like rain"]):
            self.preferences["weather_conditions"]["dislikes_rain"] = True
        
        # Activity preferences
        if any(word in message_lower for word in ["indoor", "stay inside", "inside activities"]):
            self.preferences["activity_preferences"]["prefers_indoor"] = True
        if any(word in message_lower for word in ["outdoor", "outside", "outdoors"]):
            self.preferences["activity_preferences"]["prefers_outdoor"] = True
        
        # Sunny preferences
        if any(word in message_lower for word in ["sunny", "love sun", "prefer sunny"]):
            self.preferences["weather_conditions"]["prefers_sunny"] = True
        
        # Learn from weather data if provided (e.g., if user asked about cold weather and we provided it)
        if weather_data:
            temp = weather_data.get("temperature", 0)
            if temp < 10 and "cold" in message_lower:
                self.preferences["weather_conditions"]["dislikes_cold"] = True
        
        self._save_preferences()
    
    def get_preferences_summary(self) -> str:
        """
        Get a human-readable summary of user preferences
        
        Returns:
            String summary of preferences
        """
        prefs = self.preferences
        summary_parts = []
        
        # Temperature preferences
        if prefs["temperature_preferences"]["prefers_warm"]:
            summary_parts.append("prefers warm weather")
        if prefs["temperature_preferences"]["prefers_cool"]:
            summary_parts.append("prefers cool weather")
        
        # Weather condition dislikes
        if prefs["weather_conditions"]["dislikes_cold"]:
            summary_parts.append("dislikes cold weather")
        if prefs["weather_conditions"]["dislikes_wind"]:
            summary_parts.append("dislikes windy conditions")
        if prefs["weather_conditions"]["dislikes_rain"]:
            summary_parts.append("dislikes rain")
        if prefs["weather_conditions"]["prefers_sunny"]:
            summary_parts.append("prefers sunny weather")
        
        # Activity preferences
        if prefs["activity_preferences"]["prefers_indoor"]:
            summary_parts.append("prefers indoor activities")
        if prefs["activity_preferences"]["prefers_outdoor"]:
            summary_parts.append("prefers outdoor activities")
        
        if summary_parts:
            return ", ".join(summary_parts)
        return "no specific preferences learned yet"
    
    def get_preferences(self) -> Dict[str, Any]:
        """Get the full preferences dictionary"""
        return self.preferences.copy()
    
    def apply_preferences_to_recommendation(self, weather_data: Dict[str, Any], 
                                           base_recommendations: List[str]) -> Dict[str, Any]:
        """
        Apply user preferences to weather recommendations
        
        Args:
            weather_data: Current weather data
            base_recommendations: Base recommendations from weather service
        
        Returns:
            Enhanced recommendations with preference-based suggestions
        """
        prefs = self.preferences
        enhanced_recommendations = base_recommendations.copy()
        preference_notes = []
        
        temp = weather_data.get("temperature", 0)
        condition = weather_data.get("main_condition", "")
        wind_speed = weather_data.get("wind_speed", 0)
        
        # Apply preference-based recommendations
        if prefs["weather_conditions"]["dislikes_cold"] and temp < 15:
            enhanced_recommendations.append("extra_warm_clothing")
            preference_notes.append("You mentioned disliking cold weather, so consider extra warm clothing.")
        
        if prefs["weather_conditions"]["dislikes_wind"] and wind_speed > 5:
            enhanced_recommendations.append("wind_protection")
            preference_notes.append("Since you don't like windy conditions, you might want to stay indoors or seek shelter.")
        
        if prefs["weather_conditions"]["dislikes_rain"] and "rain" in condition:
            enhanced_recommendations.append("avoid_outdoor")
            preference_notes.append("Given your dislike for rain, consider indoor activities today.")
        
        if prefs["activity_preferences"]["prefers_indoor"]:
            preference_notes.append("Based on your preference for indoor activities, here are some indoor suggestions.")
        
        return {
            "recommendations": enhanced_recommendations,
            "preference_notes": preference_notes,
            "outdoor_activity_suitable": not (
                (prefs["weather_conditions"]["dislikes_cold"] and temp < 10) or
                (prefs["weather_conditions"]["dislikes_wind"] and wind_speed > 7) or
                (prefs["weather_conditions"]["dislikes_rain"] and "rain" in condition)
            )
        }

