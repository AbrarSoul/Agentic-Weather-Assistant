# Agent Orchestration Architecture

This document explains how the agents and components are orchestrated in the Personal Weather Assistant application.

## Overview

The Personal Weather Assistant uses a multi-layered orchestration architecture built on Google's Agent Development Kit (ADK). The system coordinates between the Flask web application, ADK Runner, Weather Assistant Agent, external tools, and preference learning system to provide personalized weather assistance.

## Architecture Components

### 1. **Flask Web Application** (`app.py`)
   - **Role**: Main orchestrator and entry point
   - **Responsibilities**:
     - Receives HTTP requests from the web interface
     - Manages user sessions and user context
     - Coordinates agent creation and caching
     - Handles response extraction and formatting
     - Triggers preference learning after conversations

### 2. **ADK Runner** (`google.adk.Runner`)
   - **Role**: Agent execution engine
   - **Responsibilities**:
     - Manages agent lifecycle and execution
     - Handles session persistence via Session Service
     - Coordinates tool calls and responses
     - Manages conversation context and memory

### 3. **Session Service** (`InMemorySessionService`)
   - **Role**: Conversation state management
   - **Responsibilities**:
     - Stores conversation history per session
     - Maintains context across multiple turns
     - Enables conversation continuity

### 4. **Weather Assistant Agent** (`chatbot/agent.py`)
   - **Role**: Core intelligent agent
   - **Responsibilities**:
     - Processes user queries using LLM (GPT-4o-mini)
     - Decides which tools to invoke
     - Generates personalized responses
     - Incorporates user preferences into instructions

### 5. **Weather Tools** (`chatbot/weather_tools.py`)
   - **Role**: External API integration
   - **Tools**:
     - `get_current_weather`: Fetches current weather data from OpenWeather API
     - `get_weather_forecast`: Retrieves multi-day weather forecasts
   - **Responsibilities**:
     - Interface with OpenWeather API
     - Transform API responses into structured data
     - Handle errors gracefully

### 6. **Preference Tools** (`chatbot/agent.py`)
   - **Role**: User preference management
   - **Tools**:
     - `get_user_preferences`: Retrieves stored user preferences
     - `update_user_preferences_from_insight`: Updates preferences based on agent insights
   - **Responsibilities**:
     - Provide preference data to the agent
     - Allow agent to update preferences during conversations

### 7. **Preference Learning System** (`chatbot/preferences.py`)
   - **Role**: Automatic preference extraction
   - **Responsibilities**:
     - Keyword-based learning from user messages
     - Persistent storage of preferences
     - Preference summarization for agent instructions

## Orchestration Flow

### Step 1: Request Reception
```
User → Flask App (/chat endpoint)
```
- User sends a message via the web interface
- Flask receives POST request with `message`, `session_id`, and `user_id`

### Step 2: User Context Setup
```python
set_user_id(user_id)  # Thread-local storage
```
- User ID is stored in thread-local storage for tool access
- This ensures tools can access user context without explicit passing

### Step 3: Session Management
```python
session_service.get_session_sync() or create_session_sync()
```
- Checks if session exists
- Creates new session if needed
- Maintains conversation continuity

### Step 4: Agent Creation/Caching
```python
# Check cache
if user_id not in _agent_cache or preferences_updated:
    agent = create_agent_with_preferences(user_id)
    runner = Runner(agent=agent, ...)
    _agent_cache[user_id] = (agent, timestamp)
```

**Agent Creation Process:**
1. Load user preferences from storage
2. Generate preference summary
3. Create agent instruction with preferences embedded
4. Initialize Agent with:
   - Model: OpenAI GPT-4o-mini (via LiteLLM)
   - Instruction: Personalized with user preferences
   - Tools: Weather tools + Preference tools
5. Create Runner with agent and session service

**Caching Strategy:**
- Agents are cached per user to avoid recreation overhead
- Cache is invalidated when preferences are updated
- Timestamp-based invalidation ensures fresh preferences

