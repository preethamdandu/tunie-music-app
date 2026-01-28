"""
Advanced Reasoning Engine for TuneGenie AI Insights
Provides chain-of-thought reasoning, multi-step analysis, and explainable AI
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ReasoningEngine:
    """Advanced reasoning capabilities for music recommendations"""
    
    def __init__(self, llm_agent, spotify_client=None):
        """
        Initialize reasoning engine
        
        Args:
            llm_agent: LLM agent for generating reasoning
            spotify_client: Optional Spotify client for data access
        """
        self.llm_agent = llm_agent
        self.spotify_client = spotify_client
        
        # Reasoning modes
        self.reasoning_modes = {
            'analytical': self._analytical_reasoning,
            'creative': self._creative_reasoning,
            'comparative': self._comparative_reasoning,
            'exploratory': self._exploratory_reasoning,
            'diagnostic': self._diagnostic_reasoning
        }
        
        # Intent patterns for classification
        self.intent_patterns = {
            'recommendation': ['recommend', 'suggest', 'what should', 'find me', 'discover'],
            'analysis': ['why', 'analyze', 'explain', 'understand', 'how come'],
            'comparison': ['compare', 'difference', 'versus', 'vs', 'better than'],
            'exploration': ['explore', 'discover', 'new', 'different', 'similar'],
            'information': ['who is', 'what is', 'tell me about', 'information'],
            'diagnostic': ['fix', 'problem', 'issue', 'not working', 'help']
        }
    
    def reason_about_query(self, query: str, context: Dict, show_reasoning: bool = True) -> Dict:
        """
        Multi-step reasoning with explicit thought process
        
        Args:
            query: User's question
            context: User context and data
            show_reasoning: Whether to include reasoning steps in response
        
        Returns:
            Dict with response, reasoning steps, confidence, and sources
        """
        try:
            # Step 1: Classify query intent
            intent = self._classify_intent(query)
            logger.info(f"Query intent classified as: {intent}")
            
            # Step 2: Select reasoning mode
            reasoning_mode = self._select_reasoning_mode(intent)
            logger.info(f"Selected reasoning mode: {reasoning_mode}")
            
            # Step 3: Execute reasoning chain
            reasoning_chain = self.reasoning_modes[reasoning_mode](query, context)
            
            # Step 4: Format response
            response = self._format_reasoning_response(
                reasoning_chain,
                show_reasoning=show_reasoning
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
            return {
                'response': f"I encountered an issue while reasoning about your query: {str(e)}",
                'reasoning_steps': [],
                'confidence': 0.0,
                'sources': [],
                'error': str(e)
            }
    
    def _classify_intent(self, query: str) -> str:
        """Classify the intent of the user's query"""
        query_lower = query.lower()
        
        # Check each intent pattern
        intent_scores = {}
        for intent, patterns in self.intent_patterns.items():
            score = sum(1 for pattern in patterns if pattern in query_lower)
            if score > 0:
                intent_scores[intent] = score
        
        # Return highest scoring intent, or 'general' if none match
        if intent_scores:
            return max(intent_scores.items(), key=lambda x: x[1])[0]
        return 'general'
    
    def _select_reasoning_mode(self, intent: str) -> str:
        """Select appropriate reasoning mode based on intent"""
        mode_mapping = {
            'recommendation': 'creative',
            'analysis': 'analytical',
            'comparison': 'comparative',
            'exploration': 'exploratory',
            'information': 'analytical',
            'diagnostic': 'diagnostic',
            'general': 'analytical'
        }
        return mode_mapping.get(intent, 'analytical')
    
    def _analytical_reasoning(self, query: str, context: Dict) -> Dict:
        """
        Analytical reasoning for music analysis queries
        Example: "Why do I like this artist?"
        """
        steps = []
        
        # Step 1: Gather user data
        steps.append({
            'step': 1,
            'action': 'Analyzing your listening history',
            'description': 'Examining your top tracks, artists, and genres',
            'data_points': len(context.get('top_tracks', {}).get('medium_term', []))
        })
        
        # Step 2: Extract patterns
        patterns = self._extract_listening_patterns(context)
        steps.append({
            'step': 2,
            'action': 'Identifying musical patterns',
            'description': 'Finding common themes in your music preferences',
            'patterns': patterns
        })
        
        # Step 3: Analyze features
        features = self._extract_musical_features(context)
        steps.append({
            'step': 3,
            'action': 'Analyzing musical characteristics',
            'description': 'Understanding the audio features you prefer',
            'features': features
        })
        
        # Step 4: Generate insights
        insights = self._generate_analytical_insights(query, patterns, features)
        steps.append({
            'step': 4,
            'action': 'Synthesizing insights',
            'description': 'Combining patterns and features into actionable insights',
            'insights': insights
        })
        
        return {
            'steps': steps,
            'conclusion': insights['conclusion'],
            'confidence': insights['confidence'],
            'sources': ['user_profile', 'listening_history', 'audio_features'],
            'reasoning_type': 'analytical'
        }
    
    def _creative_reasoning(self, query: str, context: Dict) -> Dict:
        """
        Creative reasoning for recommendation queries
        Example: "Suggest music for a rainy day"
        """
        steps = []
        
        # Step 1: Understand the request
        request_analysis = self._analyze_recommendation_request(query)
        steps.append({
            'step': 1,
            'action': 'Understanding your request',
            'description': 'Extracting mood, activity, and preferences',
            'analysis': request_analysis
        })
        
        # Step 2: Consider user preferences
        user_prefs = self._extract_user_preferences(context)
        steps.append({
            'step': 2,
            'action': 'Considering your preferences',
            'description': 'Aligning recommendations with your taste',
            'preferences': user_prefs
        })
        
        # Step 3: Generate creative recommendations
        recommendations = self._generate_creative_recommendations(
            request_analysis,
            user_prefs,
            context
        )
        steps.append({
            'step': 3,
            'action': 'Generating recommendations',
            'description': 'Creating personalized music suggestions',
            'recommendations': recommendations
        })
        
        # Step 4: Explain reasoning
        explanation = self._explain_recommendations(recommendations, request_analysis)
        steps.append({
            'step': 4,
            'action': 'Explaining recommendations',
            'description': 'Why these songs fit your request',
            'explanation': explanation
        })
        
        return {
            'steps': steps,
            'conclusion': explanation['conclusion'],
            'confidence': 0.85,
            'sources': ['user_preferences', 'mood_analysis', 'music_database'],
            'reasoning_type': 'creative'
        }
    
    def _comparative_reasoning(self, query: str, context: Dict) -> Dict:
        """
        Comparative reasoning for comparison queries
        Example: "Compare Drake and The Weeknd"
        """
        steps = []
        
        # Step 1: Identify entities to compare
        entities = self._extract_comparison_entities(query)
        steps.append({
            'step': 1,
            'action': 'Identifying comparison subjects',
            'description': f'Comparing: {", ".join(entities)}',
            'entities': entities
        })
        
        # Step 2: Gather data for each entity
        entity_data = {}
        for entity in entities:
            entity_data[entity] = self._gather_entity_data(entity, context)
        
        steps.append({
            'step': 2,
            'action': 'Gathering data',
            'description': 'Collecting information about each subject',
            'data_summary': {k: len(v) for k, v in entity_data.items()}
        })
        
        # Step 3: Perform comparison
        comparison = self._perform_comparison(entity_data)
        steps.append({
            'step': 3,
            'action': 'Analyzing differences and similarities',
            'description': 'Finding key distinctions and commonalities',
            'comparison': comparison
        })
        
        # Step 4: Generate conclusion
        conclusion = self._generate_comparison_conclusion(comparison, entities)
        steps.append({
            'step': 4,
            'action': 'Drawing conclusions',
            'description': 'Summarizing the comparison',
            'conclusion': conclusion
        })
        
        return {
            'steps': steps,
            'conclusion': conclusion,
            'confidence': 0.80,
            'sources': ['artist_data', 'audio_features', 'user_preferences'],
            'reasoning_type': 'comparative'
        }
    
    def _exploratory_reasoning(self, query: str, context: Dict) -> Dict:
        """
        Exploratory reasoning for discovery queries
        Example: "Help me discover new music"
        """
        steps = []
        
        # Step 1: Assess current music landscape
        current_state = self._assess_user_music_landscape(context)
        steps.append({
            'step': 1,
            'action': 'Assessing your current music landscape',
            'description': 'Understanding what you already know and like',
            'current_state': current_state
        })
        
        # Step 2: Identify exploration opportunities
        opportunities = self._identify_exploration_opportunities(current_state, context)
        steps.append({
            'step': 2,
            'action': 'Finding exploration opportunities',
            'description': 'Discovering gaps and adjacent genres',
            'opportunities': opportunities
        })
        
        # Step 3: Generate discovery path
        discovery_path = self._generate_discovery_path(opportunities, context)
        steps.append({
            'step': 3,
            'action': 'Creating discovery path',
            'description': 'Building a journey from familiar to new',
            'path': discovery_path
        })
        
        # Step 4: Provide recommendations
        recommendations = self._provide_exploratory_recommendations(discovery_path)
        steps.append({
            'step': 4,
            'action': 'Suggesting discoveries',
            'description': 'Recommending new artists and genres',
            'recommendations': recommendations
        })
        
        return {
            'steps': steps,
            'conclusion': recommendations['conclusion'],
            'confidence': 0.75,
            'sources': ['user_profile', 'genre_graph', 'similarity_analysis'],
            'reasoning_type': 'exploratory'
        }
    
    def _diagnostic_reasoning(self, query: str, context: Dict) -> Dict:
        """
        Diagnostic reasoning for problem-solving queries
        Example: "Why don't I like these recommendations?"
        """
        steps = []
        
        # Step 1: Identify the problem
        problem = self._identify_problem(query)
        steps.append({
            'step': 1,
            'action': 'Identifying the issue',
            'description': 'Understanding what's not working',
            'problem': problem
        })
        
        # Step 2: Analyze potential causes
        causes = self._analyze_potential_causes(problem, context)
        steps.append({
            'step': 2,
            'action': 'Analyzing potential causes',
            'description': 'Finding why this might be happening',
            'causes': causes
        })
        
        # Step 3: Propose solutions
        solutions = self._propose_solutions(causes, context)
        steps.append({
            'step': 3,
            'action': 'Proposing solutions',
            'description': 'Suggesting ways to fix the issue',
            'solutions': solutions
        })
        
        # Step 4: Provide action plan
        action_plan = self._create_action_plan(solutions)
        steps.append({
            'step': 4,
            'action': 'Creating action plan',
            'description': 'Steps you can take to improve',
            'plan': action_plan
        })
        
        return {
            'steps': steps,
            'conclusion': action_plan['conclusion'],
            'confidence': 0.70,
            'sources': ['problem_analysis', 'user_feedback', 'system_diagnostics'],
            'reasoning_type': 'diagnostic'
        }
    
    # Helper methods for data extraction and analysis
    
    def _extract_listening_patterns(self, context: Dict) -> Dict:
        """Extract listening patterns from user context"""
        patterns = {
            'top_genres': [],
            'listening_diversity': 0.0,
            'temporal_patterns': {},
            'mood_preferences': []
        }
        
        try:
            # Extract top genres from top artists
            top_artists = context.get('top_artists', {}).get('medium_term', [])
            all_genres = []
            for artist in top_artists[:20]:
                all_genres.extend(artist.get('genres', []))
            
            # Count genre frequencies
            genre_counts = {}
            for genre in all_genres:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
            
            # Get top 5 genres
            patterns['top_genres'] = sorted(
                genre_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            # Calculate diversity (unique genres / total genres)
            if all_genres:
                patterns['listening_diversity'] = len(set(all_genres)) / len(all_genres)
            
        except Exception as e:
            logger.warning(f"Failed to extract listening patterns: {e}")
        
        return patterns
    
    def _extract_musical_features(self, context: Dict) -> Dict:
        """Extract musical features from user context"""
        features = {
            'avg_energy': 0.5,
            'avg_valence': 0.5,
            'avg_danceability': 0.5,
            'avg_tempo': 120,
            'preferred_acousticness': 0.5
        }
        
        # This would ideally fetch audio features from Spotify
        # For now, return defaults
        return features
    
    def _generate_analytical_insights(self, query: str, patterns: Dict, features: Dict) -> Dict:
        """Generate insights from patterns and features"""
        insights = []
        
        # Analyze genre preferences
        if patterns.get('top_genres'):
            top_genre = patterns['top_genres'][0][0]
            insights.append(f"You have a strong preference for {top_genre} music")
        
        # Analyze diversity
        diversity = patterns.get('listening_diversity', 0)
        if diversity > 0.7:
            insights.append("You have very diverse music taste, exploring many genres")
        elif diversity < 0.3:
            insights.append("You tend to stick to familiar genres and artists")
        
        # Analyze energy
        energy = features.get('avg_energy', 0.5)
        if energy > 0.7:
            insights.append("You prefer high-energy, upbeat music")
        elif energy < 0.3:
            insights.append("You prefer calm, low-energy music")
        
        conclusion = " ".join(insights) if insights else "Based on your listening history, you have eclectic taste in music."
        
        return {
            'insights': insights,
            'conclusion': conclusion,
            'confidence': 0.80
        }
    
    def _analyze_recommendation_request(self, query: str) -> Dict:
        """Analyze a recommendation request"""
        query_lower = query.lower()
        
        # Extract mood
        mood_keywords = {
            'happy': ['happy', 'joyful', 'upbeat', 'cheerful'],
            'sad': ['sad', 'melancholy', 'emotional', 'crying'],
            'energetic': ['energetic', 'pump', 'workout', 'intense'],
            'calm': ['calm', 'relaxed', 'chill', 'peaceful'],
            'focused': ['focus', 'study', 'concentrate', 'work']
        }
        
        detected_mood = 'neutral'
        for mood, keywords in mood_keywords.items():
            if any(kw in query_lower for kw in keywords):
                detected_mood = mood
                break
        
        # Extract activity
        activity_keywords = {
            'workout': ['workout', 'exercise', 'gym', 'running'],
            'study': ['study', 'studying', 'focus', 'work'],
            'party': ['party', 'dancing', 'celebration'],
            'relax': ['relax', 'chill', 'unwind', 'rest'],
            'sleep': ['sleep', 'bedtime', 'night']
        }
        
        detected_activity = 'general'
        for activity, keywords in activity_keywords.items():
            if any(kw in query_lower for kw in keywords):
                detected_activity = activity
                break
        
        return {
            'mood': detected_mood,
            'activity': detected_activity,
            'original_query': query
        }
    
    def _extract_user_preferences(self, context: Dict) -> Dict:
        """Extract user preferences from context"""
        prefs = {
            'favorite_genres': [],
            'favorite_artists': [],
            'preferred_era': 'modern',
            'language_preference': 'any'
        }
        
        try:
            # Get top artists
            top_artists = context.get('top_artists', {}).get('medium_term', [])
            prefs['favorite_artists'] = [a.get('name') for a in top_artists[:5]]
            
            # Get genres from artists
            all_genres = []
            for artist in top_artists[:10]:
                all_genres.extend(artist.get('genres', []))
            
            genre_counts = {}
            for genre in all_genres:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
            
            prefs['favorite_genres'] = [
                genre for genre, _ in sorted(
                    genre_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
            ]
        except Exception as e:
            logger.warning(f"Failed to extract user preferences: {e}")
        
        return prefs
    
    def _generate_creative_recommendations(self, request: Dict, prefs: Dict, context: Dict) -> List[str]:
        """Generate creative recommendations"""
        recommendations = []
        
        mood = request.get('mood', 'neutral')
        activity = request.get('activity', 'general')
        
        # Generate contextual recommendations
        recommendations.append(f"For {mood} mood during {activity}, I recommend:")
        
        # Add genre-based suggestions
        if prefs.get('favorite_genres'):
            top_genre = prefs['favorite_genres'][0]
            recommendations.append(f"- Explore more {top_genre} artists")
        
        # Add artist-based suggestions
        if prefs.get('favorite_artists'):
            top_artist = prefs['favorite_artists'][0]
            recommendations.append(f"- Check out artists similar to {top_artist}")
        
        return recommendations
    
    def _explain_recommendations(self, recommendations: List[str], request: Dict) -> Dict:
        """Explain why recommendations were made"""
        explanation = {
            'reasoning': [],
            'conclusion': ''
        }
        
        mood = request.get('mood', 'neutral')
        activity = request.get('activity', 'general')
        
        explanation['reasoning'].append(
            f"These recommendations match your {mood} mood and {activity} activity"
        )
        explanation['reasoning'].append(
            "They align with your listening history and preferences"
        )
        
        explanation['conclusion'] = " ".join(recommendations)
        
        return explanation
    
    def _extract_comparison_entities(self, query: str) -> List[str]:
        """Extract entities to compare from query"""
        # Simple extraction - in production, use NER
        query_lower = query.lower()
        
        # Remove comparison words
        for word in ['compare', 'versus', 'vs', 'and', 'or', 'between']:
            query_lower = query_lower.replace(word, ' ')
        
        # Split and clean
        entities = [e.strip() for e in query_lower.split() if len(e.strip()) > 2]
        
        return entities[:2]  # Return max 2 entities
    
    def _gather_entity_data(self, entity: str, context: Dict) -> Dict:
        """Gather data about an entity"""
        # Placeholder - would fetch from Spotify API
        return {
            'name': entity,
            'genres': [],
            'popularity': 0,
            'characteristics': {}
        }
    
    def _perform_comparison(self, entity_data: Dict) -> Dict:
        """Perform comparison between entities"""
        return {
            'similarities': ['Both are popular artists'],
            'differences': ['Different genres', 'Different styles'],
            'unique_aspects': {}
        }
    
    def _generate_comparison_conclusion(self, comparison: Dict, entities: List[str]) -> str:
        """Generate conclusion from comparison"""
        return f"Comparing {' and '.join(entities)}: {', '.join(comparison['similarities'])}"
    
    def _assess_user_music_landscape(self, context: Dict) -> Dict:
        """Assess user's current music knowledge"""
        return {
            'known_genres': [],
            'exploration_level': 'moderate',
            'comfort_zone': []
        }
    
    def _identify_exploration_opportunities(self, current_state: Dict, context: Dict) -> List[str]:
        """Identify opportunities for music exploration"""
        return ['Adjacent genres', 'Similar artists', 'Different eras']
    
    def _generate_discovery_path(self, opportunities: List[str], context: Dict) -> Dict:
        """Generate a path for music discovery"""
        return {
            'starting_point': 'Your current favorites',
            'intermediate_steps': opportunities,
            'destination': 'New discoveries'
        }
    
    def _provide_exploratory_recommendations(self, path: Dict) -> Dict:
        """Provide recommendations for exploration"""
        return {
            'recommendations': ['Try these new artists', 'Explore these genres'],
            'conclusion': 'Here are some exciting new directions to explore'
        }
    
    def _identify_problem(self, query: str) -> str:
        """Identify the problem from query"""
        return "Recommendations not matching preferences"
    
    def _analyze_potential_causes(self, problem: str, context: Dict) -> List[str]:
        """Analyze potential causes of the problem"""
        return [
            'Limited listening history',
            'Diverse preferences',
            'Algorithm needs more data'
        ]
    
    def _propose_solutions(self, causes: List[str], context: Dict) -> List[Dict]:
        """Propose solutions to the problem"""
        return [
            {'solution': 'Listen to more music', 'impact': 'high'},
            {'solution': 'Provide feedback', 'impact': 'medium'},
            {'solution': 'Update preferences', 'impact': 'medium'}
        ]
    
    def _create_action_plan(self, solutions: List[Dict]) -> Dict:
        """Create an action plan from solutions"""
        plan_steps = [s['solution'] for s in solutions]
        
        return {
            'steps': plan_steps,
            'conclusion': f"Try these steps: {', '.join(plan_steps)}"
        }
    
    def _format_reasoning_response(self, reasoning_chain: Dict, show_reasoning: bool = True) -> Dict:
        """Format the reasoning response for display"""
        response = {
            'response': reasoning_chain['conclusion'],
            'confidence': reasoning_chain['confidence'],
            'sources': reasoning_chain['sources'],
            'reasoning_type': reasoning_chain.get('reasoning_type', 'general')
        }
        
        if show_reasoning:
            response['reasoning_steps'] = reasoning_chain['steps']
        
        return response
