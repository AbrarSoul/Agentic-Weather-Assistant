"""Flask web application for the Personal Weather Assistant."""

import os
import uuid
from flask import Flask, render_template, request, jsonify, g
from dotenv import load_dotenv
from google.adk import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from chatbot.agent import create_agent_with_preferences
from chatbot import preferences

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Initialize the ADK Runner with in-memory session service
session_service = InMemorySessionService()

# Cache agents and runners per user to avoid event loop conflicts
# This prevents creating new async workers on every request
_agent_cache = {}  # Stores (agent, last_prefs_timestamp) tuples
_runner_cache = {}


@app.route('/')
def index():
    """Render the main chat interface."""
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages."""
    try:
        data = request.json
        message = data.get('message', '').strip()
        session_id = data.get('session_id')
        user_id = data.get('user_id', 'default_user')
        
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Store user_id in thread-local storage for tool access
        from chatbot.weather_tools import set_user_id
        set_user_id(user_id)
        
        # Check if session exists, if not create it
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Check if session exists in the session service
        existing_session = session_service.get_session_sync(
            app_name="chatbot_app",
            user_id=user_id,
            session_id=session_id
        )
        
        # Create session if it doesn't exist
        if not existing_session:
            session_service.create_session_sync(
                app_name="chatbot_app",
                user_id=user_id,
                session_id=session_id
            )
        
        # Get or create agent with user-specific preferences in the prompt
        # Cache runners per user to avoid event loop conflicts
        prefs = preferences.load_user_preferences(user_id)
        current_prefs_timestamp = prefs.get('last_updated', '')
        
        # Check if we need to create or recreate the agent
        should_create_agent = False
        if user_id not in _agent_cache:
            should_create_agent = True
        else:
            # Check if preferences have been updated
            cached_timestamp = _agent_cache[user_id][1] if isinstance(_agent_cache[user_id], tuple) else None
            if cached_timestamp != current_prefs_timestamp:
                should_create_agent = True
        
        if should_create_agent:
            agent = create_agent_with_preferences(user_id)
            runner = Runner(
                agent=agent,
                app_name="chatbot_app",
                session_service=session_service
            )
            _agent_cache[user_id] = (agent, current_prefs_timestamp)
            _runner_cache[user_id] = runner
        else:
            runner = _runner_cache[user_id]
        
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
        
        # Extract the response from events
        # Event inherits from LlmResponse, so it has 'content' directly (not 'model_response')
        response_text = ""
        for event in events:
            # Check if event has content with text parts
            # Skip partial events and events with function calls (those are intermediate)
            if (event.content and event.content.parts and 
                not event.partial and 
                event.is_final_response()):
                for part in event.content.parts:
                    # Only extract text (not function calls or other parts)
                    if part.text:
                        response_text += part.text
        
        # Fallback: if no final response found, get text from last event with content
        if not response_text:
            events_list = list(events)
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
        
        # Automatically learn from the conversation
        # This uses keyword-based learning to extract preferences from user messages
        preferences.learn_from_conversation(
            user_id=user_id,
            user_message=message,
            response=response_text
        )
        
        # Invalidate agent cache if preferences were updated
        # This ensures the agent gets the latest preferences in the prompt
        if user_id in _agent_cache:
            del _agent_cache[user_id]
            if user_id in _runner_cache:
                del _runner_cache[user_id]
        
        return jsonify({
            'response': response_text,
            'session_id': session_id
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/new_session', methods=['POST'])
def new_session():
    """Create a new chat session."""
    user_id = 'default_user'
    session_id = str(uuid.uuid4())
    
    # Create session in the session service
    session_service.create_session_sync(
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
        print("Example: export OPENAI_API_KEY='your-api-key-here'")
    
    if not os.getenv('OPENWEATHER_API_KEY'):
        print("Warning: OPENWEATHER_API_KEY environment variable is not set!")
        print("Please set it before running the application.")
        print("Get your free API key from: https://openweathermap.org/api")
        print("Example: export OPENWEATHER_API_KEY='your-api-key-here'")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

