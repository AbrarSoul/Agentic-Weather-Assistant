# Learning Capability Architecture

This document explains how the Personal Weather Assistant learns and adapts to user preferences throughout the conversation pipeline.

## Overview

The system implements a **dual-mode learning architecture** that combines:
1. **Automatic Keyword-Based Learning**: Passive extraction of preferences from user messages
2. **Agent-Driven Explicit Learning**: Active learning when the agent detects preference signals

This hybrid approach ensures comprehensive preference capture while maintaining conversation flow.

## Learning Mechanisms

### 1. Automatic Keyword-Based Learning

**Location**: `chatbot/preferences.py` → `learn_from_conversation()`

**Trigger**: Automatically called after every conversation turn in `app.py`

**Process**:
```python
preferences.learn_from_conversation(
    user_id=user_id,
    user_message=message,
    response=response_text
)
```

#### How It Works

1. **Message Normalization**
   - Converts user message to lowercase for pattern matching
   - Preserves original message for history

2. **Keyword Pattern Matching**
   - Scans message for predefined preference keywords
   - Matches against multiple keyword patterns per preference type
   - Uses `any(word in message_lower for word in [...])` pattern matching

3. **Preference Categories Detected**

   **Temperature Preferences:**
   - **Cold Dislike**: `["cold", "freezing", "too cold", "hate cold", "dislike cold", "don't like cold"]`
   - **Heat Dislike**: `["hot", "too hot", "hate hot", "dislike hot", "don't like hot", "heat"]`
   - **Warm Preference**: `["warm", "love warm", "prefer warm", "like warm"]`
   - **Cool Preference**: `["cool", "prefer cool", "like cool"]`

   **Weather Preferences:**
   - **Wind Dislike**: `["windy", "hate wind", "dislike wind", "too windy", "don't like wind"]`
   - **Rain Dislike**: `["hate rain", "dislike rain", "don't like rain", "hate rainy", "dislike rainy"]`
   - **Sunny Preference**: `["sunny", "love sun", "prefer sunny", "like sunny", "enjoy sunny"]`

   **Activity Preferences:**
   - **Indoor Preference**: `["indoor", "stay inside", "inside activities", "prefer indoor", "like indoor"]`
   - **Outdoor Preference**: `["outdoor", "outside", "outdoors", "prefer outdoor", "like outdoor"]`

4. **Contextual Learning**
   - Can use weather data if provided to enhance learning
   - Example: If temperature < 10°C and user mentions "cold", reinforces cold dislike

5. **Idempotent Updates**
   - Only updates preferences if they haven't been set before
   - Prevents overwriting existing preferences unnecessarily
   - Uses flags like `if not preferences["temperature_preferences"]["dislikes_cold"]`

#### Example Learning Scenarios

**Scenario 1: Direct Statement**
```
User: "I hate cold weather"
  ↓
Keyword match: "hate cold" → dislikes_cold = True
  ↓
Preference updated
```

**Scenario 2: Implicit Preference**
```
User: "I prefer staying indoors when it's rainy"
  ↓
Keyword matches: "indoor" + "rainy"
  ↓
prefers_indoor = True
dislikes_rain = True
```

**Scenario 3: Contextual Learning**
```
User: "It's too cold today" (temperature = 5°C)
  ↓
Keyword match: "cold" + weather_data.temp < 10
  ↓
dislikes_cold = True (reinforced)
```

### 2. Agent-Driven Explicit Learning

**Location**: `chatbot/agent.py` → `update_user_preferences_from_insight()`

**Trigger**: Agent autonomously decides to call this tool during conversation

**Process**:
The agent analyzes conversation context and explicitly calls the tool when it detects preference signals:

```python
update_user_preferences_from_insight(
    user_id=user_id,
    insight_text="User dislikes cold weather",
    dislikes_cold=True,
    ...
)
```

#### How It Works

1. **Agent Detection**
   - Agent processes user message with LLM understanding
   - Identifies preference signals beyond simple keywords
   - Can detect nuanced preferences (e.g., "I'm not a fan of windy days")

