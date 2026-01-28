"""
LLM Agent for TuneGenie
Integrates with GPT-4 for contextual music recommendation enhancement
"""

import os
import json
import openai
import time
import re
from typing import List, Dict, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import logging
from datetime import datetime
from dotenv import load_dotenv
import requests

# Load environment and logging in app.py (entrypoint)
logger = logging.getLogger(__name__)

# =========================================================
# ENHANCED AI INSIGHTS IMPORTS
# =========================================================
try:
    from src.reasoning_engine import ReasoningEngine
    from src.music_toolkit import MusicToolkit
    from src.memory_system import MemorySystem
    from src.security_utils import SecurityUtils, InputValidator
    ENHANCED_INSIGHTS_AVAILABLE = True
    logger.info("✅ Enhanced AI Insights modules loaded")
except ImportError as e:
    ENHANCED_INSIGHTS_AVAILABLE = False
    logger.warning(f"⚠️ Enhanced AI Insights modules not available: {e}")

class LLMAgent:
    """LLM agent for contextual music recommendation enhancement"""
    
    def __init__(self, model_name: str = "auto", temperature: float = 0.7):
        """
        Initialize the LLM agent with multi-provider support.
        
        Args:
            model_name: Model/provider to use:
                - "auto" (default): Uses MultiProviderAI with 5 free providers
                - "huggingface": HuggingFace only
                - "groq": Groq only (if available)
                - "gemini": Google Gemini only (if available)
            temperature: Creativity level (0.0 to 1.0)
        
        Providers (all FREE, in priority order):
            1. Groq - Ultra-fast (30 req/min)
            2. Google Gemini - High quality (15 req/min)
            3. OpenRouter - Flexible (unlimited/day)
            4. DeepSeek - Best value (5M free tokens)
            5. HuggingFace - Fallback (10 req/min)
        """
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.huggingface_token = os.getenv('HUGGINGFACE_TOKEN')
        
        # =========================================================
        # MULTI-PROVIDER AI: 5 FREE providers with auto-fallback
        # =========================================================
        self.multi_provider = None
        self.available_providers = []
        
        try:
            from src.ai_providers import get_multi_provider_ai, MultiProviderAI
            self.multi_provider = get_multi_provider_ai()
            self.available_providers = self.multi_provider.get_available_providers()
            
            if self.available_providers:
                self.model_type = "multi_provider"
                logger.info(f"✅ MultiProviderAI initialized with {len(self.available_providers)} providers: {self.available_providers}")
            else:
                # No providers configured, fall back to HuggingFace
                self.model_type = "huggingface"
                self._initialize_huggingface()
                logger.warning("⚠️ No AI providers configured, using HuggingFace as fallback")
        except ImportError as e:
            logger.warning(f"MultiProviderAI not available: {e}. Using HuggingFace fallback.")
            self.model_type = "huggingface"
            self._initialize_huggingface()
        except Exception as e:
            logger.error(f"Error initializing MultiProviderAI: {e}")
            self.model_type = "huggingface"
            self._initialize_huggingface()
        
        # Load prompt templates
        self.prompts = self._load_prompts()
        
        # Log cost status
        logger.info(f"💰 LLM Agent initialized - Cost: $0.00 (all free providers)")
        logger.info(f"📊 Active providers: {self.available_providers or ['huggingface']}")
        
        # =========================================================
        # ENHANCED AI INSIGHTS: Reasoning, Memory, Tools, Security
        # =========================================================
        self.reasoning_engine = None  # Lazy initialization
        self.toolkit = None  # Lazy initialization
        self.memory_systems = {}  # Per-user memory systems
        self.enhanced_enabled = os.getenv('AI_INSIGHTS_ENHANCED_ENABLED', 'true').lower() == 'true'
        self.show_reasoning = os.getenv('AI_INSIGHTS_SHOW_REASONING', 'true').lower() == 'true'
        
        if ENHANCED_INSIGHTS_AVAILABLE and self.enhanced_enabled:
            logger.info("🧠 Enhanced AI Insights enabled (reasoning, memory, tools, security)")
        else:
            logger.info("📝 Using standard AI Insights mode")

    
    def _initialize_huggingface(self):
        """Initialize Hugging Face model (free alternative)"""
        try:
            # Use a more reliable, commonly available model
            self.model_url = "https://api-inference.huggingface.co/models/facebook/opt-125m"
            self.headers = {"Authorization": f"Bearer {self.huggingface_token}" if self.huggingface_token else ""}
            
            # Test the connection
            if self.huggingface_token:
                import requests
                test_response = requests.post(
                    self.model_url,
                    headers=self.headers,
                    json={"inputs": "test"},
                    timeout=10
                )
                if test_response.status_code == 200:
                    logger.info("Hugging Face model connection successful")
                elif test_response.status_code == 503:
                    logger.info("Hugging Face model is loading (this is normal)")
                else:
                    logger.warning(f"Hugging Face model test failed: {test_response.status_code}")
                    # Fallback to a simpler model
                    self.model_url = "https://api-inference.huggingface.co/models/gpt2"
            
            logger.info("Using Hugging Face free model")
        except Exception as e:
            logger.warning(f"Hugging Face initialization failed: {e}")
            # Use a fallback model
            self.model_url = "https://api-inference.huggingface.co/models/gpt2"
    
    def _initialize_openai(self):
        """Initialize OpenAI model"""
        try:
            # Initialize OpenAI client
            openai.api_key = self.api_key
            
            # Initialize LangChain chat model with streaming support
            self.llm = ChatOpenAI(
                model_name="gpt-3.5-turbo",
                temperature=self.temperature,
                openai_api_key=self.api_key,
                streaming=True  # Enable streaming
            )
            logger.info("OpenAI model initialized with streaming support")
        except Exception as e:
            logger.error(f"OpenAI initialization failed: {e}")
            # Fallback to Hugging Face
            self.model_type = "huggingface"
            self._initialize_huggingface()
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load prompt templates from prompts directory"""
        prompts = {}
        
        # Default prompts if files don't exist
        default_prompts = {
            'mood_analysis': """You are a music expert and psychologist. Analyze the user's current mood and suggest what type of music would be most beneficial.

User Context: {user_context}
Current Mood: {mood}
Activity: {activity}

Please provide:
1. Mood analysis (1-2 sentences)
2. Recommended music characteristics (tempo, energy, valence, genre preferences)
3. Specific musical elements that would help with this mood
4. Any mood-specific considerations

Format your response as JSON with keys: mood_analysis, music_characteristics, musical_elements, considerations""",
            
            'playlist_enhancement': """You are a senior music curator and recommendation auditor. Your job is to correct and improve a raw SVD (collaborative filtering) candidate list so it truly matches the user's mood and activity context.

Think step-by-step, but return ONLY a final JSON object for the actual task. Do not include any extra commentary outside JSON in your final answer.

Context you will receive:
- User Profile: {user_profile}
- Current Context: {context}  
  (The context string contains the user's mood and activity.)
- Collaborative Recommendations (SVD): {collaborative_recs}

Your responsibilities:
1) Diagnose issues with the SVD list relative to the context (energy, valence, lyrics vs instrumental, language, tempo, cohesion, thematic fit).
2) Propose concrete adjustments: which tracks to remove, and what types of tracks to add (with reasons).
3) Produce a compelling, context-appropriate description and a concise, on-brand playlist name.

