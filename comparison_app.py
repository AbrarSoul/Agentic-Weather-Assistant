"""Flask web application for comparing GADK and MS weather chatbot frameworks."""

import os
import sys
import uuid
import asyncio
import threading
import time
from datetime import date, datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Add both project directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GADK'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'MS'))

# Load environment variables
load_dotenv()

# Import GADK modules
from google.adk import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from chatbot.agent import create_agent_with_preferences
from chatbot import preferences as gadk_preferences

# Import MS modules
from weather_service import WeatherService as MSWeatherService
from preferences_manager import PreferencesManager
from weather_helper import WeatherHelper

# Import evaluator
from evaluator import ChatbotEvaluator

app = Flask(__name__, template_folder='templates')

# Initialize GADK services
gadk_session_service = InMemorySessionService()
_gadk_agent_cache = {}
_gadk_runner_cache = {}

# Initialize MS services
_ms_agent = None
_ms_weather_service = None
_ms_preferences_manager = None
_ms_weather_helper = None
_ms_openai_client = None

# Initialize evaluator (will be set after MS services are initialized)
evaluator = None

def sanitize_weather_data(weather_data):
    """
    Convert date objects to strings in weather data to make it JSON serializable.
    
    Args:
        weather_data: Dictionary containing weather data that may have date objects as keys
        
    Returns:
        Sanitized dictionary with date objects converted to strings
    """
    if not weather_data:
        return None
    
    if isinstance(weather_data, dict):
        sanitized = {}
        for key, value in weather_data.items():
            # Convert date objects to strings
            if isinstance(key, date):
                key = key.isoformat()
            elif isinstance(key, datetime):
                key = key.isoformat()
            
            # Recursively sanitize nested dictionaries
            if isinstance(value, dict):
                value = sanitize_weather_data(value)
            elif isinstance(value, list):
                value = [sanitize_weather_data(item) if isinstance(item, dict) else item for item in value]
            
            sanitized[key] = value
        return sanitized
    elif isinstance(weather_data, list):
        return [sanitize_weather_data(item) if isinstance(item, dict) else item for item in weather_data]
    
    return weather_data

def initialize_ms_services():
    """Initialize MS project services"""
    global _ms_agent, _ms_weather_service, _ms_preferences_manager, _ms_weather_helper, _ms_openai_client
    
    try:
        # Initialize weather service
        try:
            _ms_weather_service = MSWeatherService()
        except ValueError as e:
            print(f"Warning: {e}")
            _ms_weather_service = None
        
        # Initialize preferences manager
        _ms_preferences_manager = PreferencesManager()
        
        # Initialize weather helper if weather service is available
        if _ms_weather_service:
            _ms_weather_helper = WeatherHelper(_ms_weather_service, _ms_preferences_manager)
        else:
            _ms_weather_helper = None
        
        # Initialize OpenAI client and agent
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        # Try to import agent_framework
        try:
            from agent_framework.openai import OpenAIResponsesClient
            model_id = os.getenv('OPENAI_RESPONSES_MODEL_ID', 'gpt-4o-mini')
            _ms_openai_client = OpenAIResponsesClient(api_key=api_key, model_id=model_id)
            
            # Get user preferences summary for agent context
            prefs_summary = _ms_preferences_manager.get_preferences_summary()
            
            # Create agent instructions
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
            _ms_agent = _ms_openai_client.create_agent(
                name="WeatherAssistant",
                instructions=instructions
            )
        except ImportError:
            print("Warning: agent_framework not found. MS project may not work correctly.")
            _ms_agent = None
    
    except Exception as e:
        print(f"Error initializing MS services: {e}")
        _ms_agent = None
    
    # Initialize evaluator with weather service
    global evaluator
    evaluator = ChatbotEvaluator(weather_service=_ms_weather_service)