2. **Structured Insight Extraction**
   - Agent extracts structured preference data
   - Creates insight text describing what was learned
   - Maps to preference schema

3. **Tool Invocation**
   - Agent calls `update_user_preferences_from_insight()` tool
   - Passes structured preference data
   - Tool validates and updates preferences

4. **Preference Update**
   - Calls `update_preferences_from_conversation()` internally
   - Updates all relevant preference fields
   - Stores insight in conversation history

#### Example Agent Learning

**Scenario: Nuanced Preference**
```
User: "I tend to avoid going outside when it's really windy"
  ↓
Agent (LLM) analyzes: Detects wind aversion preference
  ↓
Agent calls: update_user_preferences_from_insight(
    insight_text="User avoids outdoor activities in windy conditions",
    dislikes_wind=True,
    prefers_indoor=True
)
  ↓
Preference updated with structured data
```

## Learning Pipeline Flow

### Complete Learning Cycle

```
┌─────────────────────────────────────────────────────────────┐
│                    User Sends Message                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Agent Processes Message                        │
│  - LLM analyzes message                                     │
│  - May call update_user_preferences_from_insight()          │
│    if preference detected                                   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Agent Generates Response                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         Flask App Extracts Response                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│    Automatic Learning (learn_from_conversation)             │
│                                                             │
│  1. Store conversation in history                           │
│  2. Keyword pattern matching                                │
│  3. Extract preferences                                     │
│  4. Update preference storage                               │
│  5. Increment learning counter                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         Cache Invalidation                                  │
│  - Agent cache cleared if preferences updated              │
│  - Ensures next request uses fresh preferences              │
└─────────────────────────────────────────────────────────────┘
```

### Detailed Learning Steps

#### Step 1: Conversation Storage
```python
conversation_entry = {
    "timestamp": datetime.now().isoformat(),
    "user_message": user_message,
    "response": response  # Optional
}
preferences["conversation_history"].append(conversation_entry)
```
- Every conversation is stored in history
- Limited to last 50 conversations (rolling window)
- Enables future analysis and context retrieval

#### Step 2: Keyword Extraction
```python
message_lower = user_message.lower()
if any(word in message_lower for word in ["cold", "freezing", ...]):
    preferences["temperature_preferences"]["dislikes_cold"] = True
    learned_something = True
```
- Case-insensitive matching
- Multiple keyword patterns per preference
- Sets `learned_something` flag when preference detected

#### Step 3: Preference Update
```python
if learned_something:
    preferences["learned_from_conversations"] += 1

preferences["last_updated"] = datetime.now().isoformat()
save_user_preferences(user_id, preferences)
```
- Increments learning counter
- Updates timestamp
- Persists to JSON file

#### Step 4: Cache Invalidation
```python
# In app.py after learning
if user_id in _agent_cache:
    del _agent_cache[user_id]
    del _runner_cache[user_id]
```
- Ensures agent uses updated preferences on next request
- Agent will be recreated with new preference summary

## Preference Storage Architecture

### Storage Format

**Location**: `user_preferences/{user_id}_preferences.json`

**Structure**:
```json
{
  "temperature_preferences": {
    "dislikes_cold": false,
    "dislikes_heat": false,
    "preferred_temp_range": null,
    "comfortable_min": 15,
    "comfortable_max": 25
  },
  "weather_preferences": {
    "dislikes_rain": false,
    "dislikes_wind": false,
    "prefers_sunny": false,
    "prefers_indoor": false
  },
  "activity_preferences": {
    "outdoor_activities": true,
    "sensitive_to_weather": false
  },
  "conversation_history": [
    {
      "timestamp": "2024-01-15T10:30:00",
      "user_message": "I hate cold weather",
      "response": "..."
    }
  ],
  "learned_from_conversations": 3,
  "last_updated": "2024-01-15T10:30:00"
}
```

### Storage Operations

#### Loading Preferences
```python
def load_user_preferences(user_id: str) -> Dict[str, Any]:
    prefs_file = get_preferences_file(user_id)
    if not prefs_file.exists():
        return get_default_preferences()
    # Load and merge with defaults
```

