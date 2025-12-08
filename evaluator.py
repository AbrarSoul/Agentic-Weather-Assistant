"""Evaluation module for comparing chatbot performance metrics."""

import re
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime


class ChatbotEvaluator:
    """Evaluates chatbot responses on multiple metrics."""
    
    def __init__(self, weather_service=None):
        """Initialize evaluator with optional weather service for accuracy checks."""
        self.weather_service = weather_service
        # Framework characteristics for developer experience metrics
        self._framework_characteristics = self._load_framework_characteristics()
    
    def evaluate_response(
        self, 
        user_query: str, 
        response: str, 
        framework_name: str,
        weather_data_used: Optional[Dict] = None,
        conversation_history: Optional[list] = None,
        user_preferences: Optional[Dict] = None,
        response_time: Optional[float] = None,
        tool_call_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a chatbot response on multiple metrics.
        
        Args:
            user_query: Current user query
            response: Agent's response
            framework_name: Name of the framework (GADK or MS)
            weather_data_used: Weather data used in the response
            conversation_history: List of previous conversation turns
            user_preferences: Current user preferences dictionary
            response_time: Time taken to generate response in seconds
            tool_call_count: Number of tool/API calls made
        
        Returns:
            Dictionary with metrics: accuracy, task_completion, recommendation_quality,
            context_retention, adaptation_quality, response_time, tool_call_count,
            action_planning, error_recovery, implementation_effort, integration_simplicity,
            debuggability, ambiguity_handling, repeatability
        """
        metrics = {
            'accuracy': self._evaluate_accuracy(response, weather_data_used, user_query),
            'task_completion': self._evaluate_task_completion(user_query, response),
            'recommendation_quality': self._evaluate_recommendation_quality(response, user_query),
            'context_retention': self._evaluate_context_retention(user_query, response, conversation_history),
            'adaptation_quality': self._evaluate_adaptation_quality(response, user_query, user_preferences),
            'response_time': self._evaluate_response_time(response_time),
            'tool_call_count': self._evaluate_tool_call_count(tool_call_count),
            'action_planning': self._evaluate_action_planning(user_query, response, weather_data_used, tool_call_count),
            'error_recovery': self._evaluate_error_recovery(user_query, response, weather_data_used),
            'implementation_effort': self._evaluate_implementation_effort(framework_name),
            'integration_simplicity': self._evaluate_integration_simplicity(framework_name),
            'debuggability': self._evaluate_debuggability(framework_name, response),
            'ambiguity_handling': self._evaluate_ambiguity_handling(user_query, response, conversation_history),
            'repeatability': self._evaluate_repeatability(user_query, response, conversation_history)
        }
        
        return metrics
    
    def _evaluate_accuracy(
        self, 
        response: str, 
        weather_data: Optional[Dict], 
        user_query: str
    ) -> Dict[str, Any]:
        """
        Evaluate accuracy by comparing response against ground truth weather data.
        
        Returns:
            Dictionary with accuracy_score (0-1) and details
        """
        if not weather_data:
            # No ground truth available, return neutral score
            return {
                'score': 0.5,
                'details': 'No weather data available for comparison',
                'factual_errors': []
            }
        
        score = 1.0
        factual_errors = []
        response_lower = response.lower()
        
        # Extract temperature from response
        temp_patterns = [
            r'(\d+(?:\.\d+)?)\s*°?c',
            r'(\d+(?:\.\d+)?)\s*degrees?\s*(?:celsius|centigrade)',
            r'temperature[:\s]+(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*°'
        ]
        
        # Check current weather accuracy
        if 'current' in weather_data:
            current = weather_data['current']
            actual_temp = current.get('temperature', None)
            
            if actual_temp is not None:
                # Try to extract temperature from response
                found_temp = None
                for pattern in temp_patterns:
                    match = re.search(pattern, response_lower)
                    if match:
                        try:
                            found_temp = float(match.group(1))
                            break
                        except (ValueError, IndexError):
                            continue
                
                if found_temp is not None:
                    # Allow ±2°C tolerance
                    temp_diff = abs(found_temp - actual_temp)
                    if temp_diff > 2:
                        score -= 0.3
                        factual_errors.append(
                            f"Temperature mismatch: said {found_temp}°C, actual {actual_temp}°C"
                        )
                    elif temp_diff > 1:
                        score -= 0.1
                        factual_errors.append(
                            f"Temperature slightly off: said {found_temp}°C, actual {actual_temp}°C"
                        )
        
        # Check condition accuracy
        if 'current' in weather_data:
            actual_condition = weather_data['current'].get('main_condition', '').lower()
            condition_keywords = {
                'rain': ['rain', 'rainy', 'drizzle', 'shower', 'precipitation'],
                'clear': ['clear', 'sunny', 'sun', 'bright'],
                'clouds': ['cloud', 'cloudy', 'overcast', 'clouds'],
                'snow': ['snow', 'snowy', 'snowing', 'snowfall'],
                'mist': ['mist', 'fog', 'foggy', 'haze'],
                'thunderstorm': ['thunder', 'storm', 'thunderstorm', 'lightning']
            }
            
            if actual_condition:
                expected_keywords = condition_keywords.get(actual_condition, [])
                if expected_keywords:
                    has_condition = any(kw in response_lower for kw in expected_keywords)
                    if not has_condition:
                        score -= 0.2
                        factual_errors.append(
                            f"Missing weather condition: should mention {actual_condition}"
                        )
        
        # Check forecast accuracy if forecast data available
        # Handle both 'daily_summaries' and 'detailed_forecast' structures
        has_forecast_data = 'daily_summaries' in weather_data or 'detailed_forecast' in weather_data
        
        if has_forecast_data:
            # Check if response mentions forecast information
            forecast_keywords = ['forecast', 'tomorrow', 'week', 'upcoming', 'next', 'future']
            has_forecast_mention = any(kw in response_lower for kw in forecast_keywords)
            
            if any(kw in user_query.lower() for kw in forecast_keywords):
                if not has_forecast_mention:
                    score -= 0.2
                    factual_errors.append("Forecast query not addressed")
        
        score = max(0.0, min(1.0, score))  # Clamp between 0 and 1
        
        return {
            'score': round(score, 2),
            'details': f"{len(factual_errors)} factual issue(s) found" if factual_errors else "No factual errors detected",
            'factual_errors': factual_errors
        }
    
    def _evaluate_task_completion(self, user_query: str, response: str) -> Dict[str, Any]:
        """
        Evaluate if the task was successfully completed.
        
        Returns:
            Dictionary with completion_score (0-1) and details
        """
        query_lower = user_query.lower()
        response_lower = response.lower()
        
        # Check for error messages
        error_indicators = [
            'error', 'sorry', 'couldn\'t', "can't", 'unable', 
            'failed', 'not available', 'not found', 'could not',
            'i\'m sorry', 'apologize'
        ]
        
        has_error = any(indicator in response_lower for indicator in error_indicators)
        if has_error and len(response) < 100:  # Short error message
            return {
                'score': 0.2,
                'completed': False,
                'details': 'Error message detected'
            }
        
        # Check if response is empty or too short
        if len(response.strip()) < 20:
            return {
                'score': 0.1,
                'completed': False,
                'details': 'Response too short or empty'
            }
        
        # Check if response addresses weather-related queries
        weather_keywords = [
            'weather', 'temperature', 'forecast', 'rain', 'sunny', 
            'wind', 'humidity', 'umbrella', 'jacket', 'temp', 'degrees'
        ]
        
        query_is_weather = any(kw in query_lower for kw in weather_keywords)
        if query_is_weather:
            # Check if response contains relevant weather information
            has_weather_info = any(kw in response_lower for kw in weather_keywords)
            if not has_weather_info:
                return {
                    'score': 0.4,
                    'completed': False,
                    'details': 'Weather query not properly addressed'
                }
        
        # Check if response contains numbers (likely has factual data)
        has_numbers = bool(re.search(r'\d+', response))
        
        # Check if response provides recommendations or actionable advice
        recommendation_keywords = [
            'recommend', 'suggest', 'should', 'umbrella', 'jacket', 
            'outdoor', 'indoor', 'wear', 'bring', 'advise', 'consider'
        ]
        has_recommendations = any(kw in response_lower for kw in recommendation_keywords)
        
        # Calculate completion score
        score = 0.5  # Base score
        
        if has_numbers:
            score += 0.2
        if has_recommendations:
            score += 0.2
        if len(response) > 100:  # Substantial response
            score += 0.1
        
        score = min(1.0, score)
        
        return {
            'score': round(score, 2),
            'completed': score >= 0.7,
            'details': 'Task completed' if score >= 0.7 else 'Task partially completed'
        }
    
    def _evaluate_recommendation_quality(self, response: str, user_query: str) -> Dict[str, Any]:
        """
        Evaluate the quality of recommendations in the response.
        
        Returns:
            Dictionary with quality_score (0-1) and details
        """
        response_lower = response.lower()
        query_lower = user_query.lower()
        
        # Check for recommendation keywords
        recommendation_keywords = [
            'recommend', 'suggest', 'should', 'advise', 'consider',
            'umbrella', 'jacket', 'coat', 'sweater', 'raincoat',
            'outdoor', 'indoor', 'wear', 'bring', 'take', 'prepare'
        ]
        
        has_recommendations = any(kw in response_lower for kw in recommendation_keywords)
        
        if not has_recommendations:
            # Check if query asks for recommendations
            asks_for_recommendation = any(kw in query_lower for kw in [
                'should', 'recommend', 'suggest', 'what should', 'what to wear',
                'umbrella', 'jacket', 'outdoor', 'indoor', 'advice', 'help'
            ])
            
            if asks_for_recommendation:
                return {
                    'score': 0.2,
                    'details': 'Recommendations requested but not provided',
                    'has_recommendations': False
                }
            else:
                return {
                    'score': 0.5,
                    'details': 'No recommendations needed for this query',
                    'has_recommendations': False
                }
        
        # Evaluate recommendation quality
        score = 0.5  # Base score for having recommendations
        
        # Check for specific actionable items
        specific_items = ['umbrella', 'jacket', 'coat', 'sweater', 'raincoat', 'boots', 'hat', 'gloves']
        has_specific_items = any(item in response_lower for item in specific_items)
        if has_specific_items:
            score += 0.2
        
        # Check for clear reasoning
        reasoning_keywords = ['because', 'due to', 'since', 'as', 'given that', 'considering']
        has_reasoning = any(kw in response_lower for kw in reasoning_keywords)
        if has_reasoning:
            score += 0.2
        
        # Check for multiple recommendations (more helpful)
        recommendation_count = sum(1 for kw in recommendation_keywords if kw in response_lower)
        if recommendation_count >= 3:
            score += 0.1
        
        score = min(1.0, score)
        
        return {
            'score': round(score, 2),
            'details': f'High quality recommendations with {recommendation_count} suggestions' if score >= 0.8 else 'Basic recommendations provided',
            'has_recommendations': True,
            'recommendation_count': recommendation_count
        }
    
    def _evaluate_context_retention(
        self, 
        user_query: str, 
        response: str, 
        conversation_history: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Evaluate whether the agent remembers previous information from the conversation.
        
        Returns:
            Dictionary with retention_score (0-1) and details
        """
        if not conversation_history or len(conversation_history) == 0:
            # No conversation history, can't evaluate retention
            return {
                'score': 0.5,
                'details': 'No conversation history available for context retention evaluation',
                'retained_items': []
            }
        
        score = 0.5  # Base score
        retained_items = []
        response_lower = response.lower()
        query_lower = user_query.lower()
        
        # Extract entities from conversation history
        mentioned_cities = set()
        mentioned_preferences = set()
        mentioned_dates = set()
        
        for turn in conversation_history:
            if isinstance(turn, dict):
                # Handle both formats: {'user': '...'} and {'user_message': '...'}
                user_msg = turn.get('user', turn.get('user_message', '')).lower()
                # Extract cities
                city_patterns = [
                    r'\b(dhaka|helsinki|tampere|stockholm|copenhagen|oslo|reykjavik|oulu|new york|london|paris|tokyo)\b',
                    r'in\s+([A-Z][a-z]+)',
                    r'([A-Z][a-z]+)\s+(?:today|tomorrow|weather)'
                ]
                for pattern in city_patterns:
                    matches = re.findall(pattern, user_msg, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            mentioned_cities.add(match[0].title())
                        else:
                            mentioned_cities.add(match.title())
                
                # Extract preferences
                if any(kw in user_msg for kw in ['prefer', 'like', 'dislike', 'hate', 'love', 'favorite']):
                    if 'cold' in user_msg or 'warm' in user_msg:
                        mentioned_preferences.add('temperature_preference')
                    if 'rain' in user_msg or 'sunny' in user_msg:
                        mentioned_preferences.add('weather_preference')
                    if 'outdoor' in user_msg or 'indoor' in user_msg:
                        mentioned_preferences.add('activity_preference')
                
                # Extract dates/days
                days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 
                       'today', 'tomorrow', 'friday', 'saturday', 'sunday']
                for day in days:
                    if day in user_msg:
                        mentioned_dates.add(day)
        
        # Check if response references previously mentioned cities
        if mentioned_cities:
            city_mentioned = any(city.lower() in response_lower for city in mentioned_cities)
            if city_mentioned:
                score += 0.2
                retained_items.append('city')
            else:
                # Check if current query mentions a city but response doesn't reference it
                current_city_mentioned = any(city.lower() in query_lower for city in mentioned_cities)
                if current_city_mentioned:
                    score -= 0.1
        
        # Check if response references previously mentioned preferences
        if mentioned_preferences:
            # Check if response shows preference awareness
            has_pref_keywords = ('prefer' in response_lower or 'like' in response_lower or 
                                'recommend' in response_lower)
            has_pref_context = ('temperature' in response_lower or 'weather' in response_lower or 
                               'outdoor' in response_lower or 'indoor' in response_lower)
            pref_mentioned = has_pref_keywords and has_pref_context
            if pref_mentioned:
                score += 0.15
                retained_items.append('preferences')
        
        # Check if response references previously mentioned dates
        if mentioned_dates:
            date_mentioned = any(day in response_lower for day in mentioned_dates)
            if date_mentioned:
                score += 0.15
                retained_items.append('date/time')
        
        score = max(0.0, min(1.0, score))
        
        details = f"Retained {len(retained_items)} context item(s): {', '.join(retained_items)}" if retained_items else "Limited context retention detected"
        
        return {
            'score': round(score, 2),
            'details': details,
            'retained_items': retained_items
        }
    
    def _evaluate_adaptation_quality(
        self, 
        response: str, 
        user_query: str,
        user_preferences: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Evaluate whether the agent adjusts behavior based on learned user preferences.
        
        Returns:
            Dictionary with adaptation_score (0-1) and details
        """
        if not user_preferences:
            return {
                'score': 0.5,
                'details': 'No user preferences available for adaptation evaluation',
                'adaptations_detected': []
            }
        
        score = 0.5  # Base score
        adaptations_detected = []
        response_lower = response.lower()
        
        # Check if preferences indicate dislikes - handle both GADK and MS preference structures
        learned_prefs = {}
        
        # GADK structure
        if 'temperature_preferences' in user_preferences:
            temp_prefs = user_preferences.get('temperature_preferences', {})
            if temp_prefs.get('dislikes_cold', False):
                learned_prefs['dislikes_cold'] = True
            if temp_prefs.get('dislikes_heat', False):
                learned_prefs['dislikes_heat'] = True
        
        if 'weather_preferences' in user_preferences:
            weather_prefs = user_preferences.get('weather_preferences', {})
            if weather_prefs.get('dislikes_rain', False):
                learned_prefs['dislikes_rain'] = True
            if weather_prefs.get('prefers_indoor', False):
                learned_prefs['prefers_indoor'] = True
        
        if 'activity_preferences' in user_preferences:
            activity_prefs = user_preferences.get('activity_preferences', {})
            if activity_prefs.get('outdoor_activities', False):
                learned_prefs['outdoor_activities'] = True
        
        # MS structure
        if 'weather_conditions' in user_preferences:
            weather_conds = user_preferences.get('weather_conditions', {})
            if weather_conds.get('dislikes_cold', False):
                learned_prefs['dislikes_cold'] = True
            if weather_conds.get('dislikes_rain', False):
                learned_prefs['dislikes_rain'] = True
        
        if 'activity_preferences' in user_preferences:
            activity_prefs = user_preferences.get('activity_preferences', {})
            if activity_prefs.get('prefers_indoor', False):
                learned_prefs['prefers_indoor'] = True
        
        # Check learned_from_conversations for both structures
        if user_preferences.get('learned_from_conversations', 0) == 0:
            return {
                'score': 0.5,
                'details': 'No learned preferences available',
                'adaptations_detected': []
            }
        
        # Check for cold weather preference adaptation
        if learned_prefs.get('dislikes_cold', False):
            # Check if response acknowledges cold preference
            if any(kw in response_lower for kw in ['warm', 'warmer', 'jacket', 'coat', 'layers']):
                if 'cold' in response_lower or 'freezing' in response_lower:
                    score += 0.15
                    adaptations_detected.append('cold_weather_adaptation')
        
        # Check for rain preference adaptation
        if learned_prefs.get('dislikes_rain', False):
            # Check if response mentions umbrella or indoor activities when rain is expected
            if 'rain' in response_lower or 'rainy' in response_lower:
                if 'umbrella' in response_lower or 'indoor' in response_lower:
                    score += 0.15
                    adaptations_detected.append('rain_adaptation')
        
        # Check for outdoor/indoor preference adaptation
        if learned_prefs.get('prefers_indoor', False):
            if 'indoor' in response_lower and 'outdoor' not in response_lower:
                score += 0.15
                adaptations_detected.append('indoor_preference_adaptation')
        elif learned_prefs.get('outdoor_activities', False):
            if 'outdoor' in response_lower:
                score += 0.15
                adaptations_detected.append('outdoor_preference_adaptation')
        
        # Check for heat preference adaptation
        if learned_prefs.get('dislikes_heat', False):
            if any(kw in response_lower for kw in ['cool', 'shade', 'indoor', 'air conditioning']):
                score += 0.1
                adaptations_detected.append('heat_adaptation')
        
        # Check if response shows awareness of preferences
        if any(kw in response_lower for kw in ['prefer', 'preference', 'remember', 'based on', 'considering']):
            score += 0.1
            adaptations_detected.append('preference_awareness')
        
        score = max(0.0, min(1.0, score))
        
        details = f"Detected {len(adaptations_detected)} adaptation(s)" if adaptations_detected else "Limited adaptation to user preferences"
        
        return {
            'score': round(score, 2),
            'details': details,
            'adaptations_detected': adaptations_detected
        }
    
    def _evaluate_response_time(self, response_time: Optional[float]) -> Dict[str, Any]:
        """
        Evaluate response time efficiency.
        
        Returns:
            Dictionary with time_score (0-1) and details
        """
        if response_time is None:
            return {
                'score': 0.5,
                'time_seconds': None,
                'details': 'Response time not available',
                'efficiency_level': 'unknown'
            }
        
        # Score based on response time (lower is better)
        # Excellent: < 2 seconds (score: 1.0)
        # Good: 2-5 seconds (score: 0.8-0.9)
        # Acceptable: 5-10 seconds (score: 0.6-0.7)
        # Slow: > 10 seconds (score: 0.3-0.5)
        
        if response_time < 2.0:
            score = 1.0
            efficiency_level = 'excellent'
        elif response_time < 5.0:
            # Linear interpolation: 2s = 0.9, 5s = 0.7
            score = 0.9 - ((response_time - 2.0) / 3.0) * 0.2
            efficiency_level = 'good'
        elif response_time < 10.0:
            # Linear interpolation: 5s = 0.7, 10s = 0.5
            score = 0.7 - ((response_time - 5.0) / 5.0) * 0.2
            efficiency_level = 'acceptable'
        else:
            # Very slow: > 10 seconds
            score = max(0.3, 0.5 - ((response_time - 10.0) / 10.0) * 0.2)
            efficiency_level = 'slow'
        
        score = max(0.0, min(1.0, score))
        
        return {
            'score': round(score, 2),
            'time_seconds': round(response_time, 2),
            'details': f'Response time: {response_time:.2f}s ({efficiency_level})',
            'efficiency_level': efficiency_level
        }
    
    def _evaluate_tool_call_count(self, tool_call_count: Optional[int]) -> Dict[str, Any]:
        """
        Evaluate efficiency based on tool call count.
        
        Returns:
            Dictionary with efficiency_score (0-1) and details
        """
        if tool_call_count is None:
            return {
                'score': 0.5,
                'count': None,
                'details': 'Tool call count not available',
                'efficiency_level': 'unknown'
            }
        
        # Score based on tool call efficiency (fewer calls = more efficient, but need at least 1 for weather queries)
        # Optimal: 1-2 calls (score: 1.0) - Direct and efficient
        # Good: 3-4 calls (score: 0.8) - Reasonable
        # Acceptable: 5-6 calls (score: 0.6) - Some redundancy
        # Inefficient: > 6 calls (score: 0.4) - Too many calls
        
        if tool_call_count == 0:
            # No tool calls might mean no weather data fetched (could be good or bad)
            score = 0.5
            efficiency_level = 'no_calls'
        elif tool_call_count <= 2:
            score = 1.0
            efficiency_level = 'optimal'
        elif tool_call_count <= 4:
            score = 0.8
            efficiency_level = 'good'
        elif tool_call_count <= 6:
            score = 0.6
            efficiency_level = 'acceptable'
        else:
            score = 0.4
            efficiency_level = 'inefficient'
        
        return {
            'score': round(score, 2),
            'count': tool_call_count,
            'details': f'{tool_call_count} tool call(s) ({efficiency_level})',
            'efficiency_level': efficiency_level
        }
    
    def _evaluate_action_planning(
        self,
        user_query: str,
        response: str,
        weather_data_used: Optional[Dict],
        tool_call_count: Optional[int]
    ) -> Dict[str, Any]:
        """
        Evaluate how well the agent decides the correct sequence of actions.
        
        Assesses:
        - Whether appropriate tools were used for the task
        - Whether the response shows logical sequencing (e.g., checking weather before recommendations)
        - Whether tool calls were made in appropriate sequence
        - Whether the agent used the right tools for the task
        
        Returns:
            Dictionary with planning_score (0-1) and details
        """
        query_lower = user_query.lower()
        response_lower = response.lower()
        score = 0.0
        planning_issues = []
        planning_strengths = []
        
        # Check if weather-related query
        weather_keywords = ['weather', 'temperature', 'forecast', 'rain', 'sunny', 
                           'wind', 'humidity', 'umbrella', 'jacket', 'temp', 'degrees',
                           'outdoor', 'activity', 'plan']
        is_weather_query = any(kw in query_lower for kw in weather_keywords)
        
        if is_weather_query:
            # Check if weather data was used when needed
            if weather_data_used:
                planning_strengths.append('Weather data retrieved appropriately')
                score += 0.3
            else:
                # Check if response acknowledges missing data
                if any(phrase in response_lower for phrase in ['unable to get', 'could not retrieve', 
                                                                 'weather data not available', 'no weather data']):
                    planning_strengths.append('Acknowledged missing weather data')
                    score += 0.15
                else:
                    planning_issues.append('Weather query but no weather data used')
            
            # Check if recommendations follow weather information (logical sequence)
            # Look for pattern: weather info -> recommendations
            has_weather_info = any(kw in response_lower for kw in ['°c', '°f', 'degrees', 'temperature', 
                                                                     'humidity', 'wind speed', 'forecast'])
            has_recommendations = any(kw in response_lower for kw in ['recommend', 'suggest', 'should', 
                                                                      'umbrella', 'jacket', 'wear', 'bring'])
            
            if has_weather_info and has_recommendations:
                # Check if recommendations come after weather info (rough check)
                weather_pos = response_lower.find('temperature') or response_lower.find('degrees') or response_lower.find('°')
                rec_pos = response_lower.find('recommend') or response_lower.find('suggest') or response_lower.find('should')
                
                if weather_pos != -1 and rec_pos != -1 and rec_pos > weather_pos:
                    planning_strengths.append('Logical sequence: weather info before recommendations')
                    score += 0.3
                elif weather_pos != -1 and rec_pos != -1:
                    planning_strengths.append('Both weather info and recommendations present')
                    score += 0.2
            elif has_weather_info:
                planning_strengths.append('Weather information provided')
                score += 0.2
            elif has_recommendations and not weather_data_used:
                planning_issues.append('Recommendations without weather data')
        
        # Check tool call appropriateness
        if tool_call_count is not None:
            if is_weather_query:
                if tool_call_count > 0:
                    planning_strengths.append('Appropriate tool usage for weather query')
                    score += 0.2
                else:
                    planning_issues.append('No tool calls for weather query')
            else:
                # Non-weather query - tool calls might not be needed
                if tool_call_count == 0:
                    planning_strengths.append('No unnecessary tool calls')
                    score += 0.1
        
        # Check for logical flow indicators
        flow_indicators = ['first', 'then', 'next', 'after', 'based on', 'according to']
        has_flow = any(indicator in response_lower for indicator in flow_indicators)
        if has_flow:
            planning_strengths.append('Response shows logical flow')
            score += 0.1
        
        # Normalize score to 0-1 range
        score = min(1.0, score)
        
        # If no issues and has strengths, boost score
        if not planning_issues and planning_strengths:
            score = max(score, 0.8)
        
        # Generate details
        if planning_strengths and not planning_issues:
            details = f"Good planning: {', '.join(planning_strengths[:2])}"
        elif planning_issues:
            details = f"Issues: {', '.join(planning_issues[:2])}"
        else:
            details = "Basic planning observed"
        
        return {
            'score': round(score, 2),
            'details': details,
            'strengths': planning_strengths,
            'issues': planning_issues
        }
    
    def _evaluate_error_recovery(
        self,
        user_query: str,
        response: str,
        weather_data_used: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        Evaluate how well the agent handles API errors, missing info, or ambiguity.
        
        Assesses:
        - Whether errors are handled gracefully
        - Whether missing information is acknowledged
        - Whether fallback suggestions are provided
        - Whether error messages are informative
        
        Returns:
            Dictionary with recovery_score (0-1) and details
        """
        response_lower = response.lower()
        score = 0.5  # Start with neutral score
        recovery_strengths = []
        recovery_issues = []
        
        # Check for error indicators
        error_phrases = [
            'error', 'failed', 'unable', "can't", "couldn't", 'not available',
            'not found', 'could not', "i'm sorry", 'apologize', 'sorry'
        ]
        has_error_indicators = any(phrase in response_lower for phrase in error_phrases)
        
        if has_error_indicators:
            # Check if error is handled gracefully
            graceful_indicators = [
                'however', 'but', 'alternatively', 'you could', 'you might',
                'suggest', 'recommend', 'try', 'consider', 'instead'
            ]
            has_graceful_handling = any(indicator in response_lower for indicator in graceful_indicators)
            
            if has_graceful_handling:
                recovery_strengths.append('Error handled with alternatives')
                score += 0.3
            else:
                # Check if error message is informative
                if len(response) > 50:  # Not just a short error message
                    recovery_strengths.append('Detailed error explanation')
                    score += 0.2
                else:
                    recovery_issues.append('Brief error message without alternatives')
                    score -= 0.2
        
        # Check for missing data handling
        if weather_data_used is None:
            # Check if response acknowledges missing data
            missing_data_phrases = [
                'unable to get', 'could not retrieve', 'weather data not available',
                'no weather data', 'weather information unavailable', 'could not fetch'
            ]
            acknowledges_missing = any(phrase in response_lower for phrase in missing_data_phrases)
            
            if acknowledges_missing:
                recovery_strengths.append('Acknowledged missing data')
                score += 0.2
                
                # Check if provides alternatives despite missing data
                alternative_phrases = [
                    'generally', 'typically', 'usually', 'in general', 'you might want',
                    'consider', 'suggest', 'recommend', 'could', 'may want'
                ]
                provides_alternatives = any(phrase in response_lower for phrase in alternative_phrases)
                
                if provides_alternatives:
                    recovery_strengths.append('Provided alternatives despite missing data')
                    score += 0.3
            else:
                # Check if query requires weather data
                weather_keywords = ['weather', 'temperature', 'forecast', 'rain', 'sunny']
                requires_weather = any(kw in user_query.lower() for kw in weather_keywords)
                
                if requires_weather:
                    recovery_issues.append('Missing weather data not acknowledged')
                    score -= 0.2
        
        # Check for ambiguity handling
        ambiguity_indicators = [
            'could you clarify', 'could you specify', 'which city', 'which location',
            'please provide', 'need more information', 'to better assist'
        ]
        handles_ambiguity = any(indicator in response_lower for indicator in ambiguity_indicators)
        
        if handles_ambiguity:
            recovery_strengths.append('Asks for clarification when needed')
            score += 0.2
        
        # Check for fallback suggestions
        fallback_indicators = [
            'you could try', 'alternatively', 'another option', 'you might',
            'consider', 'suggest', 'recommend', 'option'
        ]
        has_fallbacks = any(indicator in response_lower for indicator in fallback_indicators)
        
        if has_fallbacks and has_error_indicators:
            recovery_strengths.append('Provides fallback options')
            score += 0.2
        
        # Normalize score to 0-1 range
        score = max(0.0, min(1.0, score))
        
        # Generate details
        if recovery_strengths and not recovery_issues:
            details = f"Good recovery: {', '.join(recovery_strengths[:2])}"
        elif recovery_issues:
            details = f"Recovery issues: {', '.join(recovery_issues[:2])}"
        elif not has_error_indicators and weather_data_used:
            details = "No errors encountered"
            score = 1.0  # Perfect if no errors and data available
        else:
            details = "Basic error handling"
        
        return {
            'score': round(score, 2),
            'details': details,
            'strengths': recovery_strengths,
            'issues': recovery_issues
        }
    
    def _load_framework_characteristics(self) -> Dict[str, Dict[str, Any]]:
        """Load framework characteristics for developer experience evaluation."""
        return {
            'GADK': {
                'files_count': 5,  # app.py, agent.py, preferences.py, weather_tools.py, etc.
                'setup_complexity': 'medium',  # Requires ADK installation, session service setup
                'tool_integration_files': 2,  # Need to modify agent.py and create tool file
                'memory_integration': 'built_in',  # Session service built-in
                'error_handling': 'framework_managed',  # ADK handles errors
                'logging': 'framework_provided',  # ADK provides logging
                'code_complexity': 'medium',  # More abstraction layers
                'documentation': 'comprehensive'  # ADK has good docs
            },
            'MS': {
                'files_count': 4,  # app.py, weather_service.py, weather_helper.py, preferences_manager.py
                'setup_complexity': 'low',  # Simple Flask + OpenAI setup
                'tool_integration_files': 1,  # Just add service and helper
                'memory_integration': 'manual',  # Manual JSON storage
                'error_handling': 'manual',  # Manual try-catch blocks
                'logging': 'basic',  # Basic print statements
                'code_complexity': 'low',  # Direct, straightforward code
                'documentation': 'moderate'  # Code is self-explanatory
            }
        }
    
    def _evaluate_implementation_effort(self, framework_name: str) -> Dict[str, Any]:
        """
        Evaluate how difficult it is to implement the same use case in each framework.
        
        Considers:
        - Number of files needed
        - Setup complexity
        - Code complexity
        - Learning curve
        
        Returns:
            Dictionary with effort_score (0-1, higher is easier) and details
        """
        if framework_name not in self._framework_characteristics:
            return {
                'score': 0.5,
                'details': 'Framework not recognized',
                'effort_level': 'unknown'
            }
        
        chars = self._framework_characteristics[framework_name]
        score = 0.5  # Start neutral
        
        # Files count (fewer files = easier)
        if chars['files_count'] <= 3:
            score -= 0.2
        elif chars['files_count'] >= 6:
            score += 0.2
        
        # Setup complexity
        if chars['setup_complexity'] == 'low':
            score -= 0.15
        elif chars['setup_complexity'] == 'high':
            score += 0.15
        
        # Code complexity
        if chars['code_complexity'] == 'low':
            score -= 0.15
        elif chars['code_complexity'] == 'high':
            score += 0.15
        
        # Normalize to 0-1 (invert so lower score = easier implementation)
        score = max(0.0, min(1.0, score))
        # Invert: 0.0 = very easy, 1.0 = very hard
        # But we want: higher score = easier, so invert
        inverted_score = 1.0 - score
        
        if inverted_score >= 0.8:
            effort_level = 'very easy'
        elif inverted_score >= 0.6:
            effort_level = 'easy'
        elif inverted_score >= 0.4:
            effort_level = 'moderate'
        elif inverted_score >= 0.2:
            effort_level = 'difficult'
        else:
            effort_level = 'very difficult'
        
        details = f"{chars['files_count']} files, {chars['setup_complexity']} setup ({effort_level})"
        
        return {
            'score': round(inverted_score, 2),
            'details': details,
            'effort_level': effort_level,
            'files_count': chars['files_count'],
            'setup_complexity': chars['setup_complexity']
        }
    
    def _evaluate_integration_simplicity(self, framework_name: str) -> Dict[str, Any]:
        """
        Evaluate how easy it is to connect tools, memory, and agents.
        
        Considers:
        - Number of files to modify to add a tool
        - Memory integration approach
        - Agent-tool connection complexity
        
        Returns:
            Dictionary with simplicity_score (0-1, higher is simpler) and details
        """
        if framework_name not in self._framework_characteristics:
            return {
                'score': 0.5,
                'details': 'Framework not recognized',
                'simplicity_level': 'unknown'
            }
        
        chars = self._framework_characteristics[framework_name]
        score = 0.5  # Start neutral
        
        # Tool integration files (fewer = simpler)
        if chars['tool_integration_files'] == 1:
            score += 0.3
        elif chars['tool_integration_files'] == 2:
            score += 0.1
        else:
            score -= 0.2
        
        # Memory integration
        if chars['memory_integration'] == 'built_in':
            score += 0.2
        elif chars['memory_integration'] == 'manual':
            score -= 0.1
        
        # Normalize to 0-1
        score = max(0.0, min(1.0, score))
        
        if score >= 0.8:
            simplicity_level = 'very simple'
        elif score >= 0.6:
            simplicity_level = 'simple'
        elif score >= 0.4:
            simplicity_level = 'moderate'
        elif score >= 0.2:
            simplicity_level = 'complex'
        else:
            simplicity_level = 'very complex'
        
        memory_desc = 'built-in' if chars['memory_integration'] == 'built_in' else 'manual'
        details = f"{chars['tool_integration_files']} file(s) to modify, {memory_desc} memory ({simplicity_level})"
        
        return {
            'score': round(score, 2),
            'details': details,
            'simplicity_level': simplicity_level,
            'tool_files': chars['tool_integration_files'],
            'memory_approach': chars['memory_integration']
        }
    
    def _evaluate_debuggability(self, framework_name: str, response: str) -> Dict[str, Any]:
        """
        Evaluate how clear the logs, errors, and debugging tools are.
        
        Considers:
        - Error message clarity
        - Logging quality
        - Framework debugging support
        
        Returns:
            Dictionary with debuggability_score (0-1, higher is better) and details
        """
        if framework_name not in self._framework_characteristics:
            return {
                'score': 0.5,
                'details': 'Framework not recognized',
                'debuggability_level': 'unknown'
            }
        
        chars = self._framework_characteristics[framework_name]
        score = 0.5  # Start neutral
        
        # Error handling approach
        if chars['error_handling'] == 'framework_managed':
            score += 0.2  # Framework handles errors better
        elif chars['error_handling'] == 'manual':
            score -= 0.1  # Manual handling can be inconsistent
        
        # Logging quality
        if chars['logging'] == 'framework_provided':
            score += 0.2  # Framework logging is usually better
        elif chars['logging'] == 'basic':
            score -= 0.1
        
        # Check response for error clarity
        response_lower = response.lower()
        if 'error:' in response_lower or 'Error:' in response:
            # Check if error is informative
            if len(response) > 50 and any(word in response_lower for word in ['unable', 'could not', 'failed', 'missing']):
                score += 0.1  # Error message is descriptive
            else:
                score -= 0.1  # Error message is too brief
        
        # Documentation helps debugging
        if chars['documentation'] == 'comprehensive':
            score += 0.1
        elif chars['documentation'] == 'moderate':
            score += 0.05
        
        # Normalize to 0-1
        score = max(0.0, min(1.0, score))
        
        if score >= 0.8:
            debuggability_level = 'excellent'
        elif score >= 0.6:
            debuggability_level = 'good'
        elif score >= 0.4:
            debuggability_level = 'moderate'
        elif score >= 0.2:
            debuggability_level = 'poor'
        else:
            debuggability_level = 'very poor'
        
        logging_desc = chars['logging'].replace('_', ' ')
        error_desc = chars['error_handling'].replace('_', ' ')
        details = f"{logging_desc} logging, {error_desc} errors ({debuggability_level})"
        
        return {
            'score': round(score, 2),
            'details': details,
            'debuggability_level': debuggability_level,
            'logging_quality': chars['logging'],
            'error_handling': chars['error_handling']
        }
    
    def _evaluate_ambiguity_handling(
        self,
        user_query: str,
        response: str,
        conversation_history: Optional[list]
    ) -> Dict[str, Any]:
        """
        Evaluate how well the agent manages missing or vague user input.
        
        Assesses:
        - Whether the agent asks for clarification when input is vague
        - Whether it handles missing information gracefully
        - Whether it provides helpful guidance when input is unclear
        - Whether it makes reasonable assumptions when information is missing
        
        Returns:
            Dictionary with ambiguity_score (0-1) and details
        """
        query_lower = user_query.lower()
        response_lower = response.lower()
        score = 0.5  # Start neutral
        handling_strengths = []
        handling_issues = []
        
        # Check if query is ambiguous (missing key information)
        ambiguous_indicators = {
            'missing_location': not any(word in query_lower for word in ['in ', 'at ', 'for ', 'weather', 'city', 'location', 'place']),
            'missing_time': any(word in query_lower for word in ['when', 'what time', 'when is']) and not any(word in query_lower for word in ['today', 'tomorrow', 'friday', 'monday', 'next']),
            'vague_request': len(user_query.split()) < 4 and not any(word in query_lower for word in ['weather', 'temperature', 'forecast']),
            'unclear_intent': not any(word in query_lower for word in ['weather', 'temp', 'forecast', 'rain', 'sunny', 'cold', 'hot', 'umbrella', 'jacket', 'activity', 'plan'])
        }
        
        is_ambiguous = any(ambiguous_indicators.values())
        
        if is_ambiguous:
            # Check if agent asks for clarification
            clarification_phrases = [
                'could you clarify', 'could you specify', 'which city', 'which location',
                'please provide', 'need more information', 'to better assist', 'could you tell me',
                'what city', 'what location', 'where', 'when', 'which', 'please specify'
            ]
            asks_clarification = any(phrase in response_lower for phrase in clarification_phrases)
            
            if asks_clarification:
                handling_strengths.append('Asks for clarification when input is vague')
                score += 0.4
            else:
                # Check if agent makes reasonable assumptions
                assumption_indicators = [
                    'assuming', 'i\'ll assume', 'if you mean', 'probably', 'likely',
                    'typically', 'generally', 'usually', 'most likely'
                ]
                makes_assumptions = any(phrase in response_lower for phrase in assumption_indicators)
                
                if makes_assumptions:
                    handling_strengths.append('Makes reasonable assumptions when information is missing')
                    score += 0.3
                else:
                    # Check if response is still helpful despite ambiguity
                    if len(response) > 100 and any(word in response_lower for word in ['weather', 'temperature', 'forecast', 'recommend']):
                        handling_strengths.append('Provides helpful response despite ambiguity')
                        score += 0.2
                    else:
                        handling_issues.append('Does not handle ambiguous input well')
                        score -= 0.2
        else:
            # Query is clear - check if agent handles it appropriately
            if len(response) > 50 and any(word in response_lower for word in ['weather', 'temperature', 'forecast', 'recommend']):
                handling_strengths.append('Handles clear queries appropriately')
                score += 0.2
        
        # Check for missing location handling
        if ambiguous_indicators['missing_location']:
            location_handling = any(phrase in response_lower for phrase in [
                'which city', 'what city', 'where', 'location', 'city name',
                'please specify the city', 'could you tell me the city'
            ])
            if location_handling:
                handling_strengths.append('Asks for missing location information')
                score += 0.2
            elif not is_ambiguous:  # If query is otherwise clear but missing location
                handling_issues.append('Does not request missing location')
                score -= 0.1
        
        # Check for helpful guidance
        guidance_phrases = [
            'you can ask', 'you might want to', 'for example', 'such as',
            'you could specify', 'to get better results', 'to help you better'
        ]
        provides_guidance = any(phrase in response_lower for phrase in guidance_phrases)
        
        if provides_guidance and is_ambiguous:
            handling_strengths.append('Provides helpful guidance for unclear input')
            score += 0.2
        
        # Normalize score to 0-1
        score = max(0.0, min(1.0, score))
        
        # Generate details
        if handling_strengths and not handling_issues:
            details = f"Good handling: {', '.join(handling_strengths[:2])}"
        elif handling_issues:
            details = f"Issues: {', '.join(handling_issues[:2])}"
        elif not is_ambiguous:
            details = "Query was clear, handled appropriately"
            score = max(score, 0.8)  # Boost score for clear queries
        else:
            details = "Basic ambiguity handling"
        
        return {
            'score': round(score, 2),
            'details': details,
            'strengths': handling_strengths,
            'issues': handling_issues,
            'is_ambiguous': is_ambiguous
        }
    
    def _evaluate_repeatability(
        self,
        user_query: str,
        response: str,
        conversation_history: Optional[list]
    ) -> Dict[str, Any]:
        """
        Evaluate whether the agent gives consistent answers across repeated queries.
        
        Assesses:
        - Consistency with previous similar queries in conversation history
        - Deterministic response patterns
        - Stability of recommendations for similar inputs
        
        Returns:
            Dictionary with repeatability_score (0-1) and details
        """
        response_lower = response.lower()
        score = 0.7  # Start with moderate-high score (assuming consistency)
        consistency_strengths = []
        consistency_issues = []
        
        # Check conversation history for similar queries
        if conversation_history and len(conversation_history) > 0:
            # Extract keywords from current query
            current_keywords = set(word.lower() for word in user_query.split() if len(word) > 3)
            
            similar_queries = []
            for turn in conversation_history:
                if isinstance(turn, dict):
                    prev_query = turn.get('user', turn.get('user_message', ''))
                    if prev_query:
                        prev_keywords = set(word.lower() for word in prev_query.split() if len(word) > 3)
                        # Check similarity (at least 2 common keywords)
                        common_keywords = current_keywords.intersection(prev_keywords)
                        if len(common_keywords) >= 2:
                            similar_queries.append({
                                'query': prev_query,
                                'response': turn.get('assistant', turn.get('response', ''))
                            })
            
            if similar_queries:
                # Compare responses for consistency
                prev_responses = [q['response'].lower() for q in similar_queries]
                
                # Check for consistent patterns
                common_phrases = []
                for prev_resp in prev_responses:
                    # Extract key phrases (temperature mentions, recommendations, etc.)
                    if 'temperature' in prev_resp or 'degrees' in prev_resp:
                        common_phrases.append('temperature_info')
                    if any(word in prev_resp for word in ['recommend', 'suggest', 'should']):
                        common_phrases.append('recommendations')
                    if any(word in prev_resp for word in ['umbrella', 'jacket', 'wear']):
                        common_phrases.append('specific_items')
                
                # Check if current response has similar structure
                has_temperature = 'temperature' in response_lower or 'degrees' in response_lower
                has_recommendations = any(word in response_lower for word in ['recommend', 'suggest', 'should'])
                has_specific_items = any(word in response_lower for word in ['umbrella', 'jacket', 'wear'])
                
                consistency_score = 0.0
                if 'temperature_info' in common_phrases and has_temperature:
                    consistency_score += 0.3
                    consistency_strengths.append('Consistent temperature information')
                if 'recommendations' in common_phrases and has_recommendations:
                    consistency_score += 0.3
                    consistency_strengths.append('Consistent recommendation style')
                if 'specific_items' in common_phrases and has_specific_items:
                    consistency_score += 0.2
                    consistency_strengths.append('Consistent item suggestions')
                
                if consistency_score > 0:
                    score = 0.5 + consistency_score  # Base 0.5 + consistency bonus
                else:
                    consistency_issues.append('Inconsistent with previous similar queries')
                    score -= 0.2
        else:
            # No history to compare - check for deterministic patterns
            # Look for consistent response structure
            has_structure = any(word in response_lower for word in ['weather', 'temperature', 'forecast', 'recommend'])
            if has_structure:
                consistency_strengths.append('Structured response format')
                score += 0.1
        
        # Check for random or non-deterministic elements
        random_indicators = ['random', 'maybe', 'perhaps', 'might be', 'could be different']
        has_random = any(indicator in response_lower for indicator in random_indicators)
        
        if has_random:
            consistency_issues.append('Contains non-deterministic language')
            score -= 0.1
        
        # Check response length consistency (very short or very long might indicate instability)
        if len(response) < 30:
            consistency_issues.append('Very short response (potential instability)')
            score -= 0.1
        elif len(response) > 1000:
            consistency_issues.append('Very long response (potential inconsistency)')
            score -= 0.05
        
        # Normalize score to 0-1
        score = max(0.0, min(1.0, score))
        
        # Generate details
        if consistency_strengths and not consistency_issues:
            details = f"Good consistency: {', '.join(consistency_strengths[:2])}"
        elif consistency_issues:
            details = f"Consistency issues: {', '.join(consistency_issues[:2])}"
        elif conversation_history and len(conversation_history) > 0:
            details = "Consistent with conversation history"
        else:
            details = "No history to compare, appears stable"
        
        return {
            'score': round(score, 2),
            'details': details,
            'strengths': consistency_strengths,
            'issues': consistency_issues
        }

