import os
import asyncio
import json
from flask import Flask, render_template, request, jsonify
from agent_framework.openai import OpenAIResponsesClient
from weather_service import WeatherService
from preferences_manager import PreferencesManager
from weather_helper import WeatherHelper

app = Flask(__name__)

# Initialize services
openai_client = None
agent = None
weather_service = None
preferences_manager = None
weather_helper = None

def initialize_services():
    """Initialize all services (weather, preferences, and agent)"""
    global openai_client, agent, weather_service, preferences_manager, weather_helper
    
    # Initialize weather service
    try:
        weather_service = WeatherService()
    except ValueError as e:
        print(f"Warning: {e}")
        weather_service = None
    
    # Initialize preferences manager
    preferences_manager = PreferencesManager()
    
    # Initialize weather helper if weather service is available
    if weather_service:
        weather_helper = WeatherHelper(weather_service, preferences_manager)
    else:
        weather_helper = None
    
    # Initialize OpenAI client and agent
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    model_id = os.getenv('OPENAI_RESPONSES_MODEL_ID', 'gpt-4o-mini')
    openai_client = OpenAIResponsesClient(api_key=api_key, model_id=model_id)
    
    # Get user preferences summary for agent context
    prefs_summary = preferences_manager.get_preferences_summary()
    
    # Create agent instructions with weather assistant context
    instructions = f"""You are a Personal Weather Assistant. Your role is to help users with weather-related queries and provide personalized recommendations.

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
    
    # Create agent
    agent = openai_client.create_agent(
        name="WeatherAssistant",
        instructions=instructions
    )
    
    return agent

@app.route('/')
def index():
    """Render the main chat interface"""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        # Initialize services if not already initialized
        if agent is None:
            initialize_services()
        
        # Get the user's message from the request
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Pre-process weather queries
        weather_data_used = None
        enhanced_message = user_message
        
        if weather_helper:
            enhanced_message, weather_data_used = weather_helper.process_weather_query(user_message)
        
        # Run the agent with the enhanced message (async)
        async def get_response():
            response = await agent.run(enhanced_message)
            return response
        
        # Execute the async function
        response = asyncio.run(get_response())
        
        # Learn from this conversation
        if preferences_manager:
            preferences_manager.learn_from_conversation(
                user_message=user_message,
                weather_data=weather_data_used,
                response=str(response)
            )
        
        # Return the response
        return jsonify({
            'response': str(response),
            'status': 'success'
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

if __name__ == '__main__':
    # Initialize services when the app starts
    try:
        initialize_services()
        print("=" * 60)
        print("Personal Weather Assistant initialized successfully!")
        print("=" * 60)
        print("Required environment variables:")
        print("  - OPENAI_API_KEY: Your OpenAI API key")
        print("  - OPENWEATHER_API_KEY: Your OpenWeather API key")
        print("\nOptional environment variables:")
        print("  - OPENAI_RESPONSES_MODEL_ID: Model to use (default: gpt-4o-mini)")
        print("=" * 60)
    except Exception as e:
        print(f"Warning: Could not initialize services: {e}")
        print("\nMake sure the following environment variables are set:")
        print("  - OPENAI_API_KEY: Required for the AI assistant")
        print("  - OPENWEATHER_API_KEY: Required for weather data")
        print("\nYou can optionally set:")
        print("  - OPENAI_RESPONSES_MODEL_ID (default: gpt-4o-mini)")
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)