**Features**:
- Returns defaults if file doesn't exist
- Merges with defaults to ensure all keys present
- Handles JSON decode errors gracefully

#### Saving Preferences
```python
def save_user_preferences(user_id: str, preferences: Dict[str, Any]):
    preferences["last_updated"] = datetime.now().isoformat()
    # Save to JSON file
```

**Features**:
- Always updates timestamp
- Atomic write operation
- UTF-8 encoding for international characters

## Preference Integration into Agent

### Agent Instruction Personalization

**Location**: `chatbot/agent.py` → `get_agent_instruction()`

**Process**:
1. **Load Preferences**
   ```python
   prefs_summary = preferences.get_preferences_summary(user_id)
   ```

2. **Generate Summary**
   ```python
   # Example output:
   # "User preferences: User dislikes cold weather; User prefers sunny weather."
   ```

3. **Embed in Instruction**
   ```python
   instruction = f"""
   You are a Personal Weather Assistant...
   
   User preferences learned so far: {prefs_summary}
   
   When providing recommendations:
   - Consider user preferences when making recommendations
   - Reference user preferences when they're relevant
   ...
   """
   ```

4. **Agent Creation**
   ```python
   agent = Agent(
       instruction=instruction,  # Contains preferences
       tools=[...],
       ...
   )
   ```

### Preference Summary Generation

**Location**: `chatbot/preferences.py` → `get_preferences_summary()`

**Process**:
1. Loads user preferences
2. Scans all preference categories
3. Builds human-readable summary
4. Returns formatted string for agent instruction

**Example Outputs**:
- **With Preferences**: `"User preferences: User dislikes cold weather; User prefers sunny weather."`
- **No Preferences**: `"No specific preferences learned yet. User preferences will be learned from conversations."`

## Learning Capability Features

### 1. **Idempotent Learning**
- Prevents duplicate preference updates
- Only sets preferences if not already set
- Example: Won't overwrite `dislikes_cold=True` if already `True`

### 2. **Conversation History**
- Stores last 50 conversations
- Enables future analysis
- Provides context for preference changes

### 3. **Learning Counter**
- Tracks number of learning events
- Incremented on each preference update
- Stored in `learned_from_conversations` field

### 4. **Timestamp Tracking**
- `last_updated` timestamp on every save
- Enables cache invalidation logic
- Tracks when preferences were last modified

### 5. **Multi-Modal Learning**
- Keyword-based (automatic)
- LLM-based (agent-driven)
- Contextual (weather data + keywords)

### 6. **Preference Persistence**
- JSON file storage per user
- Survives server restarts
- Cross-session continuity

## Learning Examples

### Example 1: Simple Keyword Learning

**User Message**: "I hate cold weather"

**Learning Process**:
1. `learn_from_conversation()` called
2. Keyword match: "hate cold" → `dislikes_cold = True`
3. Preference saved
4. Cache invalidated
5. Next agent creation includes: "User dislikes cold weather"

**Result**: Agent will consider cold weather as negative for this user

### Example 2: Agent-Driven Learning

**User Message**: "I'm not really a fan of going outside when it's windy"

**Learning Process**:
1. Agent (LLM) analyzes message
2. Agent detects: wind aversion + indoor preference
3. Agent calls: `update_user_preferences_from_insight(dislikes_wind=True, prefers_indoor=True)`
4. Preference updated with structured data
5. `learn_from_conversation()` also runs (may catch "windy" keyword)
6. Both mechanisms contribute to learning

**Result**: Comprehensive preference capture from both mechanisms

### Example 3: Contextual Learning

**User Message**: "It's freezing today" (temperature = -5°C)

**Learning Process**:
1. Weather data available: `temp = -5`
2. Keyword match: "freezing"
3. Contextual check: `temp < 10 and "cold" in message`
4. Reinforces: `dislikes_cold = True`
5. Preference updated

**Result**: Learning enhanced by weather context