def get_gadk_response(message, user_id='default_user', session_id=None):
    """Get response from GADK project"""
    weather_data_used = None
    try:
        # Store user_id in thread-local storage for tool access
        from chatbot.weather_tools import set_user_id
        set_user_id(user_id)
        
        # Try to extract weather data for evaluation
        # Check if message contains city name and fetch weather data
        if _ms_weather_service:
            try:
                # Simple city extraction (can be improved)
                import re
                city_patterns = [
                    r'\b(dhaka|helsinki|tampere|stockholm|copenhagen|oslo|reykjavik|new york|london|paris|tokyo)\b',
                    r'in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:today|tomorrow|weather)'
                ]
                
                message_lower = message.lower()
                city = None
                
                # Check common cities
                common_cities = {
                    'dhaka': 'Dhaka', 'helsinki': 'Helsinki', 'tampere': 'Tampere',
                    'stockholm': 'Stockholm', 'copenhagen': 'Copenhagen', 
                    'oslo': 'Oslo', 'reykjavik': 'Reykjavik'
                }
                
                for city_key, city_name in common_cities.items():
                    if city_key in message_lower:
                        city = city_name
                        break
                
                # Try regex patterns
                if not city:
                    for pattern in city_patterns:
                        match = re.search(pattern, message, re.IGNORECASE)
                        if match:
                            potential_city = match.group(1) if match.groups() else match.group(0)
                            if len(potential_city.split()) <= 3:
                                city = potential_city
                                break
                
                # Fetch weather data if city found and query is weather-related
                if city and any(kw in message_lower for kw in ['weather', 'temperature', 'forecast', 'rain', 'temp']):
                    try:
                        # Check if it's a forecast query
                        is_forecast = any(kw in message_lower for kw in ['tomorrow', 'forecast', 'week', 'next'])
                        if is_forecast:
                            forecast_data = _ms_weather_service.get_forecast(city, days=5)
                            weather_data_used = forecast_data
                        else:
                            current_data = _ms_weather_service.get_current_weather(city)
                            weather_data_used = {'current': current_data}
                        
                        # Sanitize weather data to convert date objects to strings
                        if weather_data_used:
                            weather_data_used = sanitize_weather_data(weather_data_used)
                    except Exception as e:
                        # Weather fetch failed, continue without weather data
                        pass
            except Exception as e:
                # Weather extraction failed, continue without weather data
                pass
        
        # Check if session exists, if not create it
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Check if session exists in the session service
        existing_session = gadk_session_service.get_session_sync(
            app_name="chatbot_app",
            user_id=user_id,
            session_id=session_id
        )
        
        # Create session if it doesn't exist
        if not existing_session:
            gadk_session_service.create_session_sync(
                app_name="chatbot_app",
                user_id=user_id,
                session_id=session_id
            )
        
        # Get or create agent with user-specific preferences
        prefs = gadk_preferences.load_user_preferences(user_id)
        current_prefs_timestamp = prefs.get('last_updated', '')
        
        # Check if we need to create or recreate the agent
        should_create_agent = False
        if user_id not in _gadk_agent_cache:
            should_create_agent = True
        else:
            cached_timestamp = _gadk_agent_cache[user_id][1] if isinstance(_gadk_agent_cache[user_id], tuple) else None
            if cached_timestamp != current_prefs_timestamp:
                should_create_agent = True
        
        if should_create_agent:
            agent = create_agent_with_preferences(user_id)
            runner = Runner(
                agent=agent,
                app_name="chatbot_app",
                session_service=gadk_session_service
            )
            _gadk_agent_cache[user_id] = (agent, current_prefs_timestamp)
            _gadk_runner_cache[user_id] = runner
        else:
            runner = _gadk_runner_cache[user_id]
        
        # Create a Content object for the user's message
        new_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=message)]
        )
        
        # Run the agent with the user's message
        events = runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message
        )
        
        # Extract the response from events and count tool calls
        # Also collect execution events for sequence diagram
        response_text = ""
        tool_call_count = 0
        execution_events = []
        event_timestamp = 0
        
        events_list = list(events)
        for event in events_list:
            event_timestamp += 1
            
            # Collect execution events for visualization
            event_data = {
                'timestamp': event_timestamp,
                'type': 'unknown',
                'from': None,
                'to': None,
                'message': None,
                'data': None
            }
            
            # Check for tool/function calls
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        # Check for function calls in parts
                        if hasattr(part, 'function_call') and part.function_call:
                            tool_call_count += 1
                            func_call = part.function_call
                            tool_name = func_call.name if hasattr(func_call, 'name') else 'Tool'
                            # Map tool names to display names
                            tool_display_name = {
                                'get_current_weather': 'WeatherAPI',
                                'get_weather_forecast': 'WeatherAPI',
                                'get_user_preferences': 'Preferences',
                                'update_user_preferences_from_insight': 'Preferences'
                            }.get(tool_name, tool_name)
                            event_data['type'] = 'tool_call'
                            event_data['from'] = 'WeatherAgent'
                            event_data['to'] = tool_display_name
                            event_data['message'] = f"Calling {tool_name}"
                            if hasattr(func_call, 'args'):
                                event_data['data'] = str(func_call.args)[:100]  # Truncate long data
                        # Check for tool calls in event
                        if hasattr(part, 'tool_call') and part.tool_call:
                            tool_call_count += 1
                            tool_call = part.tool_call
                            tool_name = tool_call.name if hasattr(tool_call, 'name') else 'Tool'
                            # Map tool names to display names
                            tool_display_name = {
                                'get_current_weather': 'WeatherAPI',
                                'get_weather_forecast': 'WeatherAPI',
                                'get_user_preferences': 'Preferences',
                                'update_user_preferences_from_insight': 'Preferences'
                            }.get(tool_name, tool_name)
                            event_data['type'] = 'tool_call'
                            event_data['from'] = 'WeatherAgent'
                            event_data['to'] = tool_display_name
                            event_data['message'] = f"Calling {tool_name}"
            
            # Check for LLM processing
            if hasattr(event, 'partial') and event.partial:
                event_data['type'] = 'llm_processing'
                event_data['from'] = 'Runner'
                event_data['to'] = 'LLM'
                event_data['message'] = 'Processing with LLM'
            
            # Check for final response
            if (event.content and event.content.parts and 
                not event.partial and 
                event.is_final_response()):
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text
                        if not event_data['message']:
                            event_data['type'] = 'response'
                            event_data['from'] = 'LLM'
                            event_data['to'] = 'WeatherAgent'
                            event_data['message'] = 'Response generated'
            
            # Add event if it has meaningful data
            if event_data['type'] != 'unknown':
                execution_events.append(event_data)
        
        # Fallback: if no final response found, get text from last event with content
        if not response_text:
            for event in reversed(events_list):
                if event.content and event.content.parts and not event.partial:
                    for part in event.content.parts:
                        if part.text:
                            response_text += part.text
                            break
                    if response_text:
                        break
        
        # If no response found, provide a default message
        if not response_text:
            response_text = "I'm sorry, I couldn't generate a response. Please try again."
        
        # Estimate tool calls if not found in events (count weather data usage)
        if tool_call_count == 0 and weather_data_used:
            # If weather data was used, at least one tool call was made
            tool_call_count = 1
            if 'daily_summaries' in weather_data_used or 'detailed_forecast' in weather_data_used:
                tool_call_count = 1  # Forecast call
            elif 'current' in weather_data_used:
                tool_call_count = 1  # Current weather call
        
        # Track learning events
        learning_events = []
        learning_timestamp = 0
        
        # Add learning trigger event
        learning_events.append({
            'timestamp': learning_timestamp,
            'type': 'learning_trigger',
            'from': 'FlaskApp',
            'to': 'Preferences',
            'message': 'Conversation completed, starting learning',
            'data': None
        })
        learning_timestamp += 1
        
        # Automatically learn from the conversation
        # Track the learning process
        learning_events.append({
            'timestamp': learning_timestamp,
            'type': 'conversation_storage',
            'from': 'Preferences',
            'to': 'Storage',
            'message': 'Storing conversation in history',
            'data': None
        })
        learning_timestamp += 1
        
        # Check if message contains preference keywords
        message_lower = message.lower()
        has_preferences = any(word in message_lower for word in [
            'cold', 'freezing', 'hot', 'warm', 'cool', 'windy', 'rain', 'sunny', 
            'indoor', 'outdoor', 'hate', 'dislike', 'prefer', 'like'
        ])
        
        if has_preferences:
            learning_events.append({
                'timestamp': learning_timestamp,
                'type': 'keyword_extraction',
                'from': 'Preferences',
                'to': 'KeywordMatcher',
                'message': 'Extracting preferences from keywords',
                'data': None
            })
            learning_timestamp += 1
            
            learning_events.append({
                'timestamp': learning_timestamp,
                'type': 'preference_update',
                'from': 'KeywordMatcher',
                'to': 'Preferences',
                'message': 'Preferences updated from keywords',
                'data': None
            })
            learning_timestamp += 1
        
        learning_events.append({
            'timestamp': learning_timestamp,
            'type': 'preference_save',
            'from': 'Preferences',
            'to': 'Storage',
            'message': 'Saving preferences to file',
            'data': None
        })
        learning_timestamp += 1
        
        # Actually perform learning
        gadk_preferences.learn_from_conversation(
            user_id=user_id,
            user_message=message,
            response=response_text
        )
        
        learning_events.append({
            'timestamp': learning_timestamp,
            'type': 'cache_invalidation',
            'from': 'Preferences',
            'to': 'AgentCache',
            'message': 'Invalidating agent cache',
            'data': None
        })
        
        # Invalidate agent cache if preferences were updated
        if user_id in _gadk_agent_cache:
            del _gadk_agent_cache[user_id]
            if user_id in _gadk_runner_cache:
                del _gadk_runner_cache[user_id]
        
        # Sanitize weather data before returning (convert date objects to strings)
        sanitized_weather_data = sanitize_weather_data(weather_data_used) if weather_data_used else None
        
        # Add tool execution events based on weather data usage
        if weather_data_used:
            if 'daily_summaries' in weather_data_used or 'detailed_forecast' in weather_data_used:
                execution_events.append({
                    'timestamp': len(execution_events) + 1,
                    'type': 'tool_call',
                    'from': 'WeatherAgent',
                    'to': 'WeatherAPI',
                    'message': 'Fetching weather forecast',
                    'data': None
                })
                execution_events.append({
                    'timestamp': len(execution_events) + 1,
                    'type': 'tool_response',
                    'from': 'WeatherAPI',
                    'to': 'WeatherAgent',
                    'message': 'Forecast data received',
                    'data': None
                })
            elif 'current' in weather_data_used:
                execution_events.append({
                    'timestamp': len(execution_events) + 1,
                    'type': 'tool_call',
                    'from': 'WeatherAgent',
                    'to': 'WeatherAPI',
                    'message': 'Fetching current weather',
                    'data': None
                })
                execution_events.append({
                    'timestamp': len(execution_events) + 1,
                    'type': 'tool_response',
                    'from': 'WeatherAPI',
                    'to': 'WeatherAgent',
                    'message': 'Weather data received',
                    'data': None
                })
        
        # Add session context loading
        execution_events.insert(0, {
            'timestamp': 0,
            'type': 'context_load',
            'from': 'Runner',
            'to': 'SessionSvc',
            'message': 'Loading conversation context',
            'data': None
        })
        
        # Add final response event
        if response_text:
            execution_events.append({
                'timestamp': len(execution_events),
                'type': 'final_response',
                'from': 'WeatherAgent',
                'to': 'User',
                'message': 'Final response ready',
                'data': None
            })
        
        return {
            'response': response_text,
            'status': 'success',
            'session_id': session_id,
            'weather_data_used': sanitized_weather_data,
            'tool_call_count': tool_call_count,
            'execution_events': execution_events,
            'learning_events': learning_events
        }
    
    except Exception as e:
        return {
            'response': f"Error: {str(e)}",
            'status': 'error',
            'session_id': session_id
        }

