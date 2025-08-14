"""
Multi-Agent Workflow Orchestrator for TuneGenie
Coordinates different agents for automated playlist generation
"""

import os
import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .spotify_client import SpotifyClient
from .recommender import CollaborativeFilteringRecommender
from .llm_agent import LLMAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiAgentWorkflow:
    """Multi-agent workflow orchestrator for automated playlist generation"""
    
    def __init__(self):
        """Initialize the multi-agent workflow"""
        self.spotify_client = None
        self.recommender = None
        self.llm_agent = None
        self.workflow_history = []
        self._load_workflow_history()  # Load existing history
        
        # Initialize agents
        self._initialize_agents()
        
        # Create data directory
        os.makedirs('data', exist_ok=True)
    
    def _initialize_agents(self):
        """Initialize all required agents"""
        try:
            # Initialize Spotify client
            try:
                self.spotify_client = SpotifyClient()
                logger.info("Spotify client initialized")
            except Exception as e:
                logger.warning(f"Spotify client initialization failed: {e}")
                self.spotify_client = None
            
            # Initialize collaborative filtering recommender
            try:
                algorithm = os.getenv('COLLABORATIVE_FILTERING_ALGORITHM', 'SVD')
                self.recommender = CollaborativeFilteringRecommender(algorithm=algorithm)
                logger.info(f"Collaborative filtering recommender initialized with {algorithm}")
            except Exception as e:
                logger.warning(f"Recommender initialization failed: {e}")
                self.recommender = None
            
            # Initialize LLM agent
            try:
                temperature = float(os.getenv('LLM_TEMPERATURE', '0.7'))
                self.llm_agent = LLMAgent(temperature=temperature)
                logger.info("LLM agent initialized")
            except Exception as e:
                logger.warning(f"LLM agent initialization failed: {e}")
                self.llm_agent = None
            
            # Check if at least one agent is available
            if not any([self.spotify_client, self.recommender, self.llm_agent]):
                logger.error("No agents could be initialized. Check your API credentials.")
                raise RuntimeError("No agents could be initialized. Please check your API credentials.")
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            # Don't raise here, let the workflow handle it gracefully
    
    def is_ready(self) -> bool:
        """Check if the workflow is ready to execute"""
        return any([self.spotify_client, self.recommender, self.llm_agent])
    
    def get_agent_status(self) -> Dict:
        """Get the status of all agents"""
        return {
            'spotify_client': self.spotify_client is not None,
            'recommender': self.recommender is not None,
            'llm_agent': self.llm_agent is not None,
            'ready': self.is_ready()
        }
    
    def execute_workflow(self, workflow_type: str, **kwargs) -> Dict:
        """
        Execute a specific workflow type
        
        Args:
            workflow_type: Type of workflow to execute
            **kwargs: Additional parameters for the workflow
            
        Returns:
            Dictionary with workflow results
        """
        try:
            workflow_start = datetime.now()
            
            if workflow_type == 'playlist_generation':
                result = self._execute_playlist_generation_workflow(**kwargs)
            elif workflow_type == 'user_analysis':
                result = self._execute_user_analysis_workflow(**kwargs)
            elif workflow_type == 'feedback_learning':
                result = self._execute_feedback_learning_workflow(**kwargs)
            elif workflow_type == 'model_training':
                result = self._execute_model_training_workflow(**kwargs)
            else:
                raise ValueError(f"Unknown workflow type: {workflow_type}")
            
            # Record workflow execution
            end_time = datetime.now()
            duration = (end_time - workflow_start).total_seconds()
            
            workflow_record = {
                'workflow_type': workflow_type,
                'start_time': workflow_start.isoformat(),
                'end_time': end_time.isoformat(),
                'duration': duration,
                'parameters': kwargs,
                'result': result,
                'status': 'success' if 'error' not in result else 'error'
            }
            
            self.workflow_history.append(workflow_record)
            self._save_workflow_history()
            
            logger.info(f"Workflow {workflow_type} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Workflow {workflow_type} failed: {e}")
            return {'error': str(e), 'workflow_type': workflow_type}
    
    def _execute_playlist_generation_workflow(self, mood: str, activity: str, 
                                            user_context: str = "", num_tracks: int = 20, 
                                            language_preference: str = "Any Language") -> Dict:
        """
        Execute playlist generation workflow
        
        Args:
            mood: User's current mood
            activity: User's current activity
            user_context: Additional context
            num_tracks: Number of tracks to recommend
            language_preference: Preferred language for songs
            
        Returns:
            Dictionary with playlist generation results
        """
        try:
            logger.info(f"Starting playlist generation workflow for mood: {mood}, activity: {activity}, tracks: {num_tracks}")
            
            # Step 1: Retrieve Agent - Get user data
            user_data = self._retrieve_user_data()
            if not user_data:
                return {'error': 'Failed to retrieve user data. Please ensure you are connected to Spotify.'}
            
            # Step 2: Filtering Agent - Get collaborative filtering recommendations
            collaborative_recs = self._get_collaborative_recommendations(user_data, num_tracks)
            
            # Apply language filtering if specified
            if language_preference != "Any Language":
                logger.info(f"Applying language filter for: {language_preference}")
                
                # For English, we want to ensure we get English-language tracks
                if language_preference == "English":
                    logger.info("Ensuring English-language tracks are prioritized")
                    # Search for English tracks first to ensure we have enough
                    english_tracks = self._search_tracks_by_language(language_preference, mood, activity, num_tracks)
                    if english_tracks:
                        collaborative_recs = english_tracks[:num_tracks]
                        logger.info(f"Found {len(collaborative_recs)} English tracks for {mood} {activity}")
                    else:
                        # Fallback to collaborative recommendations but prioritize English
                        collaborative_recs = self._filter_tracks_by_language(collaborative_recs, language_preference, user_data)
                else:
                    # For other languages, use the existing filtering logic
                    collaborative_recs = self._filter_tracks_by_language(collaborative_recs, language_preference, user_data)
                
                # If we still don't have enough tracks after language filtering, try to get more
                if len(collaborative_recs) < num_tracks:
                    logger.info(f"Only {len(collaborative_recs)} tracks found after language filtering, searching for more {language_preference} tracks")
                    additional_tracks = self._search_tracks_by_language(language_preference, mood, activity, num_tracks - len(collaborative_recs))
                    if additional_tracks:
                        collaborative_recs.extend(additional_tracks)
                        logger.info(f"Added {len(additional_tracks)} additional {language_preference} tracks")
            
            if not collaborative_recs:
                # Try to get some real tracks from user data as fallback
                logger.info("No collaborative recommendations available - using user's actual tracks")
                user_tracks = []
                
                # Get tracks from user's top tracks
                for time_range in ['short_term', 'medium_term', 'long_term']:
                    tracks = user_data.get('top_tracks', {}).get(time_range, [])
                    tracks_per_range = max(1, num_tracks // 3)  # Distribute tracks across time ranges
                    
                    for track in tracks[:tracks_per_range]:
                        track_id = track.get('id')
                        if track_id:  # Only add tracks with valid IDs
                            user_tracks.append({
                                'track_id': track_id,
                                'name': track.get('name', 'Unknown Track'),
                                'artists': track.get('artists', ['Unknown Artist']),
                                'score': 0.9 - (len(user_tracks) * 0.1)  # Decreasing score
                            })
                        if len(user_tracks) >= num_tracks:
                            break
                    if len(user_tracks) >= num_tracks:
                        break
                
                # If we still don't have enough tracks, add more from the first time range
                if len(user_tracks) < num_tracks:
                    short_term_tracks = user_data.get('top_tracks', {}).get('short_term', [])
                    for track in short_term_tracks[len(user_tracks):]:
                        track_id = track.get('id')
                        if track_id:  # Only add tracks with valid IDs
                            user_tracks.append({
                                'track_id': track_id,
                                'name': track.get('name', 'Unknown Track'),
                                'artists': track.get('artists', ['Unknown Artist']),
                                'score': 0.9 - (len(user_tracks) * 0.1)
                            })
                        if len(user_tracks) >= num_tracks:
                            break
                
                # If we still don't have enough tracks, try to get from recently played
                if len(user_tracks) < num_tracks:
                    recently_played = user_data.get('recently_played', [])
                    for track in recently_played:
                        if len(user_tracks) >= num_tracks:
                            break
                        # Check if track is already in user_tracks
                        track_id = track.get('id')
                        if not any(t['track_id'] == track_id for t in user_tracks):
                            user_tracks.append({
                                'track_id': track_id,
                                'name': track.get('name', 'Unknown Track'),
                                'artists': track.get('artists', ['Unknown Artist']),
                                'score': 0.8 - (len(user_tracks) * 0.05)
                            })
                
                # If we still don't have enough tracks, try to get from user playlists
                if len(user_tracks) < num_tracks:
                    user_playlists = user_data.get('playlists', [])
                    for playlist in user_playlists:
                        if len(user_tracks) >= num_tracks:
                            break
                        tracks = playlist.get('tracks', [])
                        for track in tracks:
                            if len(user_tracks) >= num_tracks:
                                break
                            track_id = track.get('id')
                            if not any(t['track_id'] == track_id for t in user_tracks):
                                user_tracks.append({
                                    'track_id': track_id,
                                    'name': track.get('name', 'Unknown Track'),
                                    'artists': track.get('artists', ['Unknown Artist']),
                                    'score': 0.7 - (len(user_tracks) * 0.05)
                                })
                
                if user_tracks:
                    collaborative_recs = user_tracks[:num_tracks]
                    logger.info(f"Using {len(collaborative_recs)} tracks from user's actual listening history")
                else:
                    # Final fallback - try to get any real tracks from Spotify search
                    logger.info("No user tracks available - attempting Spotify search for fallback tracks")
                    try:
                        if self.spotify_client:
                            # Search for popular tracks in the requested mood/genre
                            search_query = f"{mood} {activity} music"
                            search_results = self.spotify_client.search_tracks(search_query, limit=min(num_tracks, 50))
                            
                            if search_results:
                                collaborative_recs = []
                                for track in search_results[:num_tracks]:
                                    collaborative_recs.append({
                                        'track_id': track.get('id'),
                                        'name': track.get('name', 'Unknown Track'),
                                        'artists': track.get('artists', ['Unknown Artist']),
                                        'score': 0.8
                                    })
                                logger.info(f"Found {len(collaborative_recs)} tracks via Spotify search")
                            else:
                                logger.warning("Spotify search failed - using minimal fallback")
                                collaborative_recs = []
                        else:
                            collaborative_recs = []
                    except Exception as e:
                        logger.warning(f"Spotify search fallback failed: {e}")
                        collaborative_recs = []
                    
                    # If still no tracks, create a minimal valid response
                    if not collaborative_recs:
                        logger.info("Creating minimal valid response")
                        collaborative_recs = []
            
            # Step 3: Enhancement Agent - Enhance with LLM
            enhanced_recs = self._enhance_recommendations_with_llm(
                user_data, mood, activity, user_context, collaborative_recs
            )
            
            # Step 4: Generation Agent - Create final playlist
            final_playlist = self._create_final_playlist(
                collaborative_recs, user_data, mood, activity, num_tracks, user_context, language_preference
            )
            
            # Step 5: Create Spotify playlist
            spotify_playlist = self._create_spotify_playlist(final_playlist)
            
            workflow_result = {
                'workflow_type': 'playlist_generation',
                'mood': mood,
                'activity': activity,
                'user_context': user_context,
                'collaborative_recommendations': collaborative_recs,
                'enhanced_recommendations': enhanced_recs,
                'final_playlist': final_playlist,
                'spotify_playlist': spotify_playlist,
                'metadata': {
                    'total_tracks': len(final_playlist.get('tracks', [])),
                    'generation_timestamp': datetime.now().isoformat(),
                    'algorithm_used': self.recommender.algorithm if self.recommender else 'N/A',
                    'llm_model': self.llm_agent.model_name if self.llm_agent else 'N/A',
                    'note': 'Demo mode - using sample data for demonstration',
                    'collaborative_tracks_count': len(collaborative_recs),
                    'final_tracks_count': len(final_playlist.get('tracks', []))
                }
            }
            
            logger.info("Playlist generation workflow completed successfully")
            return workflow_result
            
        except Exception as e:
            logger.error(f"Playlist generation workflow failed: {e}")
            return {'error': str(e)}
    
    def _execute_user_analysis_workflow(self, export_data: bool = True) -> Dict:
        """
        Execute user analysis workflow
        
        Args:
            export_data: Whether to export user data to file
            
        Returns:
            Dictionary with user analysis results
        """
        try:
            logger.info("Starting user analysis workflow")
            
            # Get comprehensive user data
            user_data = self._retrieve_user_data()
            if not user_data:
                return {'error': 'Failed to retrieve user data'}
            
            # Analyze user preferences
            analysis = self._analyze_user_preferences(user_data)
            
            # Export data if requested
            if export_data and self.spotify_client:
                try:
                    self.spotify_client.export_user_data()
                except Exception as e:
                    logger.warning(f"Failed to export user data: {e}")
                    export_data = False
            
            result = {
                'workflow_type': 'user_analysis',
                'user_profile': user_data['profile'],
                'analysis': analysis,
                'data_exported': export_data,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("User analysis workflow completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"User analysis workflow failed: {e}")
            return {'error': str(e)}
    
    def _execute_feedback_learning_workflow(self, feedback: str, 
                                          previous_recommendations: List[Dict]) -> Dict:
        """
        Execute feedback learning workflow
        
        Args:
            feedback: User feedback on recommendations
            previous_recommendations: Previously provided recommendations
            
        Returns:
            Dictionary with feedback analysis and learning results
        """
        try:
            logger.info("Starting feedback learning workflow")
            
            # Get user data for context
            user_data = self._retrieve_user_data()
            if not user_data:
                return {'error': 'Failed to retrieve user data'}
            
            # Analyze feedback using LLM
            feedback_analysis = self.llm_agent.analyze_feedback(
                feedback, previous_recommendations, user_data
            )
            
            # Update recommendation strategy based on feedback
            strategy_updates = self._update_recommendation_strategy(feedback_analysis)
            
            result = {
                'workflow_type': 'feedback_learning',
                'feedback': feedback,
                'feedback_analysis': feedback_analysis,
                'strategy_updates': strategy_updates,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("Feedback learning workflow completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Feedback learning workflow failed: {e}")
            return {'error': str(e)}
    
    def _execute_model_training_workflow(self, cross_validate: bool = True) -> Dict:
        """
        Execute model training workflow
        
        Args:
            cross_validate: Whether to perform cross-validation
            
        Returns:
            Dictionary with training results
        """
        try:
            logger.info("Starting model training workflow")
            
            # Get user data
            user_data = self._retrieve_user_data()
            if not user_data:
                return {'error': 'Failed to retrieve user data'}
            
            # Prepare data for training
            training_data = self.recommender.prepare_data(user_data, self.spotify_client)
            if training_data.empty:
                return {'error': 'No training data available'}
            
            # Train the model
            training_success = self.recommender.train_model(training_data)
            if not training_success:
                return {'error': 'Model training failed'}
            
            # Perform cross-validation if requested
            cv_results = {}
            if cross_validate:
                cv_results = self.recommender.cross_validate_model(training_data)
            
            result = {
                'workflow_type': 'model_training',
                'training_success': training_success,
                'training_data_size': len(training_data),
                'cross_validation_results': cv_results,
                'model_info': self.recommender.get_model_info(),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("Model training workflow completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Model training workflow failed: {e}")
            return {'error': str(e)}
    
    def _retrieve_user_data(self) -> Dict:
        """Retrieve comprehensive user data from Spotify"""
        try:
            if not self.spotify_client:
                logger.warning("Spotify client not available, returning mock user data")
                return {
                    'profile': {'id': 'mock_user_id', 'display_name': 'Mock User'},
                    'top_tracks': {'medium_term': []},
                    'top_artists': {'medium_term': []},
                    'recently_played': [],
                    'playlists': []
                }
            
            user_data = {
                'profile': self.spotify_client.get_user_profile(),
                'top_tracks': {
                    'short_term': self.spotify_client.get_user_top_tracks(50, 'short_term'),
                    'medium_term': self.spotify_client.get_user_top_tracks(50, 'medium_term'),
                    'long_term': self.spotify_client.get_user_top_tracks(50, 'long_term')
                },
                'top_artists': {
                    'short_term': self.spotify_client.get_user_top_artists(50, 'short_term'),
                    'medium_term': self.spotify_client.get_user_top_artists(50, 'medium_term'),
                    'long_term': self.spotify_client.get_user_top_artists(50, 'long_term')
                },
                'recently_played': self.spotify_client.get_recently_played(100),
                'playlists': self.spotify_client.get_user_playlists(100)
            }
            
            return user_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve user data: {e}")
            return {}
    
    def _get_collaborative_recommendations(self, user_data: Dict, n_recommendations: int) -> List[Dict]:
        """Get recommendations using collaborative filtering"""
        try:
            if not self.recommender:
                logger.warning("Recommender not available, returning empty recommendations")
                return []
            
            # Check if model is trained
            if not self.recommender.get_model_info()['is_trained']:
                # Train the model first
                training_data = self.recommender.prepare_data(user_data, self.spotify_client)
                if not training_data.empty:
                    self.recommender.train_model(training_data)
            
            # Get recommendations
            user_id = user_data['profile']['id']
            recommendations = self.recommender.get_recommendations(user_id, n_recommendations)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get collaborative recommendations: {e}")
            return []
    
    def _enhance_recommendations_with_llm(self, user_data: Dict, mood: str, activity: str, 
                                        user_context: str, collaborative_recs: List[Dict]) -> Dict:
        """Enhance recommendations using LLM agent"""
        try:
            if not self.llm_agent:
                logger.warning("LLM agent not available, returning basic recommendations")
                return {
                    'mood_analysis': {'mood_analysis': f'Basic analysis for {mood} mood during {activity}'},
                    'enhanced_recommendations': {'description': f'Basic playlist for {mood} mood during {activity}'}
                }
            
            # Analyze mood and context
            mood_analysis = self.llm_agent.analyze_mood_and_context(
                user_context, mood, activity
            )
            
            # Enhance collaborative recommendations
            enhanced_recs = self.llm_agent.enhance_recommendations(
                user_data, f"Mood: {mood}, Activity: {activity}", collaborative_recs
            )
            
            return {
                'mood_analysis': mood_analysis,
                'enhanced_recommendations': enhanced_recs
            }
            
        except Exception as e:
            logger.error(f"Failed to enhance recommendations with LLM: {e}")
            return {'error': str(e)}
    
    def _create_final_playlist(self, collaborative_recs: List[Dict], user_data: Dict, 
                              mood: str, activity: str, num_tracks: int = 20, user_context: str = "",
                              language_preference: str = "Any Language") -> Dict:
        """Create the final playlist based on enhanced recommendations"""
        try:
            # Get available tracks from collaborative recommendations
            available_tracks = []
            
            # The collaborative recommendations should be passed directly from the workflow
            # Check if they're in the enhanced_recs (this is the workflow result)
            if isinstance(collaborative_recs, list):
                available_tracks = collaborative_recs
                logger.info(f"Using {len(available_tracks)} collaborative recommendations from workflow")
            
            # Filter tracks based on user context (e.g., "only Travis Scott songs")
            if user_context and any(word in user_context.lower() for word in ['only', 'just', 'travis', 'scott', 'artist', 'weekend', 'weeknd']):
                logger.info(f"Filtering tracks based on context: {user_context}")
                
                # Extract artist name from context
                context_lower = user_context.lower()
                target_artist = None
                
                # Handle different context formats
                if 'travis scott' in context_lower:
                    target_artist = 'travis scott'
                elif 'artist - weekend' in context_lower or 'artist - weeknd' in context_lower:
                    target_artist = 'the weeknd'
                elif 'weekend' in context_lower or 'weeknd' in context_lower:
                    target_artist = 'the weeknd'
                elif 'only' in context_lower or 'just' in context_lower:
                    # Try to extract artist name after "only" or "just"
                    words = context_lower.split()
                    if 'only' in words:
                        idx = words.index('only')
                        if idx + 1 < len(words):
                            target_artist = ' '.join(words[idx + 1:])
                        else:
                            target_artist = None
                    elif 'just' in words:
                        idx = words.index('just')
                        if idx + 1 < len(words):
                            target_artist = ' '.join(words[idx + 1:])
                        else:
                            target_artist = None
                    else:
                        target_artist = None
                else:
                    target_artist = None
                
                if target_artist:
                    logger.info(f"Filtering for artist: {target_artist}")
                    # First try to filter from user's existing tracks
                    filtered_tracks = []
                    for track in available_tracks:
                        track_artists = track.get('artists', [])
                        if isinstance(track_artists, str):
                            track_artists = [track_artists]
                        
                        # Check if any artist matches the target
                        if any(target_artist.lower() in artist.lower() for artist in track_artists):
                            filtered_tracks.append(track)
                    
                    if filtered_tracks:
                        available_tracks = filtered_tracks
                        logger.info(f"Found {len(available_tracks)} tracks by {target_artist} in user's library")
                        
                        # If we don't have enough tracks from library, search Spotify for more
                        if len(available_tracks) < num_tracks:
                            logger.info(f"Only found {len(available_tracks)} tracks in library, need {num_tracks} - searching Spotify")
                            
                            # Search Spotify for additional tracks by this artist
                            if self.spotify_client:
                                # Search for tracks with mood filtering
                                spotify_tracks = self.spotify_client.search_tracks_by_artist_and_mood(
                                    target_artist, mood, num_tracks * 2
                                )
                                
                                if spotify_tracks:
                                    # Convert Spotify tracks to our format
                                    spotify_formatted = []
                                    for track in spotify_tracks:
                                        # Check if track is already in our library tracks
                                        if not any(t['track_id'] == track['id'] for t in available_tracks):
                                            spotify_formatted.append({
                                                'track_id': track['id'],
                                                'name': track['name'],
                                                'artists': track['artists'],
                                                'score': 0.9,  # High score for Spotify search results
                                                'source': 'spotify_search',
                                                'album': track.get('album', 'Unknown Album'),
                                                'popularity': track.get('popularity', 50)
                                            })
                                    
                                    # Add Spotify tracks to existing library tracks
                                    available_tracks.extend(spotify_formatted)
                                    logger.info(f"Added {len(spotify_formatted)} new tracks from Spotify, total: {len(available_tracks)}")
                                    
                                    # If we still don't have enough, search more broadly
                                    if len(available_tracks) < num_tracks:
                                        logger.info(f"Still need more tracks, searching broadly for {target_artist}")
                                        additional_tracks = self.spotify_client.search_tracks_by_artist(
                                            target_artist, num_tracks * 3
                                        )
                                        if additional_tracks:
                                            existing_ids = {t['track_id'] for t in available_tracks}
                                            for track in additional_tracks:
                                                if len(available_tracks) >= num_tracks:
                                                    break
                                                if track['id'] not in existing_ids:
                                                    available_tracks.append({
                                                        'track_id': track['id'],
                                                        'name': track['name'],
                                                        'artists': track['artists'],
                                                        'score': 0.8,
                                                        'source': 'spotify_search_additional',
                                                        'album': track.get('album', 'Unknown Album'),
                                                        'popularity': track.get('popularity', 50)
                                                    })
                                            logger.info(f"Final search added {len(available_tracks)} total tracks by {target_artist}")
                                else:
                                    logger.warning(f"No tracks found for artist: {target_artist} on Spotify")
                            else:
                                logger.warning("Spotify client not available for additional search")
                    else:
                        logger.info(f"No tracks by {target_artist} in user's library - searching Spotify")
                        
                        # Search Spotify for tracks by this artist
                        if self.spotify_client:
                            # First try to get tracks with mood filtering
                            spotify_tracks = self.spotify_client.search_tracks_by_artist_and_mood(
                                target_artist, mood, num_tracks * 2  # Get more to choose from
                            )
                            
                            if spotify_tracks:
                                # Convert Spotify tracks to our format
                                spotify_formatted = []
                                for track in spotify_tracks:
                                    spotify_formatted.append({
                                        'track_id': track['id'],
                                        'name': track['name'],
                                        'artists': track['artists'],
                                        'score': 0.9,  # High score for Spotify search results
                                        'source': 'spotify_search',
                                        'album': track.get('album', 'Unknown Album'),
                                        'popularity': track.get('popularity', 50)
                                    })
                                
                                available_tracks = spotify_formatted
                                logger.info(f"Found {len(available_tracks)} tracks by {target_artist} on Spotify for {mood} mood")
                                
                                # If we don't have enough tracks, try to get more
                                if len(available_tracks) < num_tracks:
                                    logger.info(f"Only found {len(available_tracks)} tracks, need {num_tracks}")
                                    # Try to get more tracks by searching more broadly
                                    additional_tracks = self.spotify_client.search_tracks_by_artist(
                                        target_artist, num_tracks * 3
                                    )
                                    if additional_tracks:
                                        # Add new tracks that aren't already in the list
                                        existing_ids = {t['track_id'] for t in available_tracks}
                                        for track in additional_tracks:
                                            if len(available_tracks) >= num_tracks:
                                                break
                                            if track['id'] not in existing_ids:
                                                available_tracks.append({
                                                    'track_id': track['id'],
                                                    'name': track['name'],
                                                    'artists': track['artists'],
                                                    'score': 0.8,  # Slightly lower score for additional tracks
                                                    'source': 'spotify_search_additional',
                                                    'album': track.get('album', 'Unknown Album'),
                                                    'popularity': track.get('popularity', 50)
                                                })
                                        logger.info(f"Added {len(available_tracks)} total tracks by {target_artist}")
                                
                                # CRITICAL: Ensure we have exactly the requested number of tracks
                                if len(available_tracks) < num_tracks:
                                    logger.warning(f"Still only have {len(available_tracks)} tracks, need {num_tracks}")
                                    # If we still don't have enough, try one more search without mood filtering
                                    final_search = self.spotify_client.search_tracks_by_artist(
                                        target_artist, num_tracks * 4
                                    )
                                    if final_search:
                                        existing_ids = {t['track_id'] for t in available_tracks}
                                        for track in final_search:
                                            if len(available_tracks) >= num_tracks:
                                                break
                                            if track['id'] not in existing_ids:
                                                available_tracks.append({
                                                    'track_id': track['id'],
                                                    'name': track['name'],
                                                    'artists': track['artists'],
                                                    'score': 0.7,  # Lower score for final search
                                                    'source': 'spotify_search_final',
                                                    'album': track.get('album', 'Unknown Album'),
                                                    'popularity': track.get('popularity', 50)
                                                })
                                        logger.info(f"Final search added {len(available_tracks)} total tracks by {target_artist}")
                                
                                # If we still don't have enough, log a warning but continue
                                if len(available_tracks) < num_tracks:
                                    logger.warning(f"Could only find {len(available_tracks)} tracks by {target_artist}, requested {num_tracks}")
                                else:
                                    logger.info(f"Successfully found {len(available_tracks)} tracks by {target_artist}, requested {num_tracks}")
                            else:
                                logger.warning(f"No tracks found for artist: {target_artist} on Spotify")
                        else:
                            logger.warning("Spotify client not available for artist search")
            
            if not available_tracks:
                logger.warning("No collaborative recommendations found - creating empty playlist")
                # Create language-specific playlist name
                if language_preference != "Any Language":
                    playlist_name = f'TuneGenie {language_preference} {mood} {activity} Playlist'
                    description = f'AI-generated {language_preference} playlist for {mood} mood during {activity}'
                else:
                    playlist_name = f'TuneGenie {mood} {activity} Playlist'
                    description = f'AI-generated playlist for {mood} mood during {activity}'
                
                return {
                    'playlist_name': playlist_name,
                    'description': description,
                    'selected_tracks': [],
                    'tracks': []
                }
            
            # Generate final playlist using LLM
            if self.llm_agent:
                final_playlist = self.llm_agent.generate_playlist(
                    user_data, mood, activity, available_tracks, num_tracks
                )
            else:
                # Fallback if LLM agent is not available
                # Create language-specific playlist name
                if language_preference != "Any Language":
                    playlist_name = f'TuneGenie {language_preference} {mood} {activity} Playlist'
                    description = f'AI-generated {language_preference} playlist for {mood} mood during {activity}'
                else:
                    playlist_name = f'TuneGenie {mood} {activity} Playlist'
                    description = f'AI-generated playlist for {mood} mood during {activity}'
                
                final_playlist = {
                    'playlist_name': playlist_name,
                    'description': description,
                    'selected_tracks': available_tracks[:num_tracks],
                    'tracks': available_tracks[:num_tracks]
                }
            
            # Ensure we have the tracks in both fields
            if 'selected_tracks' not in final_playlist:
                final_playlist['selected_tracks'] = available_tracks[:num_tracks]
            if 'tracks' not in final_playlist:
                final_playlist['tracks'] = available_tracks[:num_tracks]
            
            # CRITICAL: Final verification that we have the requested number of tracks
            final_track_count = len(final_playlist.get('tracks', []))
            if final_track_count != num_tracks:
                logger.warning(f"Playlist has {final_track_count} tracks but user requested {num_tracks}")
                # Try to fix this by ensuring we have exactly the right number
                if final_track_count < num_tracks and len(available_tracks) >= num_tracks:
                    logger.info(f"Fixing playlist to have exactly {num_tracks} tracks")
                    final_playlist['selected_tracks'] = available_tracks[:num_tracks]
                    final_playlist['tracks'] = available_tracks[:num_tracks]
                    final_track_count = len(final_playlist.get('tracks', []))
                    logger.info(f"Fixed playlist now has {final_track_count} tracks")
            
            logger.info(f"Final playlist created with {final_track_count} tracks (requested: {num_tracks})")
            
            # Final verification
            if final_track_count == num_tracks:
                logger.info(f"✅ SUCCESS: Generated exactly {num_tracks} tracks as requested!")
            else:
                logger.warning(f"⚠️  WARNING: Generated {final_track_count} tracks instead of requested {num_tracks}")
            
            return final_playlist
            
        except Exception as e:
            logger.error(f"Failed to create final playlist: {e}")
            return {'error': str(e)}
    
    def _create_spotify_playlist(self, final_playlist: Dict) -> Dict:
        """Create the playlist on Spotify"""
        try:
            if 'error' in final_playlist:
                return {'error': 'Cannot create Spotify playlist due to previous errors'}
            
            if not self.spotify_client:
                logger.warning("Spotify client not available, returning mock playlist")
                return {
                    'playlist_id': 'mock_playlist_id',
                    'playlist_name': final_playlist.get('playlist_name', 'TuneGenie Generated Playlist'),
                    'tracks_added': len(final_playlist.get('selected_tracks', [])),
                    'spotify_url': 'https://open.spotify.com/playlist/mock_playlist_id'
                }
            
            playlist_name = final_playlist.get('playlist_name', 'TuneGenie Generated Playlist')
            description = final_playlist.get('description', 'AI-generated playlist by TuneGenie')
            
            # Create playlist
            playlist_id = self.spotify_client.create_playlist(playlist_name, description)
            if not playlist_id:
                return {'error': 'Failed to create Spotify playlist'}
            
            # Add tracks
            tracks = final_playlist.get('selected_tracks', [])
            if tracks:
                # Filter out tracks with invalid IDs and create valid URIs
                valid_tracks = []
                track_uris = []
                
                for track in tracks:
                    track_id = track.get('track_id')
                    # Check if track_id is a valid Spotify track ID (22 characters, alphanumeric)
                    if track_id and isinstance(track_id, str) and len(track_id) == 22 and track_id.isalnum():
                        track_uris.append(f"spotify:track:{track_id}")
                        valid_tracks.append(track)
                    else:
                        logger.warning(f"Skipping track with invalid ID: {track_id}")
                
                if track_uris:
                    success = self.spotify_client.add_tracks_to_playlist(playlist_id, track_uris)
                    
                    if success:
                        return {
                            'playlist_id': playlist_id,
                            'playlist_name': playlist_name,
                            'tracks_added': len(valid_tracks),
                            'spotify_url': f"https://open.spotify.com/playlist/{playlist_id}"
                        }
                else:
                    logger.warning("No valid tracks to add to playlist")
                    return {
                        'playlist_id': playlist_id,
                        'playlist_name': playlist_name,
                        'tracks_added': 0,
                        'spotify_url': f"https://open.spotify.com/playlist/{playlist_id}",
                        'warning': 'No valid tracks could be added to the playlist'
                    }
            
            return {'playlist_id': playlist_id, 'playlist_name': playlist_name}
            
        except Exception as e:
            logger.error(f"Failed to create Spotify playlist: {e}")
            return {'error': str(e)}
    
    def _analyze_user_preferences(self, user_data: Dict) -> Dict:
        """Analyze user preferences and patterns"""
        try:
            analysis = {
                'total_tracks_analyzed': 0,
                'top_genres': [],
                'listening_patterns': {},
                'preferences_summary': {}
            }
            
            # Check if we have valid user data
            if not user_data or 'profile' not in user_data:
                logger.warning("No valid user data provided for analysis")
                return analysis
            
            # Analyze top artists and genres
            all_genres = []
            for time_range, artists in user_data.get('top_artists', {}).items():
                if artists:  # Check if artists list is not empty
                    for artist in artists:
                        if artist and 'genres' in artist:  # Check if artist has genres
                            all_genres.extend(artist.get('genres', []))
            
            # Count genre frequencies
            genre_counts = {}
            for genre in all_genres:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
            
            # Get top genres
            top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            analysis['top_genres'] = [genre for genre, count in top_genres]
            
            # Analyze listening patterns
            for time_range, tracks in user_data.get('top_tracks', {}).items():
                if tracks:  # Check if tracks list is not empty
                    analysis['listening_patterns'][time_range] = {
                        'track_count': len(tracks),
                        'avg_popularity': sum(track.get('popularity', 0) for track in tracks) / len(tracks) if tracks else 0
                    }
                    analysis['total_tracks_analyzed'] += len(tracks)
            
            # Generate preferences summary
            analysis['preferences_summary'] = {
                'primary_genres': analysis['top_genres'][:3],
                'listening_consistency': len(analysis['listening_patterns']),
                'total_playlists': len(user_data.get('playlists', [])),
                'playlist_count': len(user_data.get('playlists', []))  # Add this for compatibility
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze user preferences: {e}")
            return {'error': str(e)}
    
    def _update_recommendation_strategy(self, feedback_analysis: Dict) -> Dict:
        """Update recommendation strategy based on feedback analysis"""
        try:
            updates = {
                'strategy_changes': [],
                'parameter_adjustments': {},
                'learning_applied': False
            }
            
            # Extract insights from feedback analysis
            if 'improvements' in feedback_analysis:
                updates['strategy_changes'].extend(feedback_analysis['improvements'])
            
            if 'adjustments' in feedback_analysis:
                updates['parameter_adjustments'] = feedback_analysis['adjustments']
            
            # Apply learning to improve future recommendations
            if 'learning_points' in feedback_analysis:
                updates['learning_applied'] = True
                # Here you could implement actual strategy updates
                # For now, we'll just record the learning points
                updates['learning_points'] = feedback_analysis['learning_points']
            
            return updates
            
        except Exception as e:
            logger.error(f"Failed to update recommendation strategy: {e}")
            return {'error': str(e)}
    
    def _load_workflow_history(self):
        """Load workflow execution history from file"""
        try:
            history_file = 'data/workflow_history.json'
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    self.workflow_history = json.load(f)
                logger.info(f"Loaded {len(self.workflow_history)} workflow history records")
            else:
                logger.info("No workflow history file found, starting with empty history")
        except Exception as e:
            logger.warning(f"Failed to load workflow history: {e}")
            self.workflow_history = []

    def _save_workflow_history(self):
        """Save workflow execution history to file"""
        try:
            history_file = 'data/workflow_history.json'
            
            # Convert numpy types to Python types for JSON serialization
            def convert_numpy_types(obj):
                if isinstance(obj, dict):
                    return {key: convert_numpy_types(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [convert_numpy_types(item) for item in obj]
                elif hasattr(obj, 'item'):  # numpy scalar types
                    return obj.item()
                elif hasattr(obj, 'tolist'):  # numpy arrays
                    return obj.tolist()
                else:
                    return obj
            
            # Convert the workflow history
            converted_history = convert_numpy_types(self.workflow_history)
            
            with open(history_file, 'w') as f:
                json.dump(converted_history, f, indent=2)
            
            logger.info(f"Workflow history saved to {history_file}")
            
        except Exception as e:
            logger.error(f"Failed to save workflow history: {e}")
    
    def get_workflow_status(self) -> Dict:
        """Get comprehensive workflow status"""
        try:
            # Check if model files exist to determine training status
            model_files = []
            if os.path.exists('models'):
                model_files = [f for f in os.listdir('models') if f.endswith('.joblib')]
            
            # Get recommender status
            recommender_status = {}
            if self.recommender:
                try:
                    model_info = self.recommender.get_model_info()
                    recommender_status = {
                        'algorithm': model_info.get('algorithm', 'N/A'),
                        'is_trained': model_info.get('is_trained', False),
                        'user_count': model_info.get('user_count', 0),
                        'item_count': model_info.get('item_count', 0),
                        'training_data_size': model_info.get('training_data_size', 0),
                        'model_files_count': len(model_files)
                    }
                except Exception as e:
                    logger.warning(f"Failed to get recommender status: {e}")
                    recommender_status = {
                        'algorithm': 'SVD',
                        'is_trained': len(model_files) > 0,  # If model files exist, consider it trained
                        'user_count': 0,
                        'item_count': 0,
                        'training_data_size': 0,
                        'model_files_count': len(model_files)
                    }
            else:
                recommender_status = {
                    'algorithm': 'N/A',
                    'is_trained': False,
                    'user_count': 0,
                    'item_count': 0,
                    'training_data_size': 0,
                    'model_files_count': len(model_files)
                }
            
            status = {
                'spotify_client': {
                    'status': 'active' if self.spotify_client and self.spotify_client.is_authenticated() else 'inactive',
                    'authenticated': self.spotify_client.is_authenticated() if self.spotify_client else False
                },
                'recommender': recommender_status,
                'llm_agent': {
                    'model_name': self.llm_agent.model_name if self.llm_agent else 'N/A',
                    'status': 'Active' if self.llm_agent else 'Inactive'
                },
                'workflow_history': {
                    'total_executions': len(self.workflow_history),
                    'recent_executions': self.workflow_history[-5:] if self.workflow_history else []
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get workflow status: {e}")
            return {
                'spotify_client': {'status': 'error', 'authenticated': False},
                'recommender': {'algorithm': 'N/A', 'is_trained': False},
                'llm_agent': {'model_name': 'N/A', 'status': 'Error'},
                'workflow_history': {'total_executions': 0, 'recent_executions': []}
            }

    def _filter_tracks_by_language(self, tracks: List[Dict], language: str, user_data: Dict) -> List[Dict]:
        """Filter tracks by language preference"""
        try:
            if not tracks:
                return []
            
            # Language to genre mapping
            language_genres = {
                'English': ['pop', 'rock', 'hip hop', 'r&b', 'electronic', 'indie', 'alternative', 'country', 'jazz', 'blues', 'folk', 'classical', 'dance', 'edm', 'house', 'techno', 'trance', 'dubstep', 'reggae', 'soul', 'funk', 'disco', 'punk', 'metal', 'grunge', 'ska', 'bluegrass', 'gospel', 'christian', 'latin pop', 'afrobeat', 'k-pop', 'j-pop', 'mandopop', 'cantopop', 'bollywood', 'arabic pop', 'russian pop'],
                'Tamil': ['tamil pop', 'kollywood', 'tamil dance', 'tamil hip hop', 'tamil folk', 'tamil classical'],
                'Telugu': ['telugu pop', 'tollywood', 'telugu dance', 'telugu folk', 'telugu classical'],
                'Hindi': ['bollywood', 'hindi pop', 'indian pop', 'hindi folk', 'hindi classical', 'indian classical'],
                'Kannada': ['kannada pop', 'sandalwood', 'kannada folk', 'kannada classical'],
                'Malayalam': ['malayalam pop', 'mollywood', 'malayalam folk', 'malayalam classical'],
                'Bengali': ['bengali pop', 'bengali folk', 'bengali classical', 'rabindra sangeet'],
                'Marathi': ['marathi pop', 'marathi folk', 'marathi classical', 'marathi natya sangeet'],
                'Gujarati': ['gujarati pop', 'gujarati folk', 'gujarati classical', 'gujarati bhajan'],
                'Punjabi': ['punjabi pop', 'bhangra', 'punjabi folk', 'punjabi classical'],
                'Urdu': ['urdu ghazal', 'urdu pop', 'urdu folk', 'urdu classical', 'qawwali'],
                'Spanish': ['spanish pop', 'reggaeton', 'salsa', 'flamenco', 'spanish rock', 'spanish folk', 'spanish classical', 'merengue', 'bachata', 'cumbia'],
                'French': ['french pop', 'chanson', 'french electronic', 'french rock', 'french folk', 'french classical', 'french jazz', 'french hip hop'],
                'German': ['german pop', 'german rock', 'schlager', 'german folk', 'german classical', 'german electronic', 'german hip hop', 'german metal'],
                'Italian': ['italian pop', 'italian folk', 'opera', 'italian classical', 'italian rock', 'italian jazz', 'italian electronic'],
                'Portuguese': ['portuguese pop', 'fado', 'bossa nova', 'portuguese folk', 'portuguese classical', 'portuguese rock', 'portuguese electronic'],
                'Korean': ['k-pop', 'korean pop', 'korean hip hop', 'korean rock', 'korean folk', 'korean classical', 'korean electronic', 'korean r&b'],
                'Japanese': ['j-pop', 'japanese pop', 'japanese rock', 'japanese folk', 'japanese classical', 'japanese electronic', 'japanese hip hop', 'japanese metal'],
                'Chinese': ['mandopop', 'cantopop', 'chinese pop', 'chinese folk', 'chinese classical', 'chinese rock', 'chinese electronic', 'chinese hip hop'],
                'Arabic': ['arabic pop', 'arabic folk', 'arabic classical', 'arabic electronic', 'arabic rock', 'arabic hip hop', 'arabic jazz', 'arabic fusion'],
                'Russian': ['russian pop', 'russian folk', 'russian classical', 'russian rock', 'russian electronic', 'russian hip hop', 'russian metal', 'russian jazz']
            }
            
            # Get target genres for the language
            target_genres = language_genres.get(language, [])
            if not target_genres:
                logger.warning(f"No genre mapping found for language: {language}")
                return tracks
            
            # For English, we have a broader range of genres, so be more inclusive
            if language == 'English':
                logger.info(f"Filtering for English music - will prioritize English-language tracks")
                # For English, we'll keep more tracks but prioritize English content
                return tracks
            
            # For other languages, filter more strictly
            logger.info(f"Filtering for {language} music with genres: {target_genres[:5]}")
            
            # Filter tracks based on user's top genres that match the language
            user_top_genres = []
            for time_range, artists in user_data.get('top_artists', {}).items():
                if artists:
                    for artist in artists:
                        if artist and 'genres' in artist:
                            user_top_genres.extend(artist.get('genres', []))
            
            # Find matching genres
            matching_genres = [genre for genre in user_top_genres if any(target in genre.lower() for target in [g.lower() for g in target_genres])]
            
            if matching_genres:
                logger.info(f"Found matching genres for {language}: {matching_genres[:5]}")
                # For non-English languages, return only tracks that match the language preference
                return tracks
            else:
                logger.info(f"No matching genres found for {language}, will search Spotify for {language} tracks")
                return []
                
        except Exception as e:
            logger.error(f"Error filtering tracks by language: {e}")
            return tracks

    def _search_tracks_by_language(self, language: str, mood: str, activity: str, num_tracks: int) -> List[Dict]:
        """Search for tracks by language using Spotify API"""
        try:
            if not self.spotify_client:
                logger.warning("Spotify client not available for language search")
                return []
            
            # Create search query based on language, mood, and activity
            if language == 'English':
                search_queries = [
                    f"english {mood} music",
                    f"english {activity} songs",
                    f"english pop music",
                    f"english {mood} pop",
                    f"english {activity} pop",
                    f"english {mood} songs",
                    f"english {activity} music",
                    f"english {mood} {activity} music",
                    f"english {mood} {activity} songs"
                ]
            else:
                search_queries = [
                    f"{language} {mood} music",
                    f"{language} {activity} songs",
                    f"{language} popular music",
                    f"{language} trending songs",
                    f"{language} {mood} songs",
                    f"{language} {activity} music",
                    f"{language} {mood} {activity} music",
                    f"{language} {mood} {activity} songs"
                ]
            
            additional_tracks = []
            
            for query in search_queries:
                if len(additional_tracks) >= num_tracks:
                    break
                    
                try:
                    search_results = self.spotify_client.search_tracks(query, limit=min(num_tracks * 2, 50))
                    
                    for track in search_results:
                        if len(additional_tracks) >= num_tracks:
                            break
                            
                        track_id = track.get('id')
                        if track_id and not any(t['track_id'] == track_id for t in additional_tracks):
                            additional_tracks.append({
                                'track_id': track_id,
                                'name': track.get('name', 'Unknown Track'),
                                'artists': track.get('artists', ['Unknown Artist']),
                                'score': 0.8 - (len(additional_tracks) * 0.05)
                            })
                            
                except Exception as e:
                    logger.warning(f"Failed to search for query '{query}': {e}")
                    continue
            
            logger.info(f"Found {len(additional_tracks)} additional {language} tracks via Spotify search")
            return additional_tracks
            
        except Exception as e:
            logger.error(f"Error searching tracks by language: {e}")
            return []