### Example 4: Preference Evolution

**Conversation 1**:
- User: "I don't like rain"
- Learned: `dislikes_rain = True`

**Conversation 2**:
- User: "I prefer staying indoors"
- Learned: `prefers_indoor = True`

**Conversation 3**:
- Agent sees: rainy forecast + user dislikes rain + prefers indoor
- Agent recommendation: "Since you prefer indoor activities and dislike rain, I'd suggest staying inside today."

**Result**: Agent uses accumulated preferences for personalized recommendations

## Learning Pipeline Integration Points

### Integration Point 1: Post-Response Learning
```python
# app.py - chat() function
response_text = extract_response(events)

# Automatic learning after response
preferences.learn_from_conversation(
    user_id=user_id,
    user_message=message,
    response=response_text
)

# Cache invalidation
if user_id in _agent_cache:
    del _agent_cache[user_id]
```

**Timing**: After response generation, before returning to user

### Integration Point 2: Agent Tool Access
```python
# chatbot/agent.py
tools=[
    get_current_weather,
    get_weather_forecast,
    get_user_preferences,  # Agent can query preferences
    update_user_preferences_from_insight,  # Agent can update preferences
]
```

**Timing**: During agent execution, when agent decides to use tools

### Integration Point 3: Agent Creation
```python
# chatbot/agent.py - create_agent_with_preferences()
prefs_summary = preferences.get_preferences_summary(user_id)
instruction = get_agent_instruction(prefs_summary)
agent = Agent(instruction=instruction, ...)
```

**Timing**: On agent creation/cache miss, preferences embedded in instruction

## Learning Metrics and Tracking

### Metrics Tracked

1. **Learning Counter**: `learned_from_conversations`
   - Incremented on each preference update
   - Tracks total learning events

2. **Last Updated**: `last_updated`
   - ISO timestamp of last preference change
   - Used for cache invalidation

3. **Conversation History**: `conversation_history`
   - Last 50 conversations stored
   - Includes user message and response
   - Enables future analysis

### Learning Effectiveness

The system tracks learning through:
- Number of preferences learned
- Timestamp of last update
- Conversation history length
- Preference summary richness

## Limitations and Future Enhancements

### Current Limitations

1. **Keyword-Based Learning**
   - Limited to predefined patterns
   - May miss nuanced preferences
   - Language-specific (English only)

2. **No Preference Confidence**
   - Binary preference values (True/False)
   - No confidence scores
   - Can't track preference strength

3. **No Preference Decay**
   - Preferences never expire
   - No mechanism to "forget" outdated preferences
   - No temporal weighting

4. **Limited Context**
   - Only uses current message
   - Doesn't analyze conversation patterns
   - No multi-turn preference inference

### Future Enhancement Opportunities

1. **LLM-Based Preference Extraction**
   - Use LLM to extract preferences from entire conversation
   - More nuanced understanding
   - Multi-language support

2. **Confidence Scoring**
   - Track preference confidence levels
   - Weight recommendations by confidence
   - Handle conflicting preferences

3. **Temporal Learning**
   - Preference decay over time
   - Seasonal preference tracking
   - Learning from preference changes

4. **Conversation Pattern Analysis**
   - Analyze conversation history for patterns
   - Detect preference changes over time
   - Identify preference clusters

5. **Explicit Preference Confirmation**
   - Ask user to confirm learned preferences
   - Allow user to correct preferences
   - Preference management UI

6. **Multi-Modal Learning**
   - Learn from user actions (not just words)
   - Analyze response acceptance
   - Track recommendation effectiveness

## Conclusion

The learning capability provides a robust foundation for personalization:

- **Dual-Mode Learning**: Combines automatic and agent-driven learning
- **Persistent Storage**: Preferences survive across sessions
- **Agent Integration**: Preferences embedded in agent instructions
- **Conversation History**: Enables future analysis
- **Cache Invalidation**: Ensures fresh preferences

The system learns continuously from every conversation, building a comprehensive user preference profile that enhances the personalization of weather recommendations.