### Step 5: Agent Execution
```python
events = runner.run(
    user_id=user_id,
    session_id=session_id,
    new_message=Content(role="user", parts=[...])
)
```

**Execution Flow:**
1. **Message Processing**: Runner receives user message
2. **Context Loading**: Runner loads conversation history from session
3. **Agent Invocation**: Agent processes message with LLM
4. **Tool Decision**: Agent decides which tools to call (if any)
5. **Tool Execution**: Tools are executed and return data
6. **Response Generation**: Agent generates response using tool results
7. **Event Streaming**: Runner yields events (partial and final responses)

### Step 6: Tool Orchestration

The agent can invoke multiple tools in sequence or parallel:

#### Weather Tool Calls
```
Agent → get_current_weather(city="Dhaka")
  ↓
OpenWeather API
  ↓
Structured weather data
  ↓
Agent processes and responds
```

#### Preference Tool Calls
```
Agent → get_user_preferences()
  ↓
Preference storage
  ↓
Preference summary
  ↓
Agent uses in response generation
```

#### Preference Update Calls
```
Agent detects user preference → update_user_preferences_from_insight(...)
  ↓
Preference storage updated
  ↓
Agent cache invalidated (next request will use new preferences)
```

### Step 7: Response Extraction
```python
for event in events:
    if event.is_final_response() and event.content:
        response_text += event.content.parts[0].text
```
- Extracts final response from event stream
- Filters out partial/intermediate events
- Handles function call events appropriately

### Step 8: Preference Learning
```python
preferences.learn_from_conversation(
    user_id=user_id,
    user_message=message,
    response=response_text
)
```

**Learning Process:**
1. **Keyword Extraction**: Analyzes user message for preference keywords
2. **Pattern Matching**: Detects phrases like "I hate cold", "prefer indoor", etc.
3. **Preference Update**: Updates stored preferences
4. **History Storage**: Saves conversation to history
5. **Cache Invalidation**: Invalidates agent cache to ensure fresh preferences

### Step 9: Response Delivery
```python
return jsonify({
    'response': response_text,
    'session_id': session_id
})
```
- Returns JSON response to web interface
- Includes session ID for conversation continuity

## Agent Instruction Personalization

The agent's instruction is dynamically generated with user preferences:

```python
instruction = f"""
You are a Personal Weather Assistant...
User preferences learned so far: {prefs_summary}
...
"""
```

**Preference Summary Example:**
- "User dislikes cold weather; User prefers sunny weather; User prefers indoor activities"

This ensures the agent:
- Knows user preferences without explicit queries
- Provides personalized recommendations
- Adapts responses to user's stated preferences

## Session and Context Management

### Session Lifecycle
1. **Creation**: New session created on first message or explicit `/new_session` call
2. **Persistence**: Session stored in `InMemorySessionService`
3. **Context**: Conversation history maintained across turns
4. **Retrieval**: Runner loads session context before each agent invocation

### User Context Thread-Local Storage
- User ID stored in thread-local storage (`threading.local()`)
- Tools access user ID via `get_user_id()` without explicit parameters
- Enables clean tool interfaces while maintaining user context

## Agent Caching Strategy

### Cache Structure
```python
_agent_cache = {
    user_id: (agent, preferences_timestamp)
}
_runner_cache = {
    user_id: runner
}
```

### Cache Invalidation Triggers
1. **Preference Updates**: When `learn_from_conversation()` updates preferences
2. **Explicit Updates**: When agent calls `update_user_preferences_from_insight()`
3. **Timestamp Mismatch**: When stored preferences timestamp differs from cache

### Benefits
- **Performance**: Avoids agent recreation on every request
- **Consistency**: Ensures agent uses latest preferences
- **Resource Efficiency**: Reuses agent instances across requests

## Tool Execution Flow

