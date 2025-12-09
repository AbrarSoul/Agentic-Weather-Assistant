# Agentic Weather Assistant

A comprehensive weather assistant project that compares two AI agent frameworks: **Google's Agent Development Kit (GADK)** and **Microsoft Agent Framework (MS)**. Both implementations provide intelligent weather assistance with natural language processing, personalized recommendations, and preference learning capabilities.

## 📋 Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Setup](#environment-setup)
  - [GADK Environment Setup](#gadk-environment-setup)
  - [MS Environment Setup](#ms-environment-setup)
  - [Comparison App Environment Setup](#comparison-app-environment-setup)
- [Running the Project](#running-the-project)
  - [Running GADK Project](#running-gadk-project)
  - [Running MS Project](#running-ms-project)
  - [Running Comparison App](#running-comparison-app)
- [Architecture](#architecture)
  - [GADK Architecture](#gadk-architecture)
  - [MS Architecture](#ms-architecture)
- [Usage Examples](#usage-examples)
- [Key Differences](#key-differences)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Overview

This project implements a Personal Weather Assistant using two different AI agent frameworks:

1. **GADK (Google Agent Development Kit)**: Uses Google's ADK framework with OpenAI GPT-4o-mini via LiteLLM, featuring tool-based agent architecture with session management.

2. **MS (Microsoft Agent Framework)**: Uses Microsoft's Agent Framework with OpenAI, featuring a service-oriented architecture with query preprocessing.

Both implementations provide:
- Real-time weather data from OpenWeather API
- Natural language query processing
- Personalized recommendations (umbrella, jacket, outdoor activities)
- User preference learning from conversations
- Multi-city weather support
- Modern web interfaces

## Project Structure

```
Agentic-Weather-Assistant/
├── GADK/                          # Google Agent Development Kit implementation
│   ├── app.py                     # Flask web application
│   ├── chatbot/                   # Agent and tools
│   │   ├── agent.py              # ADK agent definition
│   │   ├── weather_tools.py      # Weather API integration tools
│   │   └── preferences.py        # User preference learning
│   ├── templates/
│   │   └── index.html            # Web interface
│   ├── user_preferences/         # Stored user preferences
│   ├── env.example               # Environment variables template
│   ├── requirements.txt          # Python dependencies
│   └── README.md                 # GADK-specific documentation
│
├── MS/                            # Microsoft Agent Framework implementation
│   ├── app.py                    # Flask web application
│   ├── weather_service.py        # OpenWeather API service
│   ├── weather_helper.py         # Query preprocessing
│   ├── preferences_manager.py    # User preference learning
│   ├── templates/
│   │   └── index.html           # Web interface
│   ├── user_preferences.json    # Stored user preferences
│   ├── requirements.txt         # Python dependencies
│   └── README.md                # MS-specific documentation
│
├── comparison_app.py             # Side-by-side comparison application
├── evaluator.py                  # Response evaluation system
├── requirements.txt              # Root-level dependencies
├── templates/
│   └── comparison.html          # Comparison interface
└── README.md                     # This file
```

## Features

### Core Features (Both Frameworks)

- **Weather Information**: Current weather and forecasts for any city worldwide
- **Natural Language Processing**: Ask questions in plain English
- **Personalized Recommendations**: Umbrella, jacket, and activity suggestions
- **Preference Learning**: Remembers user preferences from conversations
- **Multi-City Support**: Works with cities worldwide
- **Modern Web Interface**: Clean, responsive chat interface
- **Real-time Responses**: Fast weather data fetching and processing

### GADK-Specific Features

- **Tool-based Architecture**: Uses ADK's tool system for weather queries
- **Session Management**: In-memory session service for conversation continuity
- **ADK Tools**: `get_current_weather`, `get_weather_forecast`, `get_user_preferences`, `update_user_preferences_from_insight`
- **Agent Caching**: Efficient agent caching per user to avoid event loop conflicts

### MS-Specific Features

- **Service-Oriented Architecture**: Separate services for weather, preferences, and query processing
- **Query Preprocessing**: WeatherHelper processes queries before sending to agent
- **Enhanced Context**: Weather data and preferences injected into agent context
- **Direct Agent Integration**: Uses Microsoft Agent Framework's OpenAI integration

## Prerequisites

- **Python**: 3.10 or higher (3.11+ recommended for GADK, 3.8+ for MS)
- **OpenAI API Key**: [Get one here](https://platform.openai.com/api-keys)
- **OpenWeather API Key**: [Get free key here](https://openweathermap.org/api)

## Installation

1. **Clone or download this repository**

2. **Install root-level dependencies** (for comparison app):
   ```bash
   pip install -r requirements.txt
   ```

3. **Install GADK dependencies**:
   ```bash
   cd GADK
   pip install -r requirements.txt
   cd ..
   ```

4. **Install MS dependencies**:
   ```bash
   cd MS
   pip install -r requirements.txt
   cd ..
   ```

## Environment Setup

### GADK Environment Setup

**Option 1: Using .env file (Recommended)**

1. Navigate to the `GADK` directory:
   ```bash
   cd GADK
   ```

2. Copy the example environment file:
   ```bash
   # On Windows (PowerShell)
   Copy-Item env.example .env
   
   # On Linux/Mac
   cp env.example .env
   ```

3. Edit the `.env` file and add your API keys:
   ```env
   OPENAI_API_KEY=your-actual-openai-api-key-here
   OPENWEATHER_API_KEY=your-actual-openweather-api-key-here
   ```

**Option 2: Environment Variables**

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

### MS Environment Setup

**Option 1: Using .env file (Requires python-dotenv)**

1. Navigate to the `MS` directory:
   ```bash
   cd MS
   ```

2. Create a `.env` file:
   ```bash
   # On Windows (PowerShell)
   New-Item -ItemType File -Name .env
   
   # On Linux/Mac
   touch .env
   ```

3. Edit the `.env` file and add your API keys:
   ```env
   OPENAI_API_KEY=your-openai-api-key-here
   OPENWEATHER_API_KEY=your-openweather-api-key-here
   OPENAI_RESPONSES_MODEL_ID=gpt-4o-mini
   ```

   **Note:** `OPENAI_RESPONSES_MODEL_ID` is optional (defaults to `gpt-4o-mini`). You can use other models like `gpt-4o`, `gpt-4-turbo`, or `gpt-3.5-turbo`.

**Option 2: Environment Variables**

**On Windows (PowerShell):**
```powershell
# Set for current session
$env:OPENAI_API_KEY="your-openai-api-key-here"
$env:OPENWEATHER_API_KEY="your-openweather-api-key-here"
$env:OPENAI_RESPONSES_MODEL_ID="gpt-4o-mini"  # Optional
```

**On Linux/Mac:**
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
export OPENWEATHER_API_KEY="your-openweather-api-key-here"
export OPENAI_RESPONSES_MODEL_ID="gpt-4o-mini"  # Optional
```


## Running the Project

### Running GADK Project

1. **Navigate to GADK directory:**
   ```bash
   cd GADK
   ```

2. **Ensure environment variables are set** (see [GADK Environment Setup](#gadk-environment-setup))

3. **Run the Flask application:**
   ```bash
   python app.py
   ```

4. **Open your browser and navigate to:**
   ```
   http://localhost:5000
   ```

### Running MS Project

1. **Navigate to MS directory:**
   ```bash
   cd MS
   ```

2. **Ensure environment variables are set** (see [MS Environment Setup](#ms-environment-setup))

3. **Run the Flask application:**
   ```bash
   python app.py
   ```

4. **Open your browser and navigate to:**
   ```
   http://localhost:5000
   ```

### Running Comparison App

The comparison app allows you to test both frameworks side-by-side:

1. **Navigate to root directory:**
   ```bash
   cd Agentic-Weather-Assistant
   ```

2. **Ensure environment variables are set** (see [Comparison App Environment Setup](#comparison-app-environment-setup))

3. **Run the comparison application:**
   ```bash
   python comparison_app.py
   ```

4. **Open your browser and navigate to:**
   ```
   http://localhost:5001
   ```

   **Note:** The comparison app runs on port 5001 to avoid conflicts with individual project apps on port 5000.

## Architecture

### GADK Architecture

```
User → Flask App → ADK Runner → Weather Agent → Tools
                                    ↓
                            Weather Tools (OpenWeather API)
                            Preferences Tools
                                    ↓
                            Preference Learning System
```

**Key Components:**
- **Flask App** (`app.py`): Web interface and request handling
- **ADK Runner**: Agent execution engine with session management
- **Weather Agent**: LLM-powered agent with tool access
- **Weather Tools**: `get_current_weather`, `get_weather_forecast`
- **Preference Tools**: `get_user_preferences`, `update_user_preferences_from_insight`
- **Session Service**: In-memory conversation state management
- **Preference Learning**: Automatic learning from conversations

### MS Architecture

```
User → Flask App → WeatherHelper → WeatherService → OpenWeather API
              ↓
         OpenAI Agent ← Enhanced Message (with weather data + preferences)
              ↓
         PreferencesManager (learning)
```

**Key Components:**
- **Flask App** (`app.py`): Web interface and request handling
- **WeatherHelper**: Query preprocessing and context enhancement
- **WeatherService**: OpenWeather API integration
- **OpenAI Agent**: Microsoft Agent Framework agent
- **PreferencesManager**: User preference learning and storage

## Usage Examples

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
- "I hate cold weather" → Remembers you dislike cold
- "I don't like wind" → Suggests indoor activities on windy days
- "I prefer indoor activities" → Prioritizes indoor suggestions

## Key Differences

| Feature | GADK | MS |
|---------|------|-----|
| **Framework** | Google Agent Development Kit | Microsoft Agent Framework |
| **LLM Integration** | LiteLLM (OpenAI) | Direct OpenAI via Agent Framework |
| **Tool System** | ADK native tools | Service-based architecture |
| **Session Management** | In-memory session service | Stateless (preferences stored) |
| **Query Processing** | Agent decides tool calls | Pre-processed by WeatherHelper |
| **Preference Learning** | Tool-based updates | Manager-based updates |
| **Agent Caching** | Per-user agent caching | Single agent instance |
| **Context Injection** | Via agent instructions | Via message enhancement |

## Troubleshooting

### Common Issues

**"OPENAI_API_KEY environment variable is not set"**
- Ensure you've set the environment variable or created a `.env` file
- Check that the `.env` file is in the correct directory (GADK/ or MS/)
- Verify the variable name is exactly `OPENAI_API_KEY`

**"OPENWEATHER_API_KEY environment variable is not set"**
- Get a free API key from [openweathermap.org/api](https://openweathermap.org/api)
- Set it in your `.env` file or as an environment variable

**Import errors (agent_framework, google.adk, etc.)**
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- For GADK: `cd GADK && pip install -r requirements.txt`
- For MS: `cd MS && pip install -r requirements.txt`
- For comparison app: `pip install -r requirements.txt` (root level)

**Port already in use**
- GADK and MS use port 5000
- Comparison app uses port 5001
- Change the port in the respective `app.py` file if needed

**City not found**
- Make sure you spell city names correctly
- The assistant recognizes common cities worldwide
- Try using the full city name (e.g., "New York" instead of "NYC")

**Weather data not loading**
- Check your OpenWeather API key is valid
- Verify you have API credits remaining (free tier: 60 calls/minute, 1,000,000 calls/month)
- Check your internet connection

**Agent not initializing (MS)**
- Ensure `agent-framework` package is installed: `pip install agent-framework>=1.0.0b1`
- Check that all environment variables are set correctly

**Session issues (GADK)**
- Sessions are stored in-memory and will be lost on server restart
- User preferences persist in `user_preferences/` directory

## License

- **GADK**: Uses Google's Agent Development Kit, licensed under Apache 2.0
- **MS**: MIT License
- **Project**: See individual component licenses

## Resources

- [Google Agent Development Kit Documentation](https://github.com/google/agent-development-kit)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [OpenWeather API Documentation](https://openweathermap.org/api)
- [Flask Documentation](https://flask.palletsprojects.com/)

