"""User preference learning and storage for the Personal Weather Assistant."""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

# Directory to store user preferences
PREFERENCES_DIR = Path("user_preferences")
PREFERENCES_DIR.mkdir(exist_ok=True)


def get_preferences_file(user_id: str) -> Path:
    """Get the path to the preferences file for a user."""
    return PREFERENCES_DIR / f"{user_id}_preferences.json"


def load_user_preferences(user_id: str) -> Dict[str, Any]:
    """Load user preferences from storage.
    
    Args:
        user_id: The unique identifier for the user.
    
    Returns:
        A dictionary containing user preferences with default values if none exist.
    """
    prefs_file = get_preferences_file(user_id)
    
    if not prefs_file.exists():
        return get_default_preferences()
    
    try:
        with open(prefs_file, 'r', encoding='utf-8') as f:
            preferences = json.load(f)
        # Merge with defaults to ensure all keys exist
        default_prefs = get_default_preferences()
        default_prefs.update(preferences)
        return default_prefs
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading preferences for user {user_id}: {e}")
        return get_default_preferences()


def save_user_preferences(user_id: str, preferences: Dict[str, Any]) -> None:
    """Save user preferences to storage.
    
    Args:
        user_id: The unique identifier for the user.
        preferences: Dictionary containing user preferences to save.
    """
    from datetime import datetime
    
    prefs_file = get_preferences_file(user_id)
    
    # Always update the last_updated timestamp when saving
    preferences["last_updated"] = datetime.now().isoformat()
    
    try:
        with open(prefs_file, 'w', encoding='utf-8') as f:
            json.dump(preferences, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving preferences for user {user_id}: {e}")


def get_default_preferences() -> Dict[str, Any]:
    """Get default user preferences.
    
    Returns:
        A dictionary with default preference values.
    """
    return {
        "temperature_preferences": {
            "dislikes_cold": False,  # User dislikes cold weather
            "dislikes_heat": False,  # User dislikes hot weather
            "preferred_temp_range": None,  # [min, max] in Celsius
            "comfortable_min": 15,  # Minimum comfortable temperature
            "comfortable_max": 25,  # Maximum comfortable temperature
        },
        "weather_preferences": {
            "dislikes_rain": False,  # User dislikes rainy weather
            "dislikes_wind": False,  # User dislikes windy weather
            "prefers_sunny": False,  # User prefers sunny weather
            "prefers_indoor": False,  # User prefers indoor activities
        },
        "activity_preferences": {
            "outdoor_activities": True,  # User enjoys outdoor activities
            "sensitive_to_weather": False,  # User is sensitive to weather changes
        },
        "conversation_history": [],  # Store key insights from conversations
        "learned_from_conversations": 0,  # Count of preference updates
    }


def update_preferences_from_conversation(
    user_id: str,
    conversation_insights: Dict[str, Any]
) -> Dict[str, Any]:
    """Update user preferences based on conversation insights.
    
    This function analyzes conversation insights and updates user preferences.
    It's called by the agent after analyzing user responses.
    
    Args:
        user_id: The unique identifier for the user.
        conversation_insights: Dictionary containing insights extracted from conversation.
            Expected keys:
            - dislikes_cold: bool
            - dislikes_heat: bool
            - dislikes_rain: bool
            - dislikes_wind: bool
            - prefers_sunny: bool
            - prefers_indoor: bool
            - comfortable_temp_range: [min, max] or None
            - outdoor_activities: bool
            - sensitive_to_weather: bool
    
    Returns:
        Updated preferences dictionary.
    """
    preferences = load_user_preferences(user_id)
    
    # Update temperature preferences
    if "dislikes_cold" in conversation_insights:
        preferences["temperature_preferences"]["dislikes_cold"] = conversation_insights["dislikes_cold"]
    if "dislikes_heat" in conversation_insights:
        preferences["temperature_preferences"]["dislikes_heat"] = conversation_insights["dislikes_heat"]
    if "comfortable_temp_range" in conversation_insights and conversation_insights["comfortable_temp_range"]:
        prefs = preferences["temperature_preferences"]
        new_range = conversation_insights["comfortable_temp_range"]
        if isinstance(new_range, list) and len(new_range) == 2:
            prefs["comfortable_min"] = min(new_range)
            prefs["comfortable_max"] = max(new_range)
            prefs["preferred_temp_range"] = new_range
    
    # Update weather preferences
    if "dislikes_rain" in conversation_insights:
        preferences["weather_preferences"]["dislikes_rain"] = conversation_insights["dislikes_rain"]
    if "dislikes_wind" in conversation_insights:
        preferences["weather_preferences"]["dislikes_wind"] = conversation_insights["dislikes_wind"]
    if "prefers_sunny" in conversation_insights:
        preferences["weather_preferences"]["prefers_sunny"] = conversation_insights["prefers_sunny"]
    if "prefers_indoor" in conversation_insights:
        preferences["weather_preferences"]["prefers_indoor"] = conversation_insights["prefers_indoor"]
    
    # Update activity preferences
    if "outdoor_activities" in conversation_insights:
        preferences["activity_preferences"]["outdoor_activities"] = conversation_insights["outdoor_activities"]
    if "sensitive_to_weather" in conversation_insights:
        preferences["activity_preferences"]["sensitive_to_weather"] = conversation_insights["sensitive_to_weather"]
    
    # Store conversation insight
    if "insight_text" in conversation_insights:
        preferences["conversation_history"].append({
            "insight": conversation_insights["insight_text"],
            "timestamp": conversation_insights.get("timestamp", "")
        })
        # Keep only last 50 insights
        preferences["conversation_history"] = preferences["conversation_history"][-50:]
    
    preferences["learned_from_conversations"] += 1
    
    # Save updated preferences
    save_user_preferences(user_id, preferences)
    
    return preferences


def learn_from_conversation(
    user_id: str,
    user_message: str,
    response: Optional[str] = None,
    weather_data: Optional[Dict[str, Any]] = None
) -> None:
    """Automatically learn preferences from a conversation using keyword-based extraction.
    
    This function analyzes user messages for preference keywords and updates preferences accordingly.
    It also saves the conversation to history.
    
    Args:
        user_id: The unique identifier for the user.
        user_message: The user's message.
        response: The assistant's response (optional).
        weather_data: Weather data that was used (optional).
    """
    from datetime import datetime
    
    preferences = load_user_preferences(user_id)
    message_lower = user_message.lower()
    learned_something = False
    
    # Store conversation history
    conversation_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_message": user_message,
    }
    if response:
        conversation_entry["response"] = response
    
    preferences["conversation_history"].append(conversation_entry)
    # Keep only last 50 conversations
    if len(preferences["conversation_history"]) > 50:
        preferences["conversation_history"] = preferences["conversation_history"][-50:]
    
    # Extract preferences from user message (keyword-based learning)
    # Temperature preferences - cold
    if any(word in message_lower for word in ["cold", "freezing", "too cold", "hate cold", "dislike cold", "don't like cold"]):
        if not preferences["temperature_preferences"]["dislikes_cold"]:
            preferences["temperature_preferences"]["dislikes_cold"] = True
            learned_something = True
    
    # Temperature preferences - heat
    if any(word in message_lower for word in ["hot", "too hot", "hate hot", "dislike hot", "don't like hot", "heat"]):
        if not preferences["temperature_preferences"]["dislikes_heat"]:
            preferences["temperature_preferences"]["dislikes_heat"] = True
            learned_something = True
    
    # Temperature preferences - warm
    if any(word in message_lower for word in ["warm", "love warm", "prefer warm", "like warm"]):
        if preferences["temperature_preferences"].get("prefers_warm") is None:
            preferences["temperature_preferences"]["prefers_warm"] = True
            learned_something = True
    
    # Temperature preferences - cool
    if any(word in message_lower for word in ["cool", "prefer cool", "like cool"]):
        if preferences["temperature_preferences"].get("prefers_cool") is None:
            preferences["temperature_preferences"]["prefers_cool"] = True
            learned_something = True
    
    # Wind preferences
    if any(word in message_lower for word in ["windy", "hate wind", "dislike wind", "too windy", "don't like wind"]):
        if not preferences["weather_preferences"]["dislikes_wind"]:
            preferences["weather_preferences"]["dislikes_wind"] = True
            learned_something = True
    
    # Rain preferences
    if any(word in message_lower for word in ["hate rain", "dislike rain", "don't like rain", "hate rainy", "dislike rainy"]):
        if not preferences["weather_preferences"]["dislikes_rain"]:
            preferences["weather_preferences"]["dislikes_rain"] = True
            learned_something = True
    
    # Activity preferences - indoor
    if any(word in message_lower for word in ["indoor", "stay inside", "inside activities", "prefer indoor", "like indoor"]):
        if not preferences["activity_preferences"]["prefers_indoor"]:
            preferences["activity_preferences"]["prefers_indoor"] = True
            preferences["activity_preferences"]["outdoor_activities"] = False
            preferences["weather_preferences"]["prefers_indoor"] = True
            learned_something = True
    
    # Activity preferences - outdoor
    if any(word in message_lower for word in ["outdoor", "outside", "outdoors", "prefer outdoor", "like outdoor"]):
        if preferences["activity_preferences"].get("prefers_outdoor") is None:
            preferences["activity_preferences"]["prefers_outdoor"] = True
            preferences["activity_preferences"]["outdoor_activities"] = True
            learned_something = True
    
    # Sunny preferences
    if any(word in message_lower for word in ["sunny", "love sun", "prefer sunny", "like sunny", "enjoy sunny"]):
        if not preferences["weather_preferences"]["prefers_sunny"]:
            preferences["weather_preferences"]["prefers_sunny"] = True
            learned_something = True
    
    # Learn from weather data if provided
    if weather_data:
        temp = weather_data.get("temperature", 0)
        if temp < 10 and "cold" in message_lower:
            if not preferences["temperature_preferences"]["dislikes_cold"]:
                preferences["temperature_preferences"]["dislikes_cold"] = True
                learned_something = True
    
    # Update learning counter and timestamp if we learned something
    if learned_something:
        preferences["learned_from_conversations"] += 1
    
    # Always update last_updated timestamp
    preferences["last_updated"] = datetime.now().isoformat()
    
    # Save updated preferences
    save_user_preferences(user_id, preferences)