def get_ms_response(message):
    """Get response from MS project"""
    try:
        # Initialize services if not already initialized
        if _ms_agent is None:
            initialize_ms_services()
        
        if _ms_agent is None:
            return {
                'response': 'MS agent not initialized. Please check your environment variables and dependencies.',
                'status': 'error'
            }
        
        # Pre-process weather queries
        weather_data_used = None
        enhanced_message = message
        tool_call_count = 0
        execution_events = []
        event_timestamp = 0
        
        # Add initial event
        execution_events.append({
            'timestamp': event_timestamp,
            'type': 'query_received',
            'from': 'User',
            'to': 'WeatherHelper',
            'message': 'User query received',
            'data': None
        })
        event_timestamp += 1
        
        if _ms_weather_helper:
            # Add weather helper processing event
            execution_events.append({
                'timestamp': event_timestamp,
                'type': 'processing',
                'from': 'WeatherHelper',
                'to': 'WeatherHelper',
                'message': 'Processing weather query',
                'data': None
            })
            event_timestamp += 1
            
            enhanced_message, weather_data_used = _ms_weather_helper.process_weather_query(message)
            
            # Count tool calls based on weather data fetched
            if weather_data_used:
                if 'daily_summaries' in weather_data_used or 'detailed_forecast' in weather_data_used:
                    tool_call_count = 1  # Forecast API call
                    execution_events.append({
                        'timestamp': event_timestamp,
                        'type': 'tool_call',
                        'from': 'WeatherHelper',
                        'to': 'WeatherSvc',
                        'message': 'Requesting forecast data',
                        'data': None
                    })
                    event_timestamp += 1
                    execution_events.append({
                        'timestamp': event_timestamp,
                        'type': 'tool_call',
                        'from': 'WeatherSvc',
                        'to': 'WeatherAPI',
                        'message': 'Fetching forecast from API',
                        'data': None
                    })
                    event_timestamp += 1
                    execution_events.append({
                        'timestamp': event_timestamp,
                        'type': 'tool_response',
                        'from': 'WeatherAPI',
                        'to': 'WeatherSvc',
                        'message': 'Forecast data received',
                        'data': None
                    })
                    event_timestamp += 1
                    execution_events.append({
                        'timestamp': event_timestamp,
                        'type': 'tool_response',
                        'from': 'WeatherSvc',
                        'to': 'WeatherHelper',
                        'message': 'Forecast processed',
                        'data': None
                    })
                    event_timestamp += 1
                elif 'current' in weather_data_used:
                    tool_call_count = 1  # Current weather API call
                    execution_events.append({
                        'timestamp': event_timestamp,
                        'type': 'tool_call',
                        'from': 'WeatherHelper',
                        'to': 'WeatherSvc',
                        'message': 'Requesting current weather',
                        'data': None
                    })
                    event_timestamp += 1
                    execution_events.append({
                        'timestamp': event_timestamp,
                        'type': 'tool_call',
                        'from': 'WeatherSvc',
                        'to': 'WeatherAPI',
                        'message': 'Fetching current weather from API',
                        'data': None
                    })
                    event_timestamp += 1
                    execution_events.append({
                        'timestamp': event_timestamp,
                        'type': 'tool_response',
                        'from': 'WeatherAPI',
                        'to': 'WeatherSvc',
                        'message': 'Weather data received',
                        'data': None
                    })
                    event_timestamp += 1
                    execution_events.append({
                        'timestamp': event_timestamp,
                        'type': 'tool_response',
                        'from': 'WeatherSvc',
                        'to': 'WeatherHelper',
                        'message': 'Weather processed',
                        'data': None
                    })
                    event_timestamp += 1
            
            # Add preferences context loading
            execution_events.append({
                'timestamp': event_timestamp,
                'type': 'context_load',
                'from': 'WeatherHelper',
                'to': 'PrefsMgr',
                'message': 'Loading user preferences',
                'data': None
            })
            event_timestamp += 1
            
            # Add message enhancement event
            execution_events.append({
                'timestamp': event_timestamp,
                'type': 'message_enhancement',
                'from': 'WeatherHelper',
                'to': 'OpenAIAgent',
                'message': 'Enhanced message with context',
                'data': None
            })
            event_timestamp += 1
        
        # Add LLM processing event
        execution_events.append({
            'timestamp': event_timestamp,
            'type': 'llm_processing',
            'from': 'OpenAIAgent',
            'to': 'LLM',
            'message': 'Processing with LLM',
            'data': None
        })
        event_timestamp += 1
        
        # Run the agent with the enhanced message (async)
        async def get_response():
            response = await _ms_agent.run(enhanced_message)
            return response
        
        # Execute the async function
        response = asyncio.run(get_response())
        
        # Add response generation event
        execution_events.append({
            'timestamp': event_timestamp,
            'type': 'response',
            'from': 'LLM',
            'to': 'OpenAIAgent',
            'message': 'Response generated',
            'data': None
        })
        event_timestamp += 1
        
        # Sanitize weather data before passing to preferences manager (convert date objects to strings)
        sanitized_weather_data_for_prefs = sanitize_weather_data(weather_data_used) if weather_data_used else None
        
        # Track learning events
        learning_events = []
        learning_timestamp = 0
        
        # Add learning trigger event
        learning_events.append({
            'timestamp': learning_timestamp,
            'type': 'learning_trigger',
            'from': 'FlaskApp',
            'to': 'PrefsMgr',
            'message': 'Conversation completed, starting learning',
            'data': None
        })
        learning_timestamp += 1
        
        # Learn from this conversation
        if _ms_preferences_manager:
            learning_events.append({
                'timestamp': learning_timestamp,
                'type': 'conversation_storage',
                'from': 'PrefsMgr',
                'to': 'Storage',
                'message': 'Storing conversation in history',
                'data': None
            })
            learning_timestamp += 1
            
            # Check if message contains preference keywords
            message_lower = message.lower()
            has_preferences = any(word in message_lower for word in [
                'cold', 'freezing', 'hot', 'warm', 'cool', 'windy', 'rain', 'sunny', 
                'indoor', 'outdoor', 'hate', 'dislike', 'prefer', 'like'
            ])
            
            if has_preferences:
                learning_events.append({
                    'timestamp': learning_timestamp,
                    'type': 'keyword_extraction',
                    'from': 'PrefsMgr',
                    'to': 'KeywordMatcher',
                    'message': 'Extracting preferences from keywords',
                    'data': None
                })
                learning_timestamp += 1
                
                learning_events.append({
                    'timestamp': learning_timestamp,
                    'type': 'preference_update',
                    'from': 'KeywordMatcher',
                    'to': 'PrefsMgr',
                    'message': 'Preferences updated from keywords',
                    'data': None
                })
                learning_timestamp += 1
            
            learning_events.append({
                'timestamp': learning_timestamp,
                'type': 'preference_save',
                'from': 'PrefsMgr',
                'to': 'Storage',
                'message': 'Saving preferences to file',
                'data': None
            })
            
            # Actually perform learning
            _ms_preferences_manager.learn_from_conversation(
                user_message=message,
                weather_data=sanitized_weather_data_for_prefs,
                response=str(response)
            )
        
        # Sanitize weather data before returning (convert date objects to strings)
        sanitized_weather_data = sanitized_weather_data_for_prefs
        
        # Add final response event
        execution_events.append({
            'timestamp': event_timestamp,
            'type': 'final_response',
            'from': 'OpenAIAgent',
            'to': 'User',
            'message': 'Final response ready',
            'data': None
        })
        
        return {
            'response': str(response),
            'status': 'success',
            'weather_data_used': sanitized_weather_data,
            'tool_call_count': tool_call_count,
            'execution_events': execution_events,
            'learning_events': learning_events
        }
    
    except Exception as e:
        return {
            'response': f"Error: {str(e)}",
            'status': 'error'
        }

