# Personal Weather Assistant

A smart weather assistant built with Flask and Microsoft Agent Framework, powered by OpenAI and OpenWeather API. The assistant learns your preferences over time to provide personalized weather recommendations.

## Features

- 🌤️ **Weather Queries**: Ask natural language questions about current weather and forecasts
- 📍 **Multi-City Support**: Get weather for any city (Dhaka, Helsinki, Tampere, etc.)
- 🎯 **Smart Recommendations**: Get practical advice (umbrella, jacket, outdoor activities)
- 🧠 **Preference Learning**: The assistant learns your preferences from conversations
- 💬 **Natural Language**: Chat naturally - no need for specific commands
- 🎨 **Beautiful UI**: Clean and modern web interface
- ⚡ **Fast & Responsive**: Real-time weather data and instant responses

## Prerequisites

- Python 3.8 or higher
- OpenAI API key
- OpenWeather API key (get one free at [openweathermap.org](https://openweathermap.org/api))

## Installation

1. **Clone or download this repository**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set your API keys:**
   
   On Windows (PowerShell):
   ```powershell
   $env:OPENAI_API_KEY="your-openai-api-key-here"
   $env:OPENWEATHER_API_KEY="your-openweather-api-key-here"
   # Optional: Set a specific model (default: gpt-4o-mini)
   $env:OPENAI_RESPONSES_MODEL_ID="gpt-4o-mini"
   ```
   
   On Linux/Mac:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key-here"
   export OPENWEATHER_API_KEY="your-openweather-api-key-here"
   # Optional: Set a specific model (default: gpt-4o-mini)
   export OPENAI_RESPONSES_MODEL_ID="gpt-4o-mini"
   ```
   
   Or create a `.env` file (optional, requires python-dotenv):
   ```
   OPENAI_API_KEY=your-openai-api-key-here
   OPENWEATHER_API_KEY=your-openweather-api-key-here
   OPENAI_RESPONSES_MODEL_ID=gpt-4o-mini
   ```
   
   **Note:** 
   - Get your OpenWeather API key for free at [openweathermap.org/api](https://openweathermap.org/api)
   - If you don't set `OPENAI_RESPONSES_MODEL_ID`, it will default to `gpt-4o-mini`. You can use other models like `gpt-4o`, `gpt-4-turbo`, or `gpt-3.5-turbo`.

## Running the Application

1. **Start the Flask server:**
   ```bash
   python app.py
   ```

2. **Open your browser and navigate to:**
   ```
   http://localhost:5000
   ```

3. **Start asking weather questions!**

   Try these example queries:
   - "What is the humidity in Dhaka today?"
   - "What will the weather be like in Tampere tomorrow?"
   - "Should I carry an umbrella this week?"
   - "Plan my Sunday afternoon outdoors in Helsinki."
   - "I hate cold weather. What's it like in Helsinki?"

## Project Structure

```
.
├── app.py                    # Flask application with agent integration
├── weather_service.py        # OpenWeather API integration
├── preferences_manager.py    # User preference learning system
├── weather_helper.py         # Weather query preprocessing
├── templates/
│   └── index.html           # Weather assistant web interface
├── requirements.txt         # Python dependencies
├── user_preferences.json    # Stored user preferences (auto-generated)
└── README.md               # This file
```

## How It Works

1. **Query Processing**: When you ask a weather question, the system:
   - Detects if it's a weather-related query
   - Extracts the city name from your message
   - Determines if you need current weather or a forecast

2. **Weather Data Fetching**: 
   - Calls OpenWeather API to get current conditions or forecasts
   - Interprets the data (temperature ranges, conditions, etc.)
   - Applies your learned preferences

3. **Personalized Response**:
   - The AI agent receives weather data and your preferences
   - Generates a natural, conversational response with recommendations
   - Learns from your conversation to improve future suggestions

4. **Preference Learning**:
   - Your preferences are stored in `user_preferences.json`
   - The assistant remembers if you dislike cold, wind, or rain
   - Future recommendations are personalized based on your preferences

## Use Cases

### Current Weather Queries
- "What is the humidity in Dhaka today?"
- "What's the temperature in Helsinki?"
- "How windy is it in Tampere?"

### Forecast Queries
- "What will the weather be like in Tampere tomorrow?"
- "What's the forecast for Helsinki this week?"
- "Will it rain in Dhaka on Sunday?"

### Recommendation Queries
- "Should I carry an umbrella this week?"
- "Plan my Sunday afternoon outdoors in Helsinki."
- "What should I wear in Tampere today?"

### Preference Learning
The assistant learns from statements like:
- "I hate cold weather" → Will remember you dislike cold
- "I don't like wind" → Will suggest indoor activities on windy days
- "I prefer indoor activities" → Will prioritize indoor suggestions

## Troubleshooting

- **"OPENAI_API_KEY environment variable is not set"**: Make sure you've set the environment variable before running the app
- **"OPENWEATHER_API_KEY environment variable is not set"**: Get a free API key from [openweathermap.org](https://openweathermap.org/api) and set it
- **Import errors**: Make sure all dependencies are installed with `pip install -r requirements.txt`
- **Port already in use**: Change the port in `app.py` (default is 5000)
- **City not found**: Make sure you spell city names correctly. The assistant recognizes common cities like Dhaka, Helsinki, Tampere, etc.
- **Weather data not loading**: Check your OpenWeather API key is valid and you have API credits remaining

## License

MIT License

## Resources

- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [OpenWeather API Documentation](https://openweathermap.org/api)

## Features in Detail

### Weather Data
- Current conditions: temperature, humidity, wind speed, pressure, visibility
- 5-day forecasts with daily summaries
- Weather interpretation (rainy, sunny, windy, etc.)

### Recommendations
- Umbrella suggestions for rainy conditions
- Clothing recommendations based on temperature
- Outdoor activity suitability assessment
- Wind and humidity considerations

### Preference Learning
The assistant learns:
- Temperature preferences (warm/cool)
- Weather condition dislikes (cold, wind, rain)
- Activity preferences (indoor/outdoor)
- All preferences are stored and used for future conversations

