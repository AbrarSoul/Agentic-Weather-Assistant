"""Personal Weather Assistant agent using ADK with OpenAI."""

import os
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext
from chatbot.weather_tools import get_current_weather, get_weather_forecast
from chatbot import preferences

# Load environment variables from .env file
load_dotenv()

# OpenAI API key is loaded from environment variable (from .env or system env)
# Users should set OPENAI_API_KEY in .env file or as environment variable


def get_user_preferences(user_id: str = None, tool_context: ToolContext = None) -> dict:
    """Get user preferences for personalized weather recommendations.
    
    Args:
        user_id: The unique identifier for the user (optional, will use current request user if not provided).
        tool_context: Optional tool context (required by ADK).
    
    Returns:
        A dictionary containing user preferences summary.
    """
    # Get user_id from thread-local storage if not provided
    if not user_id:
        from chatbot.weather_tools import get_user_id
        user_id = get_user_id() or 'default_user'
    
    prefs = preferences.load_user_preferences(user_id)
    summary = preferences.get_preferences_summary(user_id)
    
    return {
        "user_id": user_id,
        "preferences_summary": summary,
        "detailed_preferences": prefs,
        "preferences_learned": prefs["learned_from_conversations"] > 0
    }


def update_user_preferences_from_insight(
    user_id: str = None,
    insight_text: str = "",
    dislikes_cold: bool = None,
    dislikes_heat: bool = None,
    dislikes_rain: bool = None,
    dislikes_wind: bool = None,
    prefers_sunny: bool = None,
    prefers_indoor: bool = None,
    outdoor_activities: bool = None,
    sensitive_to_weather: bool = None,
    tool_context: ToolContext = None
) -> dict:
    """Update user preferences based on insights extracted from conversation.
    
    This tool should be called when you learn something about the user's preferences
    from their conversation. For example, if they say "I hate cold weather" or 
    "I prefer staying indoors when it's rainy", use this tool to save that preference.
    
    Args:
        user_id: The unique identifier for the user (optional, will use current request user if not provided).
        insight_text: A brief description of what was learned (e.g., "User dislikes cold weather").
        dislikes_cold: True if user dislikes cold weather.
        dislikes_heat: True if user dislikes hot weather.
        dislikes_rain: True if user dislikes rainy weather.
        dislikes_wind: True if user dislikes windy weather.
        prefers_sunny: True if user prefers sunny weather.
        prefers_indoor: True if user prefers indoor activities.
        outdoor_activities: True if user enjoys outdoor activities, False if prefers indoor.
        sensitive_to_weather: True if user is sensitive to weather changes.
        tool_context: Optional tool context (required by ADK).
    
    Returns:
        A dictionary confirming the preferences were updated.
    """
    from datetime import datetime
    
    # Get user_id from thread-local storage if not provided
    if not user_id:
        from chatbot.weather_tools import get_user_id
        user_id = get_user_id() or 'default_user'
    
    conversation_insights = {
        "insight_text": insight_text,
        "timestamp": datetime.now().isoformat()
    }
    
    if dislikes_cold is not None:
        conversation_insights["dislikes_cold"] = dislikes_cold
    if dislikes_heat is not None:
        conversation_insights["dislikes_heat"] = dislikes_heat
    if dislikes_rain is not None:
        conversation_insights["dislikes_rain"] = dislikes_rain
    if dislikes_wind is not None:
        conversation_insights["dislikes_wind"] = dislikes_wind
    if prefers_sunny is not None:
        conversation_insights["prefers_sunny"] = prefers_sunny
    if prefers_indoor is not None:
        conversation_insights["prefers_indoor"] = prefers_indoor
    if outdoor_activities is not None:
        conversation_insights["outdoor_activities"] = outdoor_activities
    if sensitive_to_weather is not None:
        conversation_insights["sensitive_to_weather"] = sensitive_to_weather
    
    updated_prefs = preferences.update_preferences_from_conversation(user_id, conversation_insights)
    
    return {
        "status": "success",
        "message": f"Preferences updated: {insight_text}",
        "updated_preferences": preferences.get_preferences_summary(user_id)
    }


def get_agent_instruction(prefs_summary: str = None) -> str:
    """Generate agent instruction with user preferences.
    
    Args:
        prefs_summary: User preferences summary string. If None, uses placeholder.
    
    Returns:
        Agent instruction string with preferences included.
    """
    if prefs_summary is None or "No specific preferences" in prefs_summary:
        prefs_summary = "No specific preferences learned yet."
    
    return f"""You are a Personal Weather Assistant. Your role is to help users with weather-related queries and provide personalized recommendations.

Key capabilities:
1. Answer questions about current weather conditions (temperature, humidity, wind, etc.)
2. Provide weather forecasts for upcoming days
3. Give practical recommendations (umbrella, jacket, outdoor activities)
4. Learn and remember user preferences from conversations

User preferences learned so far: {prefs_summary}

When users ask about weather:
- The weather data will be provided in the query context as [WEATHER DATA] sections
- Use this data to answer questions accurately
- Interpret the data and provide clear, helpful recommendations
- Consider user preferences when making recommendations (shown in [USER PREFERENCES] if available)
- Be conversational and friendly

When providing recommendations:
- Mention specific items (umbrella, jacket, etc.) when relevant
- Suggest indoor/outdoor activities based on weather conditions
- Reference user preferences when they're relevant
- Be practical and actionable
- If weather data shows rain, recommend an umbrella
- If temperature is cold, recommend warm clothing
- If conditions are good, suggest outdoor activities

Always be helpful, clear, and personalized in your responses. Use the weather data provided in the context to give accurate information."""


def create_agent_with_preferences(user_id: str = None) -> Agent:
    """Create an agent instance with user preferences in the instruction.
    
    Args:
        user_id: The unique identifier for the user. If None, uses 'default_user'.
    
    Returns:
        Agent instance with preferences included in instruction.
    """
    if user_id is None:
        user_id = 'default_user'
    
    prefs_summary = preferences.get_preferences_summary(user_id)
    instruction = get_agent_instruction(prefs_summary)
    
    return Agent(
        name="weather_assistant",
        model=LiteLlm(model="openai/gpt-4o-mini"),  # Using OpenAI GPT-4o-mini via LiteLLM
        instruction=instruction,
        description="A Personal Weather Assistant that provides weather information and learns user preferences",
        tools=[
            get_current_weather,
            get_weather_forecast,
            get_user_preferences,
            update_user_preferences_from_insight,
        ],
    )


# Create the default Personal Weather Assistant agent (without specific user preferences)
root_agent = create_agent_with_preferences('default_user')

