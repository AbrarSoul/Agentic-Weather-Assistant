# Personal Weather Assistant

A Personal Weather Assistant application built using Google's Agent Development Kit (ADK) with OpenAI API, featuring a Flask web interface. The assistant provides weather information, personalized recommendations, and learns user preferences over time.

## Features

- 🌤️ **Weather Information**: Get current weather and forecasts for any city worldwide
- 🤖 Powered by Google's Agent Development Kit (ADK)
- 🧠 Uses OpenAI GPT-4o-mini model via LiteLLM
- 💬 Natural language queries (e.g., "What's the humidity in Dhaka today?")
- 🎯 **Personalized Recommendations**: Umbrella, jacket, outdoor activity suggestions
- 🧠 **Learning System**: Remembers user preferences (dislikes cold/rain/wind, prefers indoor/sunny, etc.)
- 💬 Clean and modern web interface
- 🔄 Session management for conversation continuity
- ⚡ Real-time chat experience

## Prerequisites

- Python 3.10 or higher (Python 3.11+ recommended)
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
- OpenWeather API key ([Get free key here](https://openweathermap.org/api))

## Installation

1. Clone or download this repository

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Set your API keys:

**Option 1: Using .env file (Recommended)**
```bash
# Copy the example file
cp env.example .env

# Edit .env and add your API keys
# On Windows, you can use Notepad or any text editor
# On Linux/Mac, use: nano .env or vim .env
```

Then edit `.env` and add your API keys:
```
OPENAI_API_KEY=your-actual-openai-api-key-here
OPENWEATHER_API_KEY=your-actual-openweather-api-key-here
```

**Option 2: Environment variable**

**On Windows (PowerShell):**
```powershell
# Set for current session
$env:OPENAI_API_KEY="your-openai-api-key-here"
$env:OPENWEATHER_API_KEY="your-openweather-api-key-here"

# Or set permanently (requires admin)
[System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'your-openai-api-key-here', 'User')
[System.Environment]::SetEnvironmentVariable('OPENWEATHER_API_KEY', 'your-openweather-api-key-here', 'User')
```

**On Linux/Mac:**
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
export OPENWEATHER_API_KEY="your-openweather-api-key-here"
```

## Usage

1. Start the Flask application:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

3. Start chatting with your Personal Weather Assistant!

## Example Queries

Try asking natural language questions like:

- "What is the humidity in Dhaka today?"
- "What will the weather be like in Tampere tomorrow?"
- "Should I carry an umbrella this week?"
- "Plan my Sunday afternoon outdoors in Helsinki."
- "I hate cold weather" (the assistant will remember this preference)
- "What's the temperature in New York?"

The assistant will:
- Fetch real-time weather data from OpenWeather API
- Provide personalized recommendations based on weather conditions
- Learn and remember your preferences from conversations
- Give you tailored advice for outdoor activities

## Project Structure

```
.
├── app.py                      # Flask web application
├── chatbot/
│   ├── __init__.py
│   ├── agent.py               # ADK agent definition with weather tools
│   ├── weather_tools.py       # OpenWeather API integration
│   └── preferences.py         # User preference learning and storage
├── templates/
│   └── index.html             # Web interface
├── user_preferences/          # Stored user preferences (created automatically)
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## How It Works

### Weather Data
The assistant uses the OpenWeather API to fetch:
- **Current Weather**: Temperature, humidity, wind speed, weather conditions, etc.
- **Forecasts**: Multi-day forecasts with detailed hourly predictions

### Preference Learning
The assistant learns from your conversations:
- **Temperature Preferences**: Dislikes cold/heat, preferred temperature ranges
- **Weather Preferences**: Dislikes rain/wind, prefers sunny weather
- **Activity Preferences**: Indoor vs outdoor preferences, weather sensitivity

Preferences are stored in `user_preferences/` directory as JSON files (one per user) and persist across sessions.

### Personalized Recommendations
Based on weather data and learned preferences, the assistant provides:
- **Umbrella suggestions**: When rain is expected
- **Clothing recommendations**: Jacket suggestions for cold weather
- **Activity planning**: Whether weather is suitable for outdoor activities
- **Customized advice**: Tailored to your specific preferences

## Configuration

You can modify the assistant behavior by editing `chatbot/agent.py`:

- Change the model: Update the `model` parameter (e.g., `"openai/gpt-4o"` for GPT-4)
- Modify instructions: Update the `instruction` parameter to change the assistant's behavior
- Adjust description: Update the `description` parameter

## Notes

- The application uses in-memory session storage, so sessions will be lost when the server restarts
- User preferences are stored persistently in the `user_preferences/` directory
- Make sure to keep your API keys secure and never commit them to version control
- The default model is `gpt-4o-mini` which is cost-effective. You can change it to `gpt-4o` or other OpenAI models
- OpenWeather API free tier includes 60 calls/minute and 1,000,000 calls/month

## License

This project uses the ADK framework which is licensed under Apache 2.0.