### Sequential Tool Calls
```
User: "What's the weather in Helsinki and should I bring an umbrella?"
  ↓
Agent → get_current_weather("Helsinki")
  ↓
Weather data received
  ↓
Agent → get_user_preferences()
  ↓
Preferences received
  ↓
Agent generates personalized response with weather + preferences
```

### Parallel Tool Calls (Potential)
The agent can decide to call multiple tools in parallel if needed, though current implementation typically uses sequential calls.

## Error Handling

### Tool Errors
- Tools return error dictionaries on failure
- Agent receives error information and can respond appropriately
- User receives friendly error messages

### Agent Errors
- Runner catches exceptions during execution
- Flask app returns 500 error with message
- User sees error notification in UI

### API Errors
- OpenWeather API errors handled in tools
- Graceful degradation with error messages
- No system crashes on external API failures

## Data Flow Diagram

```
┌─────────────┐
│   User      │
│  (Browser)  │
└──────┬──────┘
       │ HTTP POST /chat
       ▼
┌─────────────────┐
│   Flask App     │
│   (app.py)      │
│                 │
│ 1. Set user_id  │
│ 2. Get/Create   │
│    session      │
│ 3. Get/Create   │
│    agent        │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  ADK Runner     │
│                 │
│ - Load session  │
│ - Execute agent │
│ - Stream events │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Weather Agent   │
│ (GPT-4o-mini)   │
│                 │
│ - Process query │
│ - Decide tools  │
│ - Generate resp │
└──────┬──────────┘
       │
       ├──────────────┐
       │              │
       ▼              ▼
┌─────────────┐  ┌──────────────┐
│Weather Tools│  │Preference    │
│             │  │Tools         │
│- get_current│  │- get_prefs   │
│- get_forecast│ │- update_prefs│
└──────┬──────┘  └──────┬───────┘
       │                │
       ▼                ▼
┌─────────────┐  ┌──────────────┐
│OpenWeather  │  │Preferences   │
│API         │  │Storage       │
└─────────────┘  └──────────────┘
       │                │
       └────────┬───────┘
                │
                ▼
       ┌─────────────────┐
       │  Agent Response │
       │  (via Runner)   │
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │  Flask App       │
       │  - Extract text  │
       │  - Learn prefs   │
       │  - Invalidate    │
       │    cache        │
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │  User (Browser)  │
       └─────────────────┘
```

## Key Orchestration Patterns

### 1. **Lazy Agent Creation**
- Agents created on-demand per user
- Cached for performance
- Recreated when preferences change

### 2. **Context Propagation**
- User ID via thread-local storage
- Session context via ADK Session Service
- Preferences embedded in agent instructions

### 3. **Reactive Preference Learning**
- Automatic learning after each conversation
- Agent can explicitly update preferences
- Cache invalidation ensures freshness

### 4. **Tool Abstraction**
- Tools are simple functions
- ADK handles tool registration and invocation
- Agent decides tool usage autonomously

### 5. **Event-Driven Response**
- Runner streams events
- Flask app filters for final responses
- Enables future streaming support

## Future Orchestration Enhancements

Potential improvements:
1. **Streaming Responses**: Real-time response streaming to UI
2. **Multi-Agent Coordination**: Specialized agents for different tasks
3. **Parallel Tool Execution**: Concurrent tool calls for performance
4. **Advanced Caching**: More sophisticated cache strategies
5. **Distributed Sessions**: Persistent session storage (database)
6. **Agent Specialization**: Separate agents for weather, preferences, recommendations

## Conclusion

The orchestration architecture provides a clean separation of concerns:
- **Flask App**: Request handling and coordination
- **ADK Runner**: Agent execution and session management
- **Agent**: Intelligent decision-making and tool orchestration
- **Tools**: External integrations and data access
- **Preferences**: Learning and personalization

This design enables:
- Scalable architecture
- Maintainable codebase
- Personalized user experience
- Extensible tool ecosystem
- Efficient resource usage