def get_preferences_summary(user_id: str) -> str:
    """Get a human-readable summary of user preferences for the agent.
    
    Args:
        user_id: The unique identifier for the user.
    
    Returns:
        A string summary of user preferences that can be included in agent instructions.
    """
    prefs = load_user_preferences(user_id)
    
    summary_parts = []
    
    # Temperature preferences
    temp_prefs = prefs["temperature_preferences"]
    if temp_prefs["dislikes_cold"]:
        summary_parts.append("User dislikes cold weather")
    if temp_prefs["dislikes_heat"]:
        summary_parts.append("User dislikes hot weather")
    if temp_prefs["preferred_temp_range"]:
        min_temp, max_temp = temp_prefs["preferred_temp_range"]
        summary_parts.append(f"User prefers temperatures between {min_temp}°C and {max_temp}°C")
    
    # Weather preferences
    weather_prefs = prefs["weather_preferences"]
    if weather_prefs["dislikes_rain"]:
        summary_parts.append("User dislikes rainy weather")
    if weather_prefs["dislikes_wind"]:
        summary_parts.append("User dislikes windy weather")
    if weather_prefs["prefers_sunny"]:
        summary_parts.append("User prefers sunny weather")
    if weather_prefs["prefers_indoor"]:
        summary_parts.append("User prefers indoor activities")
    
    # Activity preferences
    activity_prefs = prefs["activity_preferences"]
    if not activity_prefs["outdoor_activities"]:
        summary_parts.append("User prefers indoor activities over outdoor")
    if activity_prefs["sensitive_to_weather"]:
        summary_parts.append("User is sensitive to weather changes")
    
    if summary_parts:
        return "User preferences: " + "; ".join(summary_parts) + "."
    else:
        return "No specific preferences learned yet. User preferences will be learned from conversations."

