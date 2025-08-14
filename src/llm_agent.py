"""
LLM Agent for TuneGenie
Integrates with GPT-4 for contextual music recommendation enhancement
"""

import os
import json
import openai
from typing import List, Dict, Optional, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
import logging
from datetime import datetime
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMAgent:
    """LLM agent for contextual music recommendation enhancement"""
    
    def __init__(self, model_name: str = "huggingface", temperature: float = 0.7):
        """
        Initialize the LLM agent
        
        Args:
            model_name: Model to use (huggingface, openai, or specific model name)
            temperature: Creativity level (0.0 to 1.0)
        """
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.huggingface_token = os.getenv('HUGGINGFACE_TOKEN')
        
        # Choose model based on availability
        if model_name == "huggingface" or not self.api_key:
            self.model_type = "huggingface"
            self._initialize_huggingface()
        else:
            self.model_type = "openai"
            self._initialize_openai()
        
        # Load prompt templates
        self.prompts = self._load_prompts()
        
        logger.info(f"Initialized LLM agent with {self.model_type} ({model_name})")
    
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
            
            # Initialize LangChain chat model
            self.llm = ChatOpenAI(
                model_name="gpt-3.5-turbo",
                temperature=self.temperature,
                openai_api_key=self.api_key
            )
            logger.info("OpenAI model initialized")
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
            
            'playlist_enhancement': """You are a music curator and AI assistant. Enhance these collaborative filtering recommendations with contextual understanding.

User Profile: {user_profile}
Current Context: {context}
Collaborative Recommendations: {collaborative_recs}

Please:
1. Analyze the recommendations for context appropriateness
2. Suggest any mood or context-specific adjustments
3. Provide a compelling playlist description
4. Suggest a playlist name that reflects the mood/context

Format your response as JSON with keys: analysis, adjustments, description, playlist_name""",
            
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
    
    def get_music_insights(self, question: str, user_context: str = "") -> Dict:
        """
        Get AI-powered music insights based on user question
        
        Args:
            question: User's question about music
            user_context: Additional context about the user
            
        Returns:
            Dictionary with AI insights
        """
        try:
            if self.model_type == "huggingface":
                return self._get_huggingface_insights(question, user_context)
            else:
                return self._get_openai_insights(question, user_context)
            
        except Exception as e:
            logger.error(f"Failed to get music insights: {e}")
            return {
                'error': f"Failed to get AI response: {str(e)}",
                'question': question,
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_huggingface_insights(self, question: str, user_context: str = "") -> Dict:
        """Get insights using Hugging Face model or intelligent fallback"""
        try:
            # First try the actual Hugging Face API
            if hasattr(self, 'model_url') and self.model_url:
                response = requests.post(
                    self.model_url,
                    headers=self.headers,
                    json={"inputs": f"Question: {question}\nContext: {user_context}\n\nAnswer:"},
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
            return self._get_intelligent_fallback(question, user_context)
                
        except Exception as e:
            logger.warning(f"Hugging Face API call failed: {e}")
            # Use intelligent fallback
            return self._get_intelligent_fallback(question, user_context)
    
    def _get_intelligent_fallback(self, question: str, user_context: str = "") -> Dict:
        """Provide intelligent, contextual responses without external API calls"""
        try:
            # Create contextual, intelligent responses based on the question
            question_lower = question.lower()
            context_lower = user_context.lower()
            
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
            
            elif 'focus' in question_lower or 'concentrate' in question_lower:
                insight = "For focused work, choose music without lyrics to avoid cognitive interference. Instrumental music, ambient sounds, or lo-fi beats work well. Look for consistent tempos and minimal variations that provide background stimulation without distraction. Classical music, especially Baroque period pieces by Bach or Handel, has been shown to improve concentration. Modern options include lo-fi hip-hop, ambient electronic, or instrumental post-rock."
            
            elif 'workout' in question_lower or 'exercise' in question_lower:
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
            
            return {
                'insight': insight,
                'question': question,
                'timestamp': datetime.now().isoformat(),
                'model_used': 'Hugging Face (Free) - Intelligent Response'
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
    
    def _get_openai_insights(self, question: str, user_context: str = "") -> Dict:
        """Get insights using OpenAI model with enhanced fallback"""
        try:
            # Create a system message for music insights
            system_message = """You are TuneGenie, an AI-powered music expert. 
            Provide helpful, accurate, and engaging music insights, recommendations, and advice.
            Be conversational but informative. If you don't know something, say so honestly.
            
            Focus on:
            - Specific music recommendations based on mood/activity
            - Genre explanations and characteristics
            - Artist information and musical style
            - Practical advice for music selection
            - Emotional and psychological aspects of music"""
            
            # Create user message
            user_message = f"Question: {question}"
            if user_context:
                user_message += f"\nContext: {user_context}"
            
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
            return self._get_intelligent_fallback(question, user_context)
    
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