Return ONLY JSON with keys: 
- analysis: string (brief assessment of how well the raw list fits the mood/activity)
- adjustments: array of objects with any of the following fields:
  - remove: string (track name or identifier) and reason: string
  - add_hint: object describing the ideal replacement (e.g., {\"genre\": \"lo-fi\", \"energy\": \"low\", \"instrumental\": true, \"why\": \"supports deep focus\"})
- description: string (1–3 sentences, evocative, mood/activity aligned)
- playlist_name: string (short, memorable, reflects mood/activity)


FEW-SHOT EXAMPLES (for learning):

Example 1 — Fixing a “Calm Studying” mismatch
Input
Current Context: \"Mood: Calm, Activity: Studying\"
Collaborative Recommendations (SVD):
[
  {\"name\": \"POWER\", \"artists\": [\"Kanye West\"], \"energy\": 0.92},
  {\"name\": \"Uptown Funk\", \"artists\": [\"Mark Ronson\", \"Bruno Mars\"], \"energy\": 0.89},
  {\"name\": \"Don’t Start Now\", \"artists\": [\"Dua Lipa\"], \"energy\": 0.85}
]

Expected JSON
{
  \"analysis\": \"The list is high-energy and lyric-heavy, unsuitable for calm study focus.\",
  \"adjustments\": [
    {\"remove\": \"POWER — Kanye West\", \"reason\": \"energy and lyrical intensity disrupt focus\"},
    {\"remove\": \"Uptown Funk — Mark Ronson, Bruno Mars\", \"reason\": \"party vibe conflicts with calm study\"},
    {\"remove\": \"Don’t Start Now — Dua Lipa\", \"reason\": \"dance-pop too energetic for calm context\"},
    {\"add_hint\": {\"genre\": \"lo-fi\", \"energy\": \"low\", \"instrumental\": true, \"why\": \"supports deep work without lyrical distraction\"}},
    {\"add_hint\": {\"genre\": \"ambient\", \"energy\": \"very low\", \"acoustic\": true, \"why\": \"gentle textures sustain a calm mood\"}}
  ],
  \"description\": \"Soft lo-fi and airy ambient layers to keep your focus steady and mind calm.\",
  \"playlist_name\": \"Calm Focus Flow\"
}

Example 2 — Fixing an “Energetic Workout” mismatch
Input
Current Context: \"Mood: Energetic, Activity: Exercising\"
Collaborative Recommendations (SVD):
[
  {\"name\": \"Skinny Love\", \"artists\": [\"Bon Iver\"], \"energy\": 0.25},
  {\"name\": \"Holocene\", \"artists\": [\"Bon Iver\"], \"energy\": 0.31},
  {\"name\": \"The Night We Met\", \"artists\": [\"Lord Huron\"], \"energy\": 0.28}
]

Expected JSON
{
  \"analysis\": \"The list is too slow and introspective; it lacks drive for a workout.\",
  \"adjustments\": [
    {\"remove\": \"Skinny Love — Bon Iver\", \"reason\": \"too low energy and melancholic\"},
    {\"remove\": \"Holocene — Bon Iver\", \"reason\": \"slow build, not motivating\"},
    {\"remove\": \"The Night We Met — Lord Huron\", \"reason\": \"ballad pacing unsuitable for exercise\"},
    {\"add_hint\": {\"genre\": \"edm\", \"energy\": \"high\", \"tempo_bpm\": \"130-160\", \"why\": \"sustains momentum\"}},
    {\"add_hint\": {\"genre\": \"hip hop\", \"energy\": \"high\", \"why\": \"punchy rhythm elevates intensity\"}}
  ],
  \"description\": \"High-octane beats and driving rhythms to push every rep and sprint.\",
  \"playlist_name\": \"Max Power Set\"
}


NOW DO THE ACTUAL TASK
Using the provided inputs below, output ONLY a JSON object with exactly the keys: analysis, adjustments, description, playlist_name. Do not include any examples or commentary.

User Profile: {user_profile}
Current Context: {context}
Collaborative Recommendations: {collaborative_recs}""",
            
            'track_analysis': """You are a music analyst. Analyze these tracks and provide insights about their musical characteristics and emotional impact.

Tracks: {tracks}
Context: {context}

Please provide:
1. Musical characteristics analysis
2. Emotional/mood mapping
3. Cohesion assessment
4. Context appropriateness

Format your response as JSON with keys: characteristics, emotional_mapping, cohesion, appropriateness""",
            
            'playlist_generation': """You are a music playlist curator. Create a personalized playlist based on the user's preferences and current context.

User Preferences: {user_preferences}
Current Mood: {mood}
Activity: {activity}
Available Tracks: {available_tracks}

Please:
1. Select the most appropriate tracks (max 20)
2. Order them for optimal flow
3. Provide a compelling playlist description
4. Suggest a creative playlist name

Format your response as JSON with keys: selected_tracks, track_order, description, playlist_name""",
            
            'feedback_analysis': """You are a music recommendation analyst. Analyze user feedback to improve future recommendations.

User Feedback: {feedback}
Previous Recommendations: {previous_recs}
User Profile: {user_profile}

Please provide:
1. Feedback analysis and insights
2. Areas for improvement
3. Suggested adjustments to recommendation strategy
4. Learning points for future recommendations

Format your response as JSON with keys: analysis, improvements, adjustments, learning_points"""
        }
        
        # Try to load from prompts directory
        prompts_dir = 'prompts'
        if os.path.exists(prompts_dir):
            for prompt_name in default_prompts.keys():
                prompt_file = os.path.join(prompts_dir, f"{prompt_name}.txt")
                if os.path.exists(prompt_file):
                    with open(prompt_file, 'r') as f:
                        prompts[prompt_name] = f.read()
                else:
                    prompts[prompt_name] = default_prompts[prompt_name]
        else:
            prompts = default_prompts
        
        return prompts
    
    def analyze_mood_and_context(self, user_context: str, mood: str, activity: str) -> Dict:
        """Analyze user's mood and context for music recommendations"""
        try:
            if self.model_type == "huggingface":
                return self._analyze_mood_huggingface(user_context, mood, activity)
            else:
                return self._analyze_mood_openai(user_context, mood, activity)
        except Exception as e:
            logger.error(f"Failed to analyze mood and context: {e}")
            return {
                'mood_analysis': f"Based on your mood ({mood}) and activity ({activity}), I recommend music that matches your current state.",
                'music_characteristics': {
                    'tempo': 'medium' if mood in ['calm', 'focused'] else 'high',
                    'energy': 'low' if mood in ['calm', 'relaxed'] else 'high',
                    'valence': 'positive' if mood in ['happy', 'excited'] else 'neutral'
                }
            }
    
    def enhance_recommendations(self, user_data: Dict, context: str, collaborative_recs: List[Dict]) -> Dict:
        """Enhance collaborative filtering recommendations with LLM insights"""
        try:
            if self.model_type == "huggingface":
                return self._enhance_recommendations_huggingface(user_data, context, collaborative_recs)
            else:
                return self._enhance_recommendations_openai(user_data, context, collaborative_recs)
        except Exception as e:
            logger.error(f"Failed to enhance recommendations: {e}")
            return {
                'description': f"Enhanced playlist based on {context}",
                'adjustments': "Recommendations optimized for your current context",
                'playlist_name': "Personalized TuneGenie Playlist"
            }
    
    def generate_playlist(self, user_data: Dict, mood: str, activity: str, available_tracks: List[Dict], num_tracks: int = 20) -> Dict:
        """Generate a personalized playlist based on user data, mood, and activity"""
        try:
            if self.model_type == "huggingface":
                return self._generate_playlist_huggingface(user_data, mood, activity, available_tracks, num_tracks)
            else:
                return self._generate_playlist_openai(user_data, mood, activity, available_tracks, num_tracks)
        except Exception as e:
            logger.error(f"Failed to generate playlist: {e}")
            # Fallback playlist generation
            return self._generate_fallback_playlist(user_data, mood, activity, available_tracks, num_tracks)

    def generate_search_strategy(self, prompt: str) -> Dict:
        """
        Generate a comprehensive search strategy based on mood/context analysis
        
        Returns a strategy with genres, audio features, search queries, etc.
        """
        try:
            if self.model_type == "openai":
                system_msg = (
                    "You are a music expert who understands how mood, activity, and context "
                    "translate into specific musical characteristics. Generate precise search "
                    "strategies that will find the perfect tracks."
                )
                
                messages = [
                    SystemMessage(content=system_msg),
                    HumanMessage(content=prompt + "\n\nReturn ONLY valid JSON."),
                ]
                
                response = self.llm(messages)
                text = getattr(response, 'content', '') or getattr(response, 'text', '')
                
                try:
                    strategy = json.loads(text)
                    # Ensure required fields
                    strategy.setdefault('genres', ['pop', 'indie', 'electronic'])
                    strategy.setdefault('audio_features', {
                        'energy': [0.4, 0.7],
                        'valence': [0.5, 0.8],
                        'tempo': [90, 130]
                    })
                    strategy.setdefault('search_queries', [])
                    strategy.setdefault('themes', [])
                    strategy.setdefault('era', 'current')
                    
                    return strategy
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM strategy response as JSON")
                    # Try to extract key information from text
                    return self._extract_strategy_from_text(text)
            
            # Fallback for Hugging Face or other models
            return self._generate_heuristic_strategy(prompt)
            
        except Exception as e:
            logger.error(f"Failed to generate search strategy: {e}")
            return self._generate_heuristic_strategy(prompt)
    
    def _extract_strategy_from_text(self, text: str) -> Dict:
        """Extract strategy components from free-form text"""
        strategy = {
            'genres': [],
            'audio_features': {
                'energy': [0.4, 0.7],
                'valence': [0.5, 0.8],
                'tempo': [90, 130]
            },
            'search_queries': [],
            'themes': [],
            'era': 'current'
        }
        
        # Extract genres mentioned
        common_genres = ['pop', 'rock', 'hip hop', 'electronic', 'jazz', 'classical', 
                        'indie', 'r&b', 'country', 'folk', 'metal', 'punk', 'reggae',
                        'blues', 'soul', 'funk', 'disco', 'house', 'techno', 'ambient']
        
        text_lower = text.lower()
        for genre in common_genres:
            if genre in text_lower:
                strategy['genres'].append(genre)
        
        # Extract energy levels
        if any(word in text_lower for word in ['high energy', 'energetic', 'upbeat', 'intense']):
            strategy['audio_features']['energy'] = [0.7, 1.0]
        elif any(word in text_lower for word in ['low energy', 'calm', 'relaxed', 'mellow']):
            strategy['audio_features']['energy'] = [0.1, 0.4]
        
        # Extract valence (mood)
        if any(word in text_lower for word in ['happy', 'joyful', 'positive', 'uplifting']):
            strategy['audio_features']['valence'] = [0.7, 1.0]
        elif any(word in text_lower for word in ['sad', 'melancholic', 'dark', 'somber']):
            strategy['audio_features']['valence'] = [0.0, 0.3]
        
        # Extract tempo
        if 'fast' in text_lower or 'quick' in text_lower:
            strategy['audio_features']['tempo'] = [120, 180]
        elif 'slow' in text_lower:
            strategy['audio_features']['tempo'] = [60, 90]
        
        # Generate basic search queries from genres
        for genre in strategy['genres'][:3]:
            strategy['search_queries'].append(f"genre:{genre}")
        
        return strategy
    
    def _generate_heuristic_strategy(self, prompt: str) -> Dict:
        """Generate a heuristic-based strategy from the prompt"""
        # Extract mood and activity from prompt
        prompt_lower = prompt.lower()
        
        # Default strategy
        strategy = {
            'genres': ['pop', 'indie', 'electronic'],
            'audio_features': {
                'energy': [0.4, 0.7],
                'valence': [0.5, 0.8],
                'tempo': [90, 130],
                'danceability': [0.4, 0.7],
                'acousticness': [0.2, 0.6]
            },
            'search_queries': [],
            'themes': [],
            'era': 'current'
        }
        
        # Mood-based adjustments
        if 'happy' in prompt_lower or 'excited' in prompt_lower:
            strategy['genres'] = ['pop', 'dance', 'indie pop']
            strategy['audio_features']['energy'] = [0.6, 0.9]
            strategy['audio_features']['valence'] = [0.7, 1.0]
            strategy['themes'] = ['uplifting', 'positive', 'feel-good']
        elif 'sad' in prompt_lower or 'melancholic' in prompt_lower:
            strategy['genres'] = ['indie folk', 'singer-songwriter', 'ambient']
            strategy['audio_features']['energy'] = [0.1, 0.4]
            strategy['audio_features']['valence'] = [0.0, 0.3]
            strategy['themes'] = ['emotional', 'introspective', 'melancholic']
        elif 'calm' in prompt_lower or 'relaxed' in prompt_lower:
            strategy['genres'] = ['ambient', 'lo-fi', 'jazz']
            strategy['audio_features']['energy'] = [0.1, 0.3]
            strategy['audio_features']['valence'] = [0.4, 0.7]
            strategy['themes'] = ['peaceful', 'serene', 'meditative']
        elif 'energetic' in prompt_lower or 'motivated' in prompt_lower:
            strategy['genres'] = ['electronic', 'hip hop', 'rock']
            strategy['audio_features']['energy'] = [0.7, 1.0]
            strategy['audio_features']['valence'] = [0.5, 0.9]
            strategy['themes'] = ['powerful', 'motivating', 'dynamic']
        
        # Activity-based adjustments
        if 'working' in prompt_lower or 'studying' in prompt_lower:
            strategy['audio_features']['energy'] = [0.3, 0.6]
            strategy['themes'].append('focus')
            strategy['search_queries'].append('focus music')
        elif 'exercising' in prompt_lower or 'workout' in prompt_lower:
            strategy['audio_features']['energy'] = [0.7, 1.0]
            strategy['audio_features']['tempo'] = [120, 160]
            strategy['themes'].append('workout')
            strategy['search_queries'].append('workout music')
        elif 'cooking' in prompt_lower:
            strategy['themes'].append('cooking vibes')
            strategy['search_queries'].append('cooking playlist')
        
        # Generate search queries
        for genre in strategy['genres']:
            strategy['search_queries'].append(f"genre:{genre}")
        
        # Add mood-based queries
        for theme in strategy['themes'][:2]:
            strategy['search_queries'].append(f"{theme} music")
        
        return strategy
    
    def validate_playlist_against_keywords(self, parsed_keywords: Dict[str, List[str]], tracks: List[Dict]) -> Dict:
        """Validate a playlist against parsed keywords using the configured LLM, with compact JSON output.
        The LLM is prompted to reason and then provide a JSON summary only. If the model is huggingface
        text completion, we use a deterministic heuristic and place reasoning-like notes in a field.
        """
        try:
            # Prepare a compact context for evaluation
            keywords_summary = {k: parsed_keywords.get(k, [])[:10] for k in ['artists','titles','albums','genres','raw']}
            track_snippets = [
                {
                    'name': t.get('name', ''),
                    'artists': t.get('artists', [])[:3],
                    'album': t.get('album', ''),
                }
                for t in tracks[:50]
            ]

            if self.model_type == "openai":
                system_msg = (
                    "You are a strict validator that checks whether a playlist aligns with user-specified keywords. "
                    "Think step-by-step but only return a final JSON object."
                )
                user_prompt = (
                    "Keywords (parsed): {keywords}\n"
                    "Tracks (first 50): {tracks}\n\n"
                    "Evaluate coverage of keywords across artists, titles, albums, and raw terms.\n"
                    "Return ONLY compact JSON with keys: coverage_score (0-1), matched_terms, total_terms, unmet_keywords (list), "
                    "examples (array of up to 10 objects with keys: keyword, track, artists)."
                ).format(keywords=keywords_summary, tracks=track_snippets)

                messages = [
                    SystemMessage(content=system_msg),
                    HumanMessage(content=user_prompt),
                ]
                resp = self.llm(messages)
                text = getattr(resp, 'content', '') or getattr(resp, 'text', '')
                try:
                    data = json.loads(text)
                    # basic sanity
                    data.setdefault('coverage_score', 0)
                    data.setdefault('matched_terms', 0)
                    data.setdefault('total_terms', 0)
                    data.setdefault('unmet_keywords', [])
                    data.setdefault('examples', [])
                    data['enabled'] = True
                    return data
                except Exception:
                    # Fall back to heuristic if parsing fails
                    pass

            # Heuristic fallback (also used for huggingface mode)
            total_terms = sum(len(keywords_summary.get(k, [])) for k in ['artists','titles','albums','genres','raw'])
            matched_terms = 0
            per_term = {}
            examples = []
            def fields(track):
                name = (track.get('name') or '').lower()
                album = (track.get('album') or '').lower()
                artists = [a.lower() for a in (track.get('artists') or [])]
                return name, album, artists
            for key in ['artists','titles','albums','genres','raw']:
                for kw in keywords_summary.get(key, []):
                    kwl = kw.lower()
                    count = 0
                    for tr in tracks:
                        name, album, artists = fields(tr)
                        if key == 'artists' and any(kwl in a for a in artists):
                            count += 1; examples.append({'keyword': kw, 'track': tr.get('name'), 'artists': tr.get('artists')}); break
                        if key == 'titles' and kwl in name:
                            count += 1; examples.append({'keyword': kw, 'track': tr.get('name'), 'artists': tr.get('artists')}); break
                        if key == 'albums' and kwl in album:
                            count += 1; examples.append({'keyword': kw, 'track': tr.get('name'), 'artists': tr.get('artists')}); break
                        if key == 'genres' and (kwl in name or kwl in album or any(kwl in a for a in artists)):
                            count += 1; examples.append({'keyword': kw, 'track': tr.get('name'), 'artists': tr.get('artists')}); break
                        if key == 'raw' and (kwl in name or kwl in album or any(kwl in a for a in artists)):
                            count += 1; examples.append({'keyword': kw, 'track': tr.get('name'), 'artists': tr.get('artists')}); break
                    per_term[kw] = count
                    if count > 0:
                        matched_terms += 1
            coverage = (matched_terms / total_terms) if total_terms else 1.0
            unmet = [kw for kw, c in per_term.items() if c == 0]
            return {
                'enabled': True,
                'coverage_score': round(coverage, 3),
                'matched_terms': matched_terms,
                'total_terms': total_terms,
                'unmet_keywords': unmet,
                'examples': examples[:10]
            }
        except Exception as e:
            logger.error(f"Keyword validation failed: {e}")
            return {'enabled': False, 'error': str(e)}
    
    def analyze_tracks(self, tracks: List[Dict], context: str) -> Dict:
        """
        Analyze tracks for musical characteristics and emotional impact
        
        Args:
            tracks: List of tracks to analyze
            context: Context for the analysis
            
        Returns:
            Dictionary with track analysis results
        """
        try:
            prompt = self.prompts['track_analysis'].format(
                tracks=json.dumps(tracks, indent=2),
                context=context
            )
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            try:
                result = json.loads(response.content)
                logger.info("Successfully analyzed tracks")
                return result
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON response, returning raw text")
                return {'raw_response': response.content}
                
        except Exception as e:
            logger.error(f"Failed to analyze tracks: {e}")
            return {'error': str(e)}
    
    def analyze_feedback(self, feedback: str, previous_recs: List[Dict], user_profile: Dict) -> Dict:
        """
        Analyze user feedback to improve future recommendations
        
        Args:
            feedback: User's feedback on recommendations
            previous_recs: Previously provided recommendations
            user_profile: User's profile information
            
        Returns:
            Dictionary with feedback analysis and improvement suggestions
        """
        try:
            prompt = self.prompts['feedback_analysis'].format(
                feedback=feedback,
                previous_recs=json.dumps(previous_recs, indent=2),
                user_profile=json.dumps(user_profile, indent=2)
            )
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            try:
                result = json.loads(response.content)
                logger.info("Successfully analyzed feedback")
                return result
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON response, returning raw text")
                return {'raw_response': response.content}
                
        except Exception as e:
            logger.error(f"Failed to analyze feedback: {e}")
            return {'error': str(e)}
    
    def _format_conversation_history(self, conversation_history: list) -> str:
        """
        Format conversation history into a context string for the AI
        
        Args:
            conversation_history: List of dicts with 'query' and 'response' keys
            
        Returns:
            Formatted string of previous conversation
        """
        if not conversation_history:
            return ""
        
        # Take last 3 conversations for context (to avoid token limits)
        recent_history = conversation_history[-3:]
        
        formatted = "Previous conversation:\n"
        for i, chat in enumerate(recent_history, 1):
            query = chat.get('query', '')
            response = chat.get('response', '')
            # Truncate long responses to save tokens
            if len(response) > 200:
                response = response[:200] + "..."
            formatted += f"Q{i}: {query}\nA{i}: {response}\n\n"
        
        return formatted
    
    def get_music_insights(self, question: str, user_context: str = "", conversation_history: list = None) -> Dict:
        """
        Get AI-powered music insights based on user question with conversation memory
        
        Args:
            question: User's question about music
            user_context: Additional context about the user
            conversation_history: List of previous Q&A pairs for follow-up context
            
        Returns:
            Dictionary with AI insights
        """
        try:
            # Format conversation history for context
            history_context = self._format_conversation_history(conversation_history)
            
            # Try multi-provider first (5 free providers with auto-fallback)
            if self.model_type == "multi_provider" and self.multi_provider:
                return self._get_multi_provider_insights(question, user_context, history_context)
            elif self.model_type == "huggingface":
                return self._get_huggingface_insights(question, user_context, history_context)
            else:
                return self._get_openai_insights(question, user_context, history_context)
            
        except Exception as e:
            logger.error(f"Failed to get music insights: {e}")
            return {
                'error': f"Failed to get AI response: {str(e)}",
                'question': question,
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_multi_provider_insights(self, question: str, user_context: str = "", history_context: str = "") -> Dict:
        """Get insights using MultiProviderAI (5 free providers with auto-fallback)"""
        try:
            # Build the full context
            full_context = ""
            if history_context:
                full_context += history_context + "\n"
            if user_context:
                full_context += f"User context: {user_context}\n"
            
            prompt = f"{full_context}Question: {question}"
            
            system_message = """You are TuneGenie's AI Music Expert. Provide helpful, conversational insights about music.
Be knowledgeable but friendly. Reference specific artists, genres, and songs when relevant.
Keep responses concise but informative."""
            
            # Use MultiProviderAI for generation (tries Groq -> Gemini -> OpenRouter -> DeepSeek -> HuggingFace)
            response = self.multi_provider.generate(
                prompt=prompt,
                max_tokens=500,
                temperature=self.temperature,
                system_message=system_message
            )
            
            if response:
                return {
                    'answer': response,
                    'question': question,
                    'timestamp': datetime.now().isoformat(),
                    'provider': 'multi_provider',
                    'providers_available': self.available_providers
                }
            else:
                # Fallback to HuggingFace if all providers failed
                logger.warning("All multi-providers failed, falling back to HuggingFace")
                return self._get_huggingface_insights(question, user_context, history_context)
                
        except Exception as e:
            logger.error(f"MultiProvider insights failed: {e}")
            return self._get_huggingface_insights(question, user_context, history_context)

    
    def get_music_insights_stream(self, question: str, user_context: str = "", conversation_history: list = None):
        """
        Get AI-powered music insights with streaming support (generator function)
        
        This method yields chunks of the response as they're generated, allowing
        for real-time streaming display in the UI.
        
        Args:
            question: User's question about music
            user_context: Additional context about the user
            conversation_history: List of previous Q&A pairs for follow-up context
            
        Yields:
            Chunks of the response text as they're generated
        """
        try:
            # Format conversation history for context
            history_context = self._format_conversation_history(conversation_history)
            
            if self.model_type == "huggingface":
                # HuggingFace doesn't support true streaming, so we simulate it
                yield from self._get_huggingface_insights_stream(question, user_context, history_context)
            else:
                # OpenAI supports true streaming via LangChain
                yield from self._get_openai_insights_stream(question, user_context, history_context)
            
        except Exception as e:
            logger.error(f"Failed to get streaming music insights: {e}")
            yield f"❌ Error: {str(e)}"
    
    def _get_huggingface_insights_stream(self, question: str, user_context: str = "", history_context: str = ""):
        """
        Get insights using Hugging Face model with simulated streaming (generator)
        
        Since HuggingFace Inference API doesn't support true streaming,
        we fetch the full response and yield it in chunks to simulate streaming.
        """
        try:
            # Build the full context including conversation history
            full_context = ""
            if history_context:
                full_context += history_context + "\n"
            if user_context:
                full_context += f"User context: {user_context}\n"
            
            # First try the actual Hugging Face API
            if hasattr(self, 'model_url') and self.model_url:
                prompt = f"{full_context}Current question: {question}\n\nAnswer (considering the conversation above):"
                response = requests.post(
                    self.model_url,
                    headers=self.headers,
                    json={"inputs": prompt},
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # Extract the generated text
                    generated_text = ""
                    
                    if isinstance(result, list) and len(result) > 0:
                        if 'generated_text' in result[0]:
                            generated_text = result[0]['generated_text']
                        elif 'text' in result[0]:
                            generated_text = result[0]['text']
                        else:
                            generated_text = str(result[0])
                    elif isinstance(result, dict):
                        if 'generated_text' in result:
                            generated_text = result['generated_text']
                        elif 'text' in result:
                            generated_text = result['text']
                        else:
                            generated_text = str(result)
                    else:
                        generated_text = str(result)
                    
                    # Clean up the response
                    answer = generated_text.replace(f"Question: {question}\nContext: {user_context}\n\nAnswer:", '').strip()
                    if answer and len(answer) > 10:
                        # Simulate streaming by yielding in chunks
                        chunk_size = 15  # Characters per chunk
                        for i in range(0, len(answer), chunk_size):
                            yield answer[i:i + chunk_size]
                            time.sleep(0.03)  # Small delay to simulate streaming
                        return
            
            # If API fails, use intelligent fallback with simulated streaming
            fallback_result = self._get_intelligent_fallback(question, user_context, history_context)
            insight = fallback_result.get('insight', '')
            # Simulate streaming by yielding in chunks
            chunk_size = 15
            for i in range(0, len(insight), chunk_size):
                yield insight[i:i + chunk_size]
                time.sleep(0.03)  # Small delay to simulate streaming
                
        except Exception as e:
            logger.warning(f"Hugging Face streaming failed: {e}")
            # Ultimate fallback
            error_msg = f"I can help you with music recommendations! For '{question}', here are some general tips based on your context."
            chunk_size = 15
            for i in range(0, len(error_msg), chunk_size):
                yield error_msg[i:i + chunk_size]
                time.sleep(0.03)
    
    def _get_huggingface_insights(self, question: str, user_context: str = "", history_context: str = "") -> Dict:
        """Get insights using Hugging Face model or intelligent fallback with conversation memory"""
        try:
            # Build the full context including conversation history
            full_context = ""
            if history_context:
                full_context += history_context + "\n"
            if user_context:
                full_context += f"User context: {user_context}\n"
            
            # First try the actual Hugging Face API
            if hasattr(self, 'model_url') and self.model_url:
                prompt = f"{full_context}Current question: {question}\n\nAnswer (considering the conversation above):"
                response = requests.post(
                    self.model_url,
                    headers=self.headers,
                    json={"inputs": prompt},
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # Extract the generated text - handle different response formats
                    generated_text = ""
                    
                    if isinstance(result, list) and len(result) > 0:
                        if 'generated_text' in result[0]:
                            generated_text = result[0]['generated_text']
                        elif 'text' in result[0]:
                            generated_text = result[0]['text']
                        else:
                            generated_text = str(result[0])
                    elif isinstance(result, dict):
                        if 'generated_text' in result:
                            generated_text = result['generated_text']
                        elif 'text' in result:
                            generated_text = result['text']
                        else:
                            generated_text = str(result)
                    else:
                        generated_text = str(result)
                    
                    # Clean up the response
                    answer = generated_text.replace(f"Question: {question}\nContext: {user_context}\n\nAnswer:", '').strip()
                    if answer and len(answer) > 10:
                        return {
                            'insight': answer,
                            'question': question,
                            'timestamp': datetime.now().isoformat(),
                            'model_used': 'Hugging Face (Free)'
                        }
            
            # If API fails or returns poor results, use intelligent fallback
            return self._get_intelligent_fallback(question, user_context, history_context)
                
        except Exception as e:
            logger.warning(f"Hugging Face API call failed: {e}")
            # Use intelligent fallback
            return self._get_intelligent_fallback(question, user_context, history_context)
    
    def _get_intelligent_fallback(self, question: str, user_context: str = "", history_context: str = "") -> Dict:
        """Provide intelligent, contextual responses without external API calls, with conversation memory"""
        try:
            # Create contextual, intelligent responses based on the question
            question_lower = question.lower()
            context_lower = user_context.lower()
            history_lower = history_context.lower() if history_context else ""
            
            # Check for follow-up question patterns
            is_follow_up = any(phrase in question_lower for phrase in [
                'more', 'another', 'similar', 'like that', 'same', 'also', 
                'what else', 'anything else', 'tell me more', 'expand on',
                'why', 'how about', 'what about', 'and', 'but'
            ])
            
            # Extract context from previous conversation for follow-ups
            # Priority: Check ACTIVITY-based topics FIRST (more specific), then genre topics
            prev_topic = ""
            if is_follow_up and history_context:
                # Get the most recent Q&A pair for priority detection
                # The history format is "Q1: ... A1: ... Q2: ... A2: ..."
                # We want to prioritize the QUESTION content over the ANSWER content
                
                # Priority 1: Activity/mood-based topics (most specific)
                if 'workout' in history_lower or 'exercise' in history_lower or 'working out' in history_lower or 'gym' in history_lower:
                    prev_topic = "workout"
                elif 'study' in history_lower or 'studying' in history_lower or 'focus' in history_lower or 'concentrate' in history_lower:
                    prev_topic = "studying/focus"
                elif 'sleep' in history_lower or 'bedtime' in history_lower or 'relax' in history_lower:
                    prev_topic = "relaxation"
                elif 'happy' in history_lower or 'joy' in history_lower or 'upbeat' in history_lower:
                    prev_topic = "happy mood"
                elif 'sad' in history_lower or 'melancholy' in history_lower or 'emotional' in history_lower:
                    prev_topic = "sad mood"
                # Priority 2: Genre-based topics (check question keywords, not answer mentions)
                elif 'tell me about jazz' in history_lower or 'jazz music' in history_lower:
                    prev_topic = "jazz"
                elif 'tell me about hip-hop' in history_lower or 'hip-hop music' in history_lower or 'rap music' in history_lower:
                    prev_topic = "hip-hop"
                elif 'tell me about classical' in history_lower or 'classical music' in history_lower:
                    prev_topic = "classical"
                elif 'tell me about rock' in history_lower or 'rock music' in history_lower:
                    prev_topic = "rock"
                elif 'tell me about pop' in history_lower or 'pop music' in history_lower:
                    prev_topic = "pop"
                elif 'tell me about electronic' in history_lower or 'electronic music' in history_lower or 'edm' in history_lower:
                    prev_topic = "electronic"
            
            # Handle follow-up questions with context from previous conversation
            if is_follow_up and prev_topic:
                follow_up_responses = {
                    "jazz": "Building on our jazz discussion - if you want to explore more, try bebop (Charlie Parker, Dizzy Gillespie) for complex improvisation, or smooth jazz (Kenny G, George Benson) for a more relaxed feel. Modern jazz artists like Robert Glasper blend jazz with hip-hop and R&B. For vocal jazz, check out Ella Fitzgerald or modern artists like Norah Jones.",
                    "hip-hop": "Continuing with hip-hop - you might also enjoy underground/conscious hip-hop (MF DOOM, Aesop Rock), boom bap classics (Nas, Wu-Tang Clan), or alternative hip-hop (Anderson .Paak, Tyler, The Creator). For production-focused hip-hop, check out J Dilla or Madlib's work.",
                    "classical": "Expanding on classical music - try Romantic era composers (Chopin, Liszt, Brahms) for emotional depth, or Impressionist composers (Debussy, Ravel) for dreamy atmospheres. For modern classical, explore minimalists like Philip Glass or Max Richter. Film score composers like Hans Zimmer also bridge classical and contemporary.",
                    "rock": "More rock recommendations - explore progressive rock (Pink Floyd, Yes) for complex arrangements, alternative rock (Radiohead, Arcade Fire) for experimental sounds, or indie rock (The Strokes, Arctic Monkeys) for modern vibes. Classic rock legends like Led Zeppelin and Queen are always worth revisiting.",
                    "pop": "For more pop exploration - try synth-pop (The Weeknd, Dua Lipa), indie pop (Lorde, Billie Eilish), or classic pop (Michael Jackson, Madonna). K-pop (BTS, BLACKPINK) offers a unique blend of pop with intricate choreography and production.",
                    "electronic": "Diving deeper into electronic music - explore house (Disclosure, Duke Dumont), techno (Carl Cox, Charlotte de Witte), ambient (Tycho, Boards of Canada), or future bass (Flume, San Holo). For live electronic, check out artists like ODESZA or Bonobo.",
                    "happy mood": "For more uplifting music - try feel-good indie (Vampire Weekend, Phoenix), classic Motown (Stevie Wonder, Marvin Gaye), or modern funk (Bruno Mars, Doja Cat). Upbeat jazz and bossa nova can also be surprisingly mood-boosting!",
                    "sad mood": "For more emotional music exploration - try post-rock (Sigur Rós, Explosions in the Sky), acoustic singer-songwriters (Iron & Wine, Fleet Foxes), or ambient/neo-classical (Ólafur Arnalds, Nils Frahm). These can help process emotions while being musically rich.",
                    "workout": "More workout music ideas - try drum and bass (Netsky, Sub Focus) for high-intensity cardio, metal (Metallica, Bring Me The Horizon) for lifting, or dancehall/reggaeton for a fun cardio session. Power ballads can be great for cool-down stretches.",
                    "studying/focus": "More focus music options - try video game soundtracks (they're designed for concentration!), lo-fi hip-hop playlists, or classical piano (Chopin's Nocturnes, Debussy). White noise or nature sounds can also boost concentration for some people.",
                    "relaxation": "More relaxation music - try spa/wellness music, nature soundscapes (rain, ocean waves), soft piano (Ludovico Einaudi), or meditation music. Slow tempo jazz (50-70 BPM), new age artists like Enya, or ambient music by Brian Eno are also excellent for unwinding."
                }
                
                if prev_topic in follow_up_responses:
                    return {
                        'insight': follow_up_responses[prev_topic],
                        'question': question,
                        'timestamp': datetime.now().isoformat(),
                        'model_used': 'TuneGenie AI (Conversation Memory)',
                        'is_follow_up': True
                    }
            
            # Enhanced mood-based responses
            if 'happy' in question_lower or 'joy' in question_lower:
                if 'work' in context_lower or 'working' in context_lower:
                    insight = "For a happy working mood, I recommend upbeat, energetic music that keeps you motivated without being distracting. Think pop, indie rock, or electronic music with positive vibes and steady rhythms that help maintain focus and energy throughout your work session. Artists like Vampire Weekend, The 1975, or upbeat electronic producers like ODESZA work great for this."
                else:
                    insight = "Happy music should be bright, uplifting, and energizing! Look for songs with major keys, upbeat tempos (120-140 BPM), and positive lyrics. Genres like pop, funk, disco, and upbeat indie rock are perfect for boosting your mood and energy levels. Classic happy songs include 'Happy' by Pharrell Williams, 'Walking on Sunshine' by Katrina & The Waves, or anything by artists like Bruno Mars or Taylor Swift."
            
            elif 'sad' in question_lower or 'melancholy' in question_lower:
                if 'work' in context_lower or 'working' in context_lower:
                    insight = "When you're feeling down but need to work, try gentle, ambient music or soft instrumental pieces. Avoid overly emotional songs that might deepen your mood. Look for calming acoustic music, lo-fi beats, or peaceful classical pieces that provide comfort without distraction. Artists like Bon Iver, Sufjan Stevens, or instrumental albums by Ludovico Einaudi can help."
                else:
                    insight = "Sad music can be therapeutic and help process emotions. Look for songs with minor keys, slower tempos, and meaningful lyrics. Genres like indie folk, acoustic, and some classical music can provide comfort and emotional release. Artists like Adele, Lana Del Rey, or The National are known for their emotional depth. Remember, it's okay to feel sad, and music can help you process those feelings."
            
            elif 'energetic' in question_lower or 'pump' in question_lower:
                if 'work' in context_lower or 'working' in context_lower:
                    insight = "For energetic work sessions, choose high-energy music with strong beats and motivating rhythms. Rock, electronic dance music, or upbeat hip-hop can provide the energy boost you need. Look for songs with driving bass lines and tempos around 130-150 BPM. Artists like Imagine Dragons, The Killers, or electronic producers like Skrillex and Martin Garrix are perfect for maintaining high energy during work."
                else:
                    insight = "Energetic music should get your heart pumping and body moving! Look for high-tempo songs (140+ BPM) with strong beats, powerful bass lines, and dynamic energy. Genres like rock, electronic, hip-hop, and dance music are perfect for workouts and high-energy activities. Think artists like Linkin Park, Eminem, or electronic dance music that makes you want to move!"
            
            elif 'calm' in question_lower or 'relax' in question_lower:
                if 'work' in context_lower or 'working' in context_lower:
                    insight = "For calm, focused work, choose ambient music, lo-fi beats, or gentle instrumental pieces. Avoid lyrics that might distract you. Look for music with consistent, soothing rhythms and minimal variations that support concentration without being boring. Artists like Brian Eno, Tycho, or lo-fi channels on streaming platforms provide perfect background music for focused work."
                else:
                    insight = "Calm music should be soothing and peaceful. Look for slow tempos (60-80 BPM), gentle melodies, and minimal complexity. Genres like ambient, classical, acoustic, and some jazz can help reduce stress and create a peaceful atmosphere. Artists like Sigur Rós, Explosions in the Sky, or classical composers like Debussy create beautiful calming music."
            
            elif 'focus' in question_lower or 'concentrate' in question_lower or 'study' in question_lower or 'studying' in question_lower:
                insight = "For studying and focused work, choose music without lyrics to avoid cognitive interference. Instrumental music, ambient sounds, or lo-fi beats work well. Look for consistent tempos and minimal variations that provide background stimulation without distraction. Classical music, especially Baroque period pieces by Bach or Handel, has been shown to improve concentration. Modern options include lo-fi hip-hop, ambient electronic, or instrumental post-rock."
            
            elif 'workout' in question_lower or 'exercise' in question_lower or 'working out' in question_lower or 'gym' in question_lower:
                insight = "Workout music should be high-energy and motivating! Look for songs with strong beats (120-150 BPM), powerful bass lines, and energizing rhythms. Genres like rock, electronic dance music, hip-hop, and pop are perfect for maintaining energy and motivation during exercise. Artists like Eminem, Linkin Park, The Weeknd, or electronic producers like Calvin Harris and David Guetta create perfect workout anthems."
            
            elif 'sleep' in question_lower or 'bedtime' in question_lower:
                insight = "Sleep music should be extremely gentle and calming. Look for very slow tempos (60 BPM or slower), soft melodies, and minimal complexity. Genres like ambient, classical, or nature sounds can help quiet your mind and prepare your body for rest. Artists like Max Richter, Ólafur Arnalds, or ambient composers like Brian Eno create beautiful sleep music. Avoid anything with strong beats or sudden changes."
            
            # Enhanced genre responses
            elif 'jazz' in question_lower:
                insight = "Jazz is a uniquely American art form that emerged in the early 20th century. It's characterized by improvisation, syncopated rhythms, and complex harmonies. Jazz can range from smooth and relaxing (like Miles Davis' 'Kind of Blue') to energetic and complex (like John Coltrane's work). For beginners, try artists like Chet Baker, Billie Holiday, or modern jazz musicians like Kamasi Washington. Jazz is perfect for sophisticated dinner parties, studying, or relaxing evenings."
            
            elif 'hip-hop' in question_lower or 'rap' in question_lower:
                insight = "Hip-hop is more than just music - it's a cultural movement that emerged in the 1970s in the Bronx, New York. It's characterized by rhythmic speech (rapping), beatboxing, and often includes sampling from other songs. Hip-hop can be conscious and political (like Kendrick Lamar or J. Cole), party-oriented (like Drake or Travis Scott), or experimental (like Tyler, The Creator). It's perfect for workouts, parties, or when you want to feel confident and empowered."
            
            elif 'classical' in question_lower:
                insight = "Classical music spans over 400 years of Western musical tradition, from the Renaissance to the present day. It's characterized by complex compositions, orchestral arrangements, and often follows specific forms and structures. Classical music can be incredibly diverse - from the peaceful works of Debussy to the dramatic symphonies of Beethoven. It's perfect for studying, relaxing, or when you want to experience deep emotional expression through music."
            
            elif 'electronic' in question_lower:
                insight = "Electronic music is created using electronic instruments and technology. It encompasses a wide range of styles from ambient and chill (like Tycho or ODESZA) to high-energy dance music (like Skrillex or Martin Garrix). Electronic music is perfect for workouts, parties, studying, or creating atmosphere. It's incredibly versatile and can match any mood or activity you're in."
            
            elif 'rock' in question_lower:
                insight = "Rock music emerged in the 1950s and has evolved into countless subgenres. It's characterized by electric guitars, strong rhythms, and often rebellious or emotional themes. Rock can be soft and melodic (like The Beatles or Fleetwood Mac) or heavy and aggressive (like Metallica or Slipknot). It's perfect for workouts, driving, or when you want to feel powerful and energized. Rock music has shaped popular culture and continues to influence modern music."
            
            # Enhanced artist responses
            elif 'drake' in question_lower:
                insight = "Drake is a Canadian rapper, singer, and actor who has become one of the most successful artists of the 21st century. Known for his melodic rap style, emotional lyrics, and ability to blend hip-hop with R&B, Drake has created hits like 'Hotline Bling,' 'God's Plan,' and 'One Dance.' His music often explores themes of love, success, and personal growth. Drake's versatile style makes his music suitable for various moods - from party anthems to introspective tracks."
            
            elif 'beatles' in question_lower:
                insight = "The Beatles were an English rock band formed in Liverpool in 1960, widely regarded as the most influential band in popular music history. Their music evolved from simple pop songs to complex, experimental compositions. They pioneered recording techniques and influenced countless artists. Their catalog includes everything from upbeat pop ('Hey Jude') to psychedelic rock ('Lucy in the Sky with Diamonds') to gentle ballads ('Let It Be'). The Beatles' music is timeless and suitable for any mood or occasion."
            
            elif 'taylor swift' in question_lower:
                insight = "Taylor Swift is an American singer-songwriter known for her narrative songwriting and genre-spanning career. She started in country music and has evolved into pop, indie folk, and alternative styles. Her music often tells personal stories and explores themes of love, heartbreak, and personal growth. Albums like '1989' are perfect for upbeat, confident moods, while 'folklore' and 'evermore' are ideal for introspective, calm moments. Taylor's music is great for driving, working out, or emotional processing."
            
            elif 'kendrick lamar' in question_lower:
                insight = "Kendrick Lamar is an American rapper and songwriter known for his socially conscious lyrics and innovative musical style. His music addresses themes of race, inequality, and personal struggle with poetic depth. Albums like 'To Pimp A Butterfly' and 'DAMN.' are considered modern classics. Kendrick's music is perfect for deep listening, studying, or when you want to engage with meaningful, thought-provoking content. His complex wordplay and powerful messages make his music both entertaining and intellectually stimulating."
            
            elif 'queen' in question_lower:
                insight = "Queen was a British rock band formed in 1970, known for their theatrical performances and diverse musical style. Led by the charismatic Freddie Mercury, they created anthems like 'Bohemian Rhapsody,' 'We Will Rock You,' and 'Another One Bites the Dust.' Queen's music combines rock with opera, disco, and other genres, creating a unique sound. Their music is perfect for workouts, parties, or when you want to feel powerful and confident. Queen's songs are known for their energy and ability to bring people together."
            
            # Enhanced complex scenario responses
            elif 'party' in question_lower:
                insight = "For a party playlist, you want high-energy music that gets people dancing and creates a fun atmosphere. Mix different genres to appeal to various tastes: include pop hits (like Dua Lipa or The Weeknd), hip-hop bangers (like Drake or Travis Scott), electronic dance music (like Calvin Harris or David Guetta), and classic party songs (like 'Uptown Funk' or 'Happy'). Aim for songs with strong beats (120-140 BPM) and positive energy. Don't forget to include some crowd-pleasing classics that everyone knows!"
            
            elif 'anxiety' in question_lower or 'depression' in question_lower:
                insight = "Music can be a powerful tool for managing anxiety and depression. Look for calming, gentle music with slow tempos and soothing melodies. Genres like ambient, classical, or acoustic music can help reduce stress and provide comfort. Artists like Sigur Rós, Bon Iver, or instrumental composers like Max Richter create music that can help calm your mind. However, remember that music is just one tool - if you're struggling, please reach out to mental health professionals for support."
            
            elif 'meditation' in question_lower or 'yoga' in question_lower:
                insight = "For meditation and yoga, choose music that supports mindfulness and inner peace. Look for ambient music, nature sounds, or gentle instrumental pieces with minimal variation. Avoid anything with lyrics or strong rhythms that might distract you. Artists like Brian Eno, Tycho, or composers like Ludovico Einaudi create perfect meditation music. The music should fade into the background, supporting your practice without becoming the focus."
            
            elif 'discover' in question_lower or 'new artists' in question_lower:
                insight = "Discovering new artists is exciting! Start by exploring music similar to what you already love - streaming platforms have great 'discover' features. Try listening to different genres, check out music from different countries, or explore artists from different time periods. Attend local concerts, listen to music podcasts, or ask friends for recommendations. Remember that it's okay not to like everything - the goal is to expand your musical horizons and find new favorites that resonate with you."
            
            else:
                # Generic but helpful response
                insight = f"I can help you with music recommendations! For '{question}', consider what mood you're in and what activity you're doing. Different situations call for different types of music - energetic for workouts, calm for relaxation, focused for work, and so on. What specific mood or activity are you looking for music for? I can provide detailed recommendations based on your needs."
            
            # Add personalization based on user context if available
            personalized_suffix = ""
            if user_context:
                personalized_suffix = self._generate_personalization_suffix(user_context, question_lower)
                if personalized_suffix:
                    insight = insight + " " + personalized_suffix
            
            # Determine model attribution
            model_used = 'Hugging Face (Free) - Intelligent Response'
            if user_context and 'USER PROFILE' in user_context:
                model_used = 'TuneGenie AI (Personalized)'
            elif is_follow_up and prev_topic:
                model_used = 'TuneGenie AI (Conversation Memory)'
            
            return {
                'insight': insight,
                'question': question,
                'timestamp': datetime.now().isoformat(),
                'model_used': model_used
            }
            
        except Exception as e:
            logger.error(f"Intelligent fallback failed: {e}")
            # Ultimate fallback
            return {
                'insight': f"I can help you with music recommendations! For '{question}', here are some general tips based on your context. Try asking about specific genres, moods, or activities.",
                'question': question,
                'timestamp': datetime.now().isoformat(),
                'model_used': 'Hugging Face (Free) - Fallback'
            }
    
    def _generate_personalization_suffix(self, user_context: str, question_lower: str) -> str:
        """
        Generate a personalized recommendation suffix based on user's listening profile.
        
        Args:
            user_context: The user's profile context string
            question_lower: The lowercase question for context matching
            
        Returns:
            A personalized recommendation string to append to the insight
        """
        try:
            if not user_context or 'USER PROFILE' not in user_context:
                return ""
            
            context_lower = user_context.lower()
            personalization_parts = []
            
            # Extract user's favorite genres from context
            favorite_genres = []
            if 'favorite genres:' in context_lower:
                genres_line = context_lower.split('favorite genres:')[1].split('\n')[0]
                favorite_genres = [g.strip() for g in genres_line.split(',') if g.strip()]
            
            # Extract music style preferences
            style_prefs = []
            if 'music style preferences:' in context_lower:
                style_line = context_lower.split('music style preferences:')[1].split('\n')[0]
                style_prefs = [s.strip() for s in style_line.split(',') if s.strip()]
            
            # Extract recent artists
            recent_artists = []
            if 'recently listening to:' in context_lower:
                artists_line = context_lower.split('recently listening to:')[1].split('\n')[0]
                recent_artists = [a.strip() for a in artists_line.split(',') if a.strip()]
            
            # Generate personalized recommendations
            if favorite_genres:
                # Match question context with user's genres
                if any(word in question_lower for word in ['recommend', 'suggest', 'what', 'which']):
                    if len(favorite_genres) >= 2:
                        personalization_parts.append(
                            f"Based on your listening history, I see you enjoy {favorite_genres[0]} and {favorite_genres[1]} - "
                            f"artists from these genres might resonate with you."
                        )
                    elif favorite_genres:
                        personalization_parts.append(
                            f"Since you're a fan of {favorite_genres[0]}, you might enjoy exploring similar artists."
                        )
            
            if style_prefs:
                # Add style-based recommendations
                if 'high-energy' in style_prefs or 'upbeat' in style_prefs:
                    if 'calm' in question_lower or 'relax' in question_lower or 'sleep' in question_lower:
                        personalization_parts.append(
                            "I notice you usually prefer energetic music, but for relaxation, "
                            "you might try acoustic versions of songs from your favorite artists."
                        )
                elif 'acoustic' in style_prefs or 'lo-fi' in style_prefs:
                    if 'workout' in question_lower or 'exercise' in question_lower or 'party' in question_lower:
                        personalization_parts.append(
                            "While you typically enjoy acoustic/lo-fi music, for this activity, "
                            "consider more upbeat versions or remixes of your favorite tracks."
                        )
            
            if recent_artists and not personalization_parts:
                # Suggest similar artists
                personalization_parts.append(
                    f"Since you've been listening to {recent_artists[0]} recently, "
                    f"you might also enjoy exploring similar artists in that style."
                )
            
            return " ".join(personalization_parts)
            
        except Exception as e:
            logger.warning(f"Failed to generate personalization suffix: {e}")
            return ""
    
    def _get_openai_insights(self, question: str, user_context: str = "", history_context: str = "") -> Dict:
        """Get insights using OpenAI model with enhanced fallback and conversation memory"""
        try:
            # Create a system message for music insights with conversation awareness
            system_message = """You are TuneGenie, an AI-powered music expert with conversation memory.
            Provide helpful, accurate, and engaging music insights, recommendations, and advice.
            Be conversational but informative. If you don't know something, say so honestly.
            
            IMPORTANT: Pay attention to the conversation history provided. If this is a follow-up question,
            reference and build upon previous answers. Use context from earlier in the conversation.
            
            Focus on:
            - Specific music recommendations based on mood/activity
            - Genre explanations and characteristics
            - Artist information and musical style
            - Practical advice for music selection
            - Emotional and psychological aspects of music
            - Connecting new answers to previous conversation context"""
            
            # Create user message with conversation history
            user_message = ""
            if history_context:
                user_message += f"{history_context}\n"
            user_message += f"Current question: {question}"
            if user_context:
                user_message += f"\nUser context: {user_context}"
            
            # Make API call
            response = self.llm.invoke([HumanMessage(content=user_message)])
            
            # Extract response
            insight = response.content.strip()
            
            return {
                'insight': insight,
                'question': question,
                'timestamp': datetime.now().isoformat(),
                'model_used': f'OpenAI ({self.model_name})'
            }
            
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}")
            # Enhanced fallback: use intelligent fallback instead of error
            logger.info("Falling back to intelligent fallback system")
            return self._get_intelligent_fallback(question, user_context, history_context)
    
    def _get_openai_insights_stream(self, question: str, user_context: str = "", history_context: str = ""):
        """
        Get insights using OpenAI model with streaming support (generator)
        
        Yields chunks of text as they're generated by the OpenAI API.
        """
        try:
            # Create a system message for music insights with conversation awareness
            system_message = """You are TuneGenie, an AI-powered music expert with conversation memory.
            Provide helpful, accurate, and engaging music insights, recommendations, and advice.
            Be conversational but informative. If you don't know something, say so honestly.
            
            IMPORTANT: Pay attention to the conversation history provided. If this is a follow-up question,
            reference and build upon previous answers. Use context from earlier in the conversation.
            
            Focus on:
            - Specific music recommendations based on mood/activity
            - Genre explanations and characteristics
            - Artist information and musical style
            - Practical advice for music selection
            - Emotional and psychological aspects of music
            - Connecting new answers to previous conversation context"""
            
            # Create user message with conversation history
            user_message = ""
            if history_context:
                user_message += f"{history_context}\n"
            user_message += f"Current question: {question}"
            if user_context:
                user_message += f"\nUser context: {user_context}"
            
            # Create messages for streaming
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_message)
            ]
            
            # Stream the response chunk by chunk
            full_response = ""
            for chunk in self.llm.stream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    content = chunk.content
                    full_response += content
                    yield content
            
            # If streaming returned empty, fallback to non-streaming
            if not full_response.strip():
                logger.warning("Streaming returned empty, falling back to non-streaming")
                response = self.llm.invoke(messages)
                if hasattr(response, 'content'):
                    yield response.content.strip()
            
        except Exception as e:
            logger.warning(f"OpenAI streaming failed: {e}")
            # Fallback to intelligent fallback with simulated streaming
            logger.info("Falling back to intelligent fallback with simulated streaming")
            fallback_result = self._get_intelligent_fallback(question, user_context, history_context)
            insight = fallback_result.get('insight', '')
            # Simulate streaming by yielding in chunks
            chunk_size = 10
            for i in range(0, len(insight), chunk_size):
                yield insight[i:i + chunk_size]
                time.sleep(0.05)  # Small delay to simulate streaming
    
    def save_prompt_template(self, prompt_name: str, template: str) -> bool:
        """
        Save a custom prompt template
        
        Args:
            prompt_name: Name of the prompt
            template: Prompt template content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            os.makedirs('prompts', exist_ok=True)
            prompt_file = os.path.join('prompts', f"{prompt_name}.txt")
            
            with open(prompt_file, 'w') as f:
                f.write(template)
            
            # Update in-memory prompts
            self.prompts[prompt_name] = template
            
            logger.info(f"Saved prompt template: {prompt_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save prompt template: {e}")
            return False
    
    def get_agent_info(self) -> Dict:
        """Get information about the LLM agent"""
        return {
            'model_name': self.model_name,
            'temperature': self.temperature,
            'available_prompts': list(self.prompts.keys()),
            'api_key_configured': bool(self.api_key)
        }

    def _analyze_mood_huggingface(self, user_context: str, mood: str, activity: str) -> Dict:
        """Analyze mood using Hugging Face model"""
        try:
            prompt = f"Analyze this mood and activity for music: Mood: {mood}, Activity: {activity}, Context: {user_context}"
            response = requests.post(
                self.model_url,
                headers=self.headers,
                json={"inputs": prompt}
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    analysis = result[0].get('generated_text', '')
                    return {
                        'mood_analysis': analysis[:200] + "..." if len(analysis) > 200 else analysis,
                        'music_characteristics': {
                            'tempo': 'medium' if mood in ['calm', 'focused'] else 'high',
                            'energy': 'low' if mood in ['calm', 'relaxed'] else 'high',
                            'valence': 'positive' if mood in ['happy', 'excited'] else 'neutral'
                        }
                    }
            
            # Fallback
            return {
                'mood_analysis': f"Based on your {mood} mood and {activity} activity, I recommend music that matches your current state.",
                'music_characteristics': {
                    'tempo': 'medium' if mood in ['calm', 'focused'] else 'high',
                    'energy': 'low' if mood in ['calm', 'relaxed'] else 'high',
                    'valence': 'positive' if mood in ['happy', 'excited'] else 'neutral'
                }
            }
        except Exception as e:
            logger.error(f"Hugging Face mood analysis failed: {e}")
            return {
                'mood_analysis': f"Based on your {mood} mood and {activity} activity, I recommend music that matches your current state.",
                'music_characteristics': {
                    'tempo': 'medium' if mood in ['calm', 'focused'] else 'high',
                    'energy': 'low' if mood in ['calm', 'relaxed'] else 'high',
                    'valence': 'positive' if mood in ['happy', 'excited'] else 'neutral'
                }
            }
    
    def _enhance_recommendations_huggingface(self, user_data: Dict, context: str, collaborative_recs: List[Dict]) -> Dict:
        """Enhance recommendations using Hugging Face model"""
        try:
            prompt = f"Enhance these music recommendations for context: {context}. Tracks: {len(collaborative_recs)} available."
            response = requests.post(
                self.model_url,
                headers=self.headers,
                json={"inputs": prompt}
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    enhancement = result[0].get('generated_text', '')
                    return {
                        'description': enhancement[:200] + "..." if len(enhancement) > 200 else enhancement,
                        'adjustments': "Recommendations optimized for your context",
                        'playlist_name': "Personalized TuneGenie Playlist"
                    }
            
            # Fallback
            return {
                'description': f"Enhanced playlist based on {context}",
                'adjustments': "Recommendations optimized for your current context",
                'playlist_name': "Personalized TuneGenie Playlist"
            }
        except Exception as e:
            logger.error(f"Hugging Face enhancement failed: {e}")
            return {
                'description': f"Enhanced playlist based on {context}",
                'adjustments': "Recommendations optimized for your current context",
                'playlist_name': "Personalized TuneGenie Playlist"
            }
    
    def _generate_playlist_huggingface(self, user_data: Dict, mood: str, activity: str, available_tracks: List[Dict], num_tracks: int = 20) -> Dict:
        """Generate playlist using Hugging Face model"""
        try:
            prompt = f"Generate a playlist for mood: {mood}, activity: {activity}. Available tracks: {len(available_tracks)}. Target tracks: {num_tracks}"
            response = requests.post(
                self.model_url,
                headers=self.headers,
                json={"inputs": prompt}
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    generation = result[0].get('generated_text', '')
                    return {
                        'playlist_name': f'TuneGenie {mood} {activity} Playlist',
                        'description': generation[:200] + "..." if len(generation) > 200 else generation,
                        'selected_tracks': available_tracks[:num_tracks],
                        'tracks': available_tracks[:num_tracks]
                    }
            
            # Fallback
            return {
                'playlist_name': f'TuneGenie {mood} {activity} Playlist',
                'description': f'AI-generated playlist for {mood} mood during {activity}',
                'selected_tracks': available_tracks[:num_tracks],
                'tracks': available_tracks[:num_tracks]
            }
        except Exception as e:
            logger.error(f"Hugging Face playlist generation failed: {e}")
            return {
                'playlist_name': f'TuneGenie {mood} {activity} Playlist',
                'description': f'AI-generated playlist for {mood} mood during {activity}',
                'selected_tracks': available_tracks[:num_tracks],
                'tracks': available_tracks[:num_tracks]
            }
    
    def _generate_fallback_playlist(self, user_data: Dict, mood: str, activity: str, available_tracks: List[Dict], num_tracks: int = 20) -> Dict:
        """Fallback playlist generation if LLM fails"""
        logger.warning(f"LLM playlist generation failed, falling back to default for {mood} {activity}")
        return {
            'playlist_name': f'TuneGenie {mood} {activity} Playlist',
            'description': f'AI-generated playlist for {mood} mood during {activity}',
            'selected_tracks': available_tracks[:num_tracks],
            'tracks': available_tracks[:num_tracks]
        }
    
    def _analyze_mood_openai(self, user_context: str, mood: str, activity: str) -> Dict:
        """Analyze mood using OpenAI model"""
        try:
            system_message = """You are a music expert. Analyze the user's mood and activity to suggest music characteristics."""
            user_message = f"Context: {user_context}\nMood: {mood}\nActivity: {activity}"
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_message)
            ]
            
            response = self.llm.invoke(messages)
            return {
                'mood_analysis': response.content,
                'music_characteristics': {
                    'tempo': 'medium' if mood in ['calm', 'focused'] else 'high',
                    'energy': 'low' if mood in ['calm', 'relaxed'] else 'high',
                    'valence': 'positive' if mood in ['happy', 'excited'] else 'neutral'
                }
            }
        except Exception as e:
            logger.error(f"OpenAI mood analysis failed: {e}")
            return {
                'mood_analysis': f"Based on your {mood} mood and {activity} activity, I recommend music that matches your current state.",
                'music_characteristics': {
                    'tempo': 'medium' if mood in ['calm', 'focused'] else 'high',
                    'energy': 'low' if mood in ['calm', 'relaxed'] else 'high',
                    'valence': 'positive' if mood in ['happy', 'excited'] else 'neutral'
                }
            }
    
    def _enhance_recommendations_openai(self, user_data: Dict, context: str, collaborative_recs: List[Dict]) -> Dict:
        """Enhance recommendations using OpenAI model"""
        try:
            system_message = """You are a music curator. Enhance these recommendations with context."""
            user_message = f"Context: {context}\nRecommendations: {len(collaborative_recs)} tracks"
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_message)
            ]
            
            response = self.llm.invoke(messages)
            return {
                'description': response.content,
                'adjustments': "Recommendations optimized for your context",
                'playlist_name': "Personalized TuneGenie Playlist"
            }
        except Exception as e:
            logger.error(f"OpenAI enhancement failed: {e}")
            return {
                'description': f"Enhanced playlist based on {context}",
                'adjustments': "Recommendations optimized for your current context",
                'playlist_name': "Personalized TuneGenie Playlist"
            }
    
    def _generate_playlist_openai(self, user_data: Dict, mood: str, activity: str, available_tracks: List[Dict], num_tracks: int = 20) -> Dict:
        """Generate playlist using OpenAI model"""
        try:
            system_message = """You are a music playlist curator. Generate a playlist description."""
            user_message = f"Mood: {mood}\nActivity: {activity}\nTracks: {len(available_tracks)} available. Target tracks: {num_tracks}"
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_message)
            ]
            
            response = self.llm.invoke(messages)
            return {
                'playlist_name': f'TuneGenie {mood} {activity} Playlist',
                'description': response.content,
                'selected_tracks': available_tracks[:num_tracks],
                'tracks': available_tracks[:num_tracks]
            }
        except Exception as e:
            logger.error(f"OpenAI playlist generation failed: {e}")
            return {
                'playlist_name': f'TuneGenie {mood} {activity} Playlist',
                'description': f'AI-generated playlist for {mood} mood during {activity}',
                'selected_tracks': available_tracks[:num_tracks],
                'tracks': available_tracks[:num_tracks]
            }
    
    # =========================================================
    # ENHANCED AI INSIGHTS METHODS
    # =========================================================
    
    def _init_enhanced_features(self, spotify_client=None):
        """
        Lazy initialize enhanced AI Insights features.
        
        Args:
            spotify_client: Spotify client for toolkit operations
        """
        if not ENHANCED_INSIGHTS_AVAILABLE:
            return
        
        try:
            # Initialize ReasoningEngine
            if self.reasoning_engine is None:
                self.reasoning_engine = ReasoningEngine(self, spotify_client)
                logger.info("🧠 ReasoningEngine initialized")
            
            # Initialize MusicToolkit
            if self.toolkit is None and spotify_client:
                self.toolkit = MusicToolkit(spotify_client, self)
                logger.info("🔧 MusicToolkit initialized with Spotify client")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced features: {e}")
    
    def _get_user_memory(self, user_id: str) -> 'MemorySystem':
        """
        Get or create a MemorySystem for a user.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            MemorySystem instance for the user
        """
        if not ENHANCED_INSIGHTS_AVAILABLE:
            return None
        
        if user_id not in self.memory_systems:
            try:
                self.memory_systems[user_id] = MemorySystem(user_id)
                logger.info(f"🧠 Created MemorySystem for user: {user_id[:8]}...")
            except Exception as e:
                logger.error(f"Failed to create MemorySystem: {e}")
                return None
        
        return self.memory_systems[user_id]
    
    def get_music_insights_enhanced(
        self,
        question: str,
        user_id: str = "anonymous",
        context: Dict = None,
        spotify_client=None,
        show_reasoning: bool = True
    ) -> Dict:
        """
        Get AI-powered music insights with enhanced reasoning, memory, and security.
        
        This method provides advanced capabilities:
        - Chain-of-thought reasoning with 5 specialized modes
        - Multi-tier memory (short-term, long-term, semantic)
        - Security validation and sanitization
        - Confidence scoring and source attribution
        
        Args:
            question: User's question about music
            user_id: Unique user identifier for memory
            context: User context (top_artists, top_tracks, profile, etc.)
            spotify_client: Spotify client for real-time data access
            show_reasoning: Whether to include reasoning steps in response
            
        Returns:
            Dict containing:
              - response: AI-generated answer
              - reasoning_steps: List of reasoning steps (if show_reasoning=True)
              - confidence: Confidence score (0-1)
              - sources: Data sources used
              - memory_stats: Memory system statistics
        """
        context = context or {}
        
        # =========================================================
        # STEP 1: Security validation
        # =========================================================
        if ENHANCED_INSIGHTS_AVAILABLE:
            try:
                # Validate input
                is_valid, error = InputValidator.validate_question(question)
                if not is_valid:
                    logger.warning(f"Input validation failed: {error}")
                    return {
                        'response': f"I couldn't process that question. {error}",
                        'reasoning_steps': [],
                        'confidence': 0.0,
                        'sources': [],
                        'error': error
                    }
                
                # Check for malicious intent
                is_malicious, attack_type = SecurityUtils.detect_malicious_intent(question)
                if is_malicious:
                    logger.warning(f"Malicious input detected: {attack_type}")
                    return {
                        'response': "I'd love to help you with music questions! Please ask something about songs, artists, genres, or recommendations.",
                        'reasoning_steps': [],
                        'confidence': 1.0,
                        'sources': ['security'],
                        'blocked': True,
                        'reason': 'input_validation'
                    }
                
                # Sanitize input
                question = SecurityUtils.validate_input(question)
            except Exception as e:
                logger.error(f"Security validation error: {e}")
                # Continue with unsanitized input if validation fails
        
        # =========================================================
        # STEP 2: Initialize enhanced features
        # =========================================================
        if ENHANCED_INSIGHTS_AVAILABLE and self.enhanced_enabled:
            self._init_enhanced_features(spotify_client)
        
        # =========================================================
        # STEP 3: Memory operations
        # =========================================================
        memory = None
        conversation_history = []
        
        if ENHANCED_INSIGHTS_AVAILABLE and self.enhanced_enabled:
            memory = self._get_user_memory(user_id)
            
            if memory:
                try:
                    # Add question to short-term memory
                    memory.short_term.add('user', question)
                    
                    # Get conversation history for context
                    conversation_history = [
                        {'role': msg['role'], 'content': msg['content']}
                        for msg in memory.short_term.get_recent(5)
                    ]
                except Exception as e:
                    logger.error(f"Memory operation failed: {e}")
        
        # =========================================================
        # STEP 4: Reasoning Engine (if available)
        # =========================================================
        result = None
        
        if ENHANCED_INSIGHTS_AVAILABLE and self.enhanced_enabled and self.reasoning_engine:
            try:
                result = self.reasoning_engine.reason_about_query(
                    query=question,
                    context=context,
                    show_reasoning=show_reasoning and self.show_reasoning
                )
                
                # Format the result
                if result:
                    result = {
                        'response': result.get('response', 'No response generated'),
                        'reasoning_steps': result.get('reasoning_steps', []),
                        'confidence': result.get('confidence', 0.7),
                        'sources': result.get('sources', ['reasoning_engine']),
                        'reasoning_type': result.get('reasoning_type', 'general')
                    }
            except Exception as e:
                logger.error(f"ReasoningEngine failed: {e}")
                result = None
        
        # =========================================================
        # STEP 5: Fallback to standard insights
        # =========================================================
        if result is None:
            try:
                # Use standard get_music_insights method
                standard_result = self.get_music_insights(
                    question=question,
                    user_context=str(context),
                    conversation_history=conversation_history
                )
                
                result = {
                    'response': standard_result.get('answer', standard_result.get('insight', 'No response')),
                    'reasoning_steps': [],
                    'confidence': 0.7,
                    'sources': ['llm'],
                    'reasoning_type': 'standard'
                }
            except Exception as e:
                logger.error(f"Standard insights failed: {e}")
                result = {
                    'response': f"I encountered an issue processing your question: {str(e)}",
                    'reasoning_steps': [],
                    'confidence': 0.0,
                    'sources': [],
                    'error': str(e)
                }
        
        # =========================================================
        # STEP 6: Update memory with response
        # =========================================================
        if memory:
            try:
                # Add response to short-term memory
                memory.short_term.add('assistant', result['response'])
                
                # Record interaction in long-term memory
                memory.long_term.add_interaction(
                    interaction_type='ai_insights_query',
                    details={
                        'query': question[:100],  # Truncate for storage
                        'response_length': len(result['response']),
                        'confidence': result.get('confidence', 0),
                        'reasoning_type': result.get('reasoning_type', 'standard')
                    }
                )
                
                # Add memory stats to result
                result['memory_stats'] = memory.get_context_summary()
            except Exception as e:
                logger.error(f"Memory update failed: {e}")
        
        # =========================================================
        # STEP 7: Output sanitization
        # =========================================================
        if ENHANCED_INSIGHTS_AVAILABLE and result.get('response'):
            try:
                result['response'] = SecurityUtils.sanitize_output(
                    result['response'],
                    escape_html=False  # Don't escape for Streamlit markdown
                )
            except Exception as e:
                logger.error(f"Output sanitization failed: {e}")
        
        # Add metadata
        result['enhanced'] = ENHANCED_INSIGHTS_AVAILABLE and self.enhanced_enabled
        result['timestamp'] = datetime.now().isoformat()
        result['user_id'] = user_id[:8] + '...' if len(user_id) > 8 else user_id
        
        return result