@app.route('/')
def index():
    """Render the main comparison interface."""
    return render_template('comparison.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages and run both projects simultaneously."""
    try:
        data = request.json
        message = data.get('message', '').strip()
        user_id = data.get('user_id', 'default_user')
        session_id = data.get('session_id')
        
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Results dictionary
        results = {
            'gadk': None,
            'ms': None,
            'gadk_time': 0,
            'ms_time': 0
        }
        
        # Run both projects in parallel using threads
        def run_gadk():
            start_time = time.time()
            results['gadk'] = get_gadk_response(message, user_id, session_id)
            results['gadk_time'] = time.time() - start_time
        
        def run_ms():
            start_time = time.time()
            results['ms'] = get_ms_response(message)
            results['ms_time'] = time.time() - start_time
        
        # Create and start threads
        gadk_thread = threading.Thread(target=run_gadk)
        ms_thread = threading.Thread(target=run_ms)
        
        gadk_thread.start()
        ms_thread.start()
        
        # Wait for both threads to complete
        gadk_thread.join()
        ms_thread.join()
        
        # Generate session_id from GADK if not provided
        if not session_id and results['gadk'] and results['gadk'].get('session_id'):
            session_id = results['gadk']['session_id']
        
        # Evaluate responses if evaluator is available
        gadk_metrics = None
        ms_metrics = None
        
        if evaluator:
            try:
                if results['gadk'] and results['gadk'].get('response'):
                    # Ensure weather data is sanitized before evaluation
                    gadk_weather_data = results['gadk'].get('weather_data_used')
                    if gadk_weather_data:
                        gadk_weather_data = sanitize_weather_data(gadk_weather_data)
                    
                    # Get user preferences for GADK
                    gadk_user_prefs = None
                    gadk_conversation_history = None
                    try:
                        gadk_user_prefs = gadk_preferences.load_user_preferences(user_id)
                        # Extract conversation history from preferences
                        if gadk_user_prefs and 'conversation_history' in gadk_user_prefs:
                            # Format conversation history for evaluator
                            # Evaluator expects: [{'user': '...', 'assistant': '...'}]
                            history = gadk_user_prefs.get('conversation_history', [])
                            # Exclude the current message from history (it's being evaluated now)
                            gadk_conversation_history = [
                                {
                                    'user': turn.get('user_message', turn.get('user', '')),
                                    'assistant': turn.get('response', turn.get('assistant', ''))
                                }
                                for turn in history
                                if isinstance(turn, dict) and turn.get('user_message') != message
                            ]
                    except Exception as e:
                        print(f"Error loading GADK preferences/history: {e}")
                    
                    gadk_metrics = evaluator.evaluate_response(
                        user_query=message,
                        response=results['gadk']['response'],
                        framework_name='GADK',
                        weather_data_used=gadk_weather_data,
                        conversation_history=gadk_conversation_history,
                        user_preferences=gadk_user_prefs,
                        response_time=results['gadk_time'],
                        tool_call_count=results['gadk'].get('tool_call_count')
                    )
            except Exception as e:
                print(f"Error evaluating GADK response: {e}")
                import traceback
                traceback.print_exc()
            
            try:
                if results['ms'] and results['ms'].get('response'):
                    # Ensure weather data is sanitized before evaluation
                    ms_weather_data = results['ms'].get('weather_data_used')
                    if ms_weather_data:
                        ms_weather_data = sanitize_weather_data(ms_weather_data)
                    
                    # Get user preferences for MS
                    ms_user_prefs = None
                    ms_conversation_history = None
                    try:
                        if _ms_preferences_manager:
                            ms_user_prefs = _ms_preferences_manager.preferences
                            # Extract conversation history from preferences
                            if ms_user_prefs and 'conversation_history' in ms_user_prefs:
                                # Format conversation history for evaluator
                                # Evaluator expects: [{'user': '...', 'assistant': '...'}]
                                history = ms_user_prefs.get('conversation_history', [])
                                # Exclude the current message from history (it's being evaluated now)
                                ms_conversation_history = [
                                    {
                                        'user': turn.get('user_message', turn.get('user', '')),
                                        'assistant': turn.get('response', turn.get('assistant', ''))
                                    }
                                    for turn in history
                                    if isinstance(turn, dict) and turn.get('user_message') != message
                                ]
                    except Exception as e:
                        print(f"Error loading MS preferences/history: {e}")
                    
                    ms_metrics = evaluator.evaluate_response(
                        user_query=message,
                        response=results['ms']['response'],
                        framework_name='MS',
                        weather_data_used=ms_weather_data,
                        conversation_history=ms_conversation_history,
                        user_preferences=ms_user_prefs,
                        response_time=results['ms_time'],
                        tool_call_count=results['ms'].get('tool_call_count')
                    )
            except Exception as e:
                print(f"Error evaluating MS response: {e}")
                import traceback
                traceback.print_exc()
        
        # Prepare response data
        response_data = {
            'gadk': results['gadk'] or {'response': 'No response', 'status': 'error'},
            'ms': results['ms'] or {'response': 'No response', 'status': 'error'},
            'gadk_time': round(results['gadk_time'], 2),
            'ms_time': round(results['ms_time'], 2),
            'session_id': session_id
        }
        
        # Add metrics if available
        if gadk_metrics:
            response_data['gadk']['metrics'] = gadk_metrics
        if ms_metrics:
            response_data['ms']['metrics'] = ms_metrics
        
        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'gadk': {'response': f'Error: {str(e)}', 'status': 'error'},
            'ms': {'response': f'Error: {str(e)}', 'status': 'error'}
        }), 500

@app.route('/new_session', methods=['POST'])
def new_session():
    """Create a new chat session."""
    user_id = 'default_user'
    session_id = str(uuid.uuid4())
    
    # Create session in GADK session service
    gadk_session_service.create_session_sync(
        app_name="chatbot_app",
        user_id=user_id,
        session_id=session_id
    )
    
    return jsonify({'session_id': session_id})

if __name__ == '__main__':
    # Check if API keys are set
    if not os.getenv('OPENAI_API_KEY'):
        print("Warning: OPENAI_API_KEY environment variable is not set!")
        print("Please set it before running the application.")
    
    if not os.getenv('OPENWEATHER_API_KEY'):
        print("Warning: OPENWEATHER_API_KEY environment variable is not set!")
        print("Get your free API key from: https://openweathermap.org/api")
    
    # Initialize MS services
    print("Initializing services...")
    initialize_ms_services()
    print("Services initialized!")
    
    app.run(debug=True, host='0.0.0.0', port=5001)

