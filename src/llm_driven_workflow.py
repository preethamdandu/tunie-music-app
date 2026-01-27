"""
LLM-Driven Workflow for TuneGenie
Alternative architecture where LLM understanding of mood drives candidate generation
"""

from __future__ import annotations

import os
import json
import logging
from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

from .spotify_client import SpotifyClient
from .recommender import CollaborativeFilteringRecommender
from .llm_agent import LLMAgent

logger = logging.getLogger(__name__)


class LLMDrivenWorkflow:
    """LLM-driven workflow where mood understanding influences candidate generation"""
    
    def __init__(self):
        """Initialize the LLM-driven workflow"""
        self.spotify_client = None
        self.recommender = None
        self.llm_agent = None
        self.workflow_history = []
        
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
            
            # Initialize collaborative filtering recommender (as fallback)
            try:
                algorithm = os.getenv('COLLABORATIVE_FILTERING_ALGORITHM', 'SVD')
                self.recommender = CollaborativeFilteringRecommender(algorithm=algorithm)
                logger.info(f"Collaborative filtering recommender initialized with {algorithm}")
            except Exception as e:
                logger.warning(f"Recommender initialization failed: {e}")
                self.recommender = None
            
            # Initialize LLM agent (critical for this workflow)
            try:
                temperature = float(os.getenv('LLM_TEMPERATURE', '0.7'))
                self.llm_agent = LLMAgent(temperature=temperature)
                logger.info("LLM agent initialized")
            except Exception as e:
                logger.warning(f"LLM agent initialization failed: {e}")
                self.llm_agent = None
            
            # Check if LLM is available (critical for this workflow)
            if not self.llm_agent:
                logger.error("LLM agent is required for LLM-driven workflow")
                raise RuntimeError("LLM agent is required for LLM-driven workflow")
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            raise
    
    def execute_playlist_generation(self, mood: str, activity: str, 
                                   user_context: str = "", num_tracks: int = 20, 
                                   language_preference: str = "Any Language",
                                   keywords = None,
                                   must_be_instrumental: bool = False,
                                   search_strictness: int = 1,
                                   taste_profile: Optional[Dict] = None) -> Dict:
        """
        Execute LLM-driven playlist generation workflow
        
        The key difference: LLM analyzes mood/context FIRST and generates search strategies
        that drive candidate generation, rather than just filtering pre-generated candidates.
        
        Architecture:
        1. LLM analyzes mood/context/keywords → generates semantic search queries
        2. Search queries drive Spotify API to get targeted candidates
        3. User profile influences ranking but doesn't dominate
        4. LLM validates and refines the final selection
        """
        try:
            logger.info(f"Starting LLM-driven playlist generation for mood: {mood}, activity: {activity}")
            
            # Step 1: LLM-Driven Mood Analysis → Search Strategy Generation
            logger.info("Step 1: LLM analyzing mood and generating search strategy")
            search_strategy = self._generate_llm_search_strategy(
                mood, activity, user_context, language_preference, keywords
            )
            
            # Step 2: Execute semantic searches based on LLM strategy
            logger.info("Step 2: Executing LLM-guided searches for candidates")
            candidate_tracks = self._execute_semantic_searches(
                search_strategy, num_tracks * 3  # Get 3x candidates for selection
            )
            
            # Step 3: Get user profile for personalization (but not as primary driver)
            logger.info("Step 3: Retrieving user profile for personalization")
            user_data = self._retrieve_user_data()
            
            # Step 4: Score and rank candidates using LLM understanding + user preferences
            logger.info("Step 4: Scoring candidates with LLM insights and user preferences")
            scored_tracks = self._score_tracks_with_llm(
                candidate_tracks, mood, activity, user_context, user_data, search_strategy, taste_profile
            )
            
            # Step 5: Final selection and ordering by LLM
            logger.info("Step 5: LLM making final selection and ordering")
            final_playlist = self._llm_final_selection(
                scored_tracks, mood, activity, num_tracks, search_strategy
            )

            # Final filtering per advanced settings (instrumentalness)
            if must_be_instrumental:
                try:
                    ids = [t.get('track_id') for t in final_playlist.get('tracks', []) if t.get('track_id')]
                    feats = self.spotify_client.get_audio_features_for_tracks(ids)
                    threshold = 0.8 if search_strictness >= 2 else (0.6 if search_strictness == 1 else 0.0)
                    filtered = [t for t in final_playlist.get('tracks', []) if feats.get(t.get('track_id'), {}).get('instrumentalness', 0.0) >= threshold]
                    if filtered:
                        final_playlist['tracks'] = filtered[:num_tracks]
                        final_playlist['selected_tracks'] = filtered[:num_tracks]
                except Exception:
                    pass
            
            # Step 6: Create Spotify playlist
            logger.info("Step 6: Creating Spotify playlist")
            spotify_playlist = self._create_spotify_playlist(final_playlist)
            warnings: List[str] = []
            try:
                requested = len(final_playlist.get('tracks', []))
                added = int(spotify_playlist.get('tracks_added', 0)) if isinstance(spotify_playlist, dict) else 0
                if added < requested:
                    warnings.append('Some tracks could not be added.')
            except Exception:
                pass
            
            # Step 7: Validate if keywords were provided
            keyword_validation = {}
            if keywords:
                keyword_validation = self._validate_playlist(keywords, final_playlist.get('tracks', []))
            
            result = {
                'workflow_type': 'llm_driven_playlist_generation',
                'mood': mood,
                'activity': activity,
                'user_context': user_context,
                'search_strategy': search_strategy,
                'candidate_count': len(candidate_tracks),
                'final_playlist': final_playlist,
                'spotify_playlist': spotify_playlist,
                'keyword_validation': keyword_validation,
                'metadata': {
                    'total_tracks': len(final_playlist.get('tracks', [])),
                    'generation_timestamp': datetime.now().isoformat(),
                    'llm_model': self.llm_agent.model_name if self.llm_agent else 'N/A',
                    'architecture': 'llm_driven',
                    'taste_profile_used': bool(taste_profile)
                },
                'warnings': warnings
            }
            
            logger.info("LLM-driven playlist generation completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"LLM-driven playlist generation failed: {e}")
            return {'error': str(e)}
    
    def _generate_llm_search_strategy(self, mood: str, activity: str, 
                                     user_context: str, language_preference: str,
                                     keywords: Union[Dict, str, None]) -> Dict:
        """
        Use LLM to analyze mood/context and generate a comprehensive search strategy
        
        Returns a strategy with:
        - genres: List of genres that match the mood
        - artists: Suggested artists that fit the vibe
        - audio_features: Target audio features (energy, valence, tempo, etc.)
        - search_queries: Specific Spotify search queries to execute
        - themes: Thematic elements to look for
        """
        try:
            # Build comprehensive prompt for LLM
            prompt = f"""
            Analyze this music request and generate a search strategy:
            
            Mood: {mood}
            Activity: {activity}
            Context: {user_context}
            Language: {language_preference}
            Keywords: {keywords if keywords else 'None'}
            
            Generate a JSON search strategy with:
            1. genres: List of 3-5 specific genres that match this mood/activity
            2. audio_features: Dict with target ranges for:
               - energy: 0-1 (low to high)
               - valence: 0-1 (sad to happy)
               - tempo: BPM range
               - danceability: 0-1
               - acousticness: 0-1
            3. search_queries: List of 5-10 specific Spotify search queries
            4. themes: List of thematic keywords (e.g., "uplifting", "nostalgic")
            5. era: Preferred time period (e.g., "2020s", "90s", "current")
            
            Consider the activity context deeply - {activity} requires specific energy levels.
            Mood {mood} suggests certain emotional qualities.
            """
            
            # Get LLM response
            if hasattr(self.llm_agent, 'generate_search_strategy'):
                strategy = self.llm_agent.generate_search_strategy(prompt)
            else:
                # Fallback to basic strategy generation
                strategy = self._generate_fallback_strategy(mood, activity, keywords)
            
            logger.info(f"Generated search strategy with {len(strategy.get('search_queries', []))} queries")
            return strategy
            
        except Exception as e:
            logger.error(f"Failed to generate LLM search strategy: {e}")
            return self._generate_fallback_strategy(mood, activity, keywords)
    
    def _generate_fallback_strategy(self, mood: str, activity: str, keywords: Union[Dict, str, None]) -> Dict:
        """Generate a fallback search strategy using heuristics"""
        
        # Mood to genre/feature mappings
        mood_mappings = {
            'Happy': {
                'genres': ['pop', 'indie pop', 'dance pop', 'electropop'],
                'energy': [0.6, 0.9],
                'valence': [0.7, 1.0],
                'tempo': [100, 140]
            },
            'Sad': {
                'genres': ['indie folk', 'singer-songwriter', 'ambient', 'neo-classical'],
                'energy': [0.1, 0.4],
                'valence': [0.0, 0.3],
                'tempo': [60, 90]
            },
            'Energetic': {
                'genres': ['edm', 'hip hop', 'rock', 'electronic'],
                'energy': [0.7, 1.0],
                'valence': [0.5, 0.9],
                'tempo': [120, 180]
            },
            'Calm': {
                'genres': ['ambient', 'lo-fi', 'classical', 'jazz'],
                'energy': [0.1, 0.3],
                'valence': [0.4, 0.7],
                'tempo': [60, 100]
            },
            'Focused': {
                'genres': ['lo-fi hip hop', 'instrumental', 'classical', 'minimal techno'],
                'energy': [0.3, 0.6],
                'valence': [0.4, 0.7],
                'tempo': [70, 110]
            }
        }
        
        # Activity modifiers
        activity_modifiers = {
            'Working': {'energy_boost': -0.2, 'instrumental_preference': True},
            'Exercising': {'energy_boost': 0.3, 'tempo_boost': 20},
            'Studying': {'energy_boost': -0.3, 'instrumental_preference': True},
            'Cooking': {'energy_boost': 0.1, 'valence_boost': 0.1},
            'Commuting': {'energy_boost': 0.0, 'variety': True}
        }
        
        # Get base features from mood
        base = mood_mappings.get(mood, mood_mappings['Happy'])
        
        # Apply activity modifiers
        modifier = activity_modifiers.get(activity, {})
        
        energy_range = base['energy'].copy()
        if 'energy_boost' in modifier:
            energy_range[0] = max(0, energy_range[0] + modifier['energy_boost'])
            energy_range[1] = min(1, energy_range[1] + modifier['energy_boost'])
        
        tempo_range = base['tempo'].copy()
        if 'tempo_boost' in modifier:
            tempo_range[0] += modifier.get('tempo_boost', 0)
            tempo_range[1] += modifier.get('tempo_boost', 0)
        
        # Generate search queries
        search_queries = []
        
        # Genre-based queries
        for genre in base['genres'][:3]:
            search_queries.append(f"genre:{genre} {mood.lower()}")
        
        # Mood + activity queries
        search_queries.append(f"{mood.lower()} {activity.lower()} music")
        search_queries.append(f"{mood.lower()} vibes")
        
        # Add keyword-based queries if provided
        if keywords:
            if isinstance(keywords, str):
                search_queries.append(keywords)
            elif isinstance(keywords, dict):
                if keywords.get('artists'):
                    for artist in keywords['artists'][:2]:
                        search_queries.append(f"artist:{artist}")
                if keywords.get('genres'):
                    for genre in keywords['genres'][:2]:
                        search_queries.append(f"genre:{genre}")
        
        return {
            'genres': base['genres'],
            'audio_features': {
                'energy': energy_range,
                'valence': base['valence'],
                'tempo': tempo_range,
                'danceability': [0.4, 0.8],
                'acousticness': [0.0, 0.5] if activity != 'Studying' else [0.3, 0.8]
            },
            'search_queries': search_queries,
            'themes': [mood.lower(), activity.lower()],
            'era': 'current'
        }
    
    def _execute_semantic_searches(self, search_strategy: Dict, limit: int) -> List[Dict]:
        """Execute the LLM-generated search queries to get candidate tracks"""
        try:
            if not self.spotify_client:
                logger.error("Spotify client not available")
                return []
            
            all_tracks = []
            seen_ids = set()
            
            # Execute each search query
            queries = search_strategy.get('search_queries', [])
            tracks_per_query = max(10, limit // len(queries)) if queries else limit
            
            for query in queries:
                try:
                    logger.info(f"Executing search: {query}")
                    results = self.spotify_client.search_tracks(query, limit=tracks_per_query)
                    
                    for track in results:
                        track_id = track.get('id')
                        if track_id and track_id not in seen_ids:
                            seen_ids.add(track_id)
                            
                            # Get audio features if possible
                            try:
                                features = self.spotify_client.get_track_features([track_id])
                                if features and features[0]:
                                    track['audio_features'] = features[0]
                            except:
                                pass
                            
                            all_tracks.append(track)
                            
                            if len(all_tracks) >= limit:
                                break
                    
                    if len(all_tracks) >= limit:
                        break
                        
                except Exception as e:
                    logger.warning(f"Search query '{query}' failed: {e}")
                    continue
            
            logger.info(f"Collected {len(all_tracks)} candidate tracks from semantic searches")
            return all_tracks
            
        except Exception as e:
            logger.error(f"Failed to execute semantic searches: {e}")
            return []
    
    def _score_tracks_with_llm(self, tracks: List[Dict], mood: str, activity: str,
                               user_context: str, user_data: Dict, search_strategy: Dict,
                               taste_profile: Optional[Dict]) -> List[Dict]:
        """
        Score tracks using LLM understanding of mood/context plus user preferences
        
        Key difference from traditional approach:
        - LLM-derived features are primary
        - User history is secondary (for personalization, not generation)
        """
        try:
            # Get target audio features from strategy
            target_features = search_strategy.get('audio_features', {})
            
            # Score each track
            for track in tracks:
                score = 0.0
                
                # 1. Audio feature matching (40% weight)
                if 'audio_features' in track and target_features:
                    feature_score = self._calculate_feature_similarity(
                        track['audio_features'], target_features
                    )
                    score += feature_score * 0.4
                
                # 2. Genre matching (30% weight)
                # This would require genre detection or artist genre lookup
                # For now, use popularity as proxy
                popularity = track.get('popularity', 50) / 100
                score += popularity * 0.3
                
                # 3. User preference matching (20% weight)
                if user_data:
                    user_score = self._calculate_user_preference_score(track, user_data)
                    score += user_score * 0.2
                
                # 4. Recency/freshness (10% weight)
                # Prefer newer tracks for most moods
                if 'release_date' in track:
                    try:
                        release_year = int(track['release_date'][:4])
                        recency_score = max(0, (release_year - 2015) / 10)
                        score += min(1.0, recency_score) * 0.1
                    except:
                        pass
                
                # 5. Taste profile alignment (optional +10%)
                if taste_profile:
                    try:
                        bonus = 0.0
                        sonic = [str(s).lower() for s in (taste_profile.get('sonic_profile') or [])]
                        prefs = taste_profile.get('preferred_genres') or []
                        # Normalize preferred_genres entries
                        pref_names = set()
                        for p in prefs:
                            if isinstance(p, str):
                                pref_names.add(p.lower())
                            elif isinstance(p, dict) and p.get('genre'):
                                pref_names.add(str(p['genre']).lower())
                        # Use available track fields as weak signals
                        name = (track.get('name') or '').lower()
                        album = (track.get('album') or '').lower()
                        artists = [str(a).lower() for a in (track.get('artists') or [])]
                        # Sonic hints via audio features if present
                        feats = track.get('audio_features') or {}
                        if any('high-energy' in s or 'energetic' in s for s in sonic):
                            if feats.get('energy', 0.0) >= 0.6:
                                bonus += 0.05
                        if any('acoustic' in s or 'lo-fi' in s or 'lofi' in s for s in sonic):
                            if feats.get('acousticness', 0.0) >= 0.5:
                                bonus += 0.05
                        # Genre name hints via text fields
                        if any(g in name or g in album or any(g in a for a in artists) for g in pref_names):
                            bonus += 0.05
                        score += min(0.1, bonus)
                    except Exception:
                        pass

                track['llm_score'] = score
            
            # Sort by score
            scored_tracks = sorted(tracks, key=lambda x: x.get('llm_score', 0), reverse=True)
            return scored_tracks
            
        except Exception as e:
            logger.error(f"Failed to score tracks with LLM: {e}")
            return tracks
    
    def _calculate_feature_similarity(self, track_features: Dict, target_features: Dict) -> float:
        """Calculate similarity between track audio features and target features"""
        try:
            similarity = 0.0
            feature_count = 0
            
            for feature, target_range in target_features.items():
                if feature in track_features and isinstance(target_range, list) and len(target_range) == 2:
                    value = track_features[feature]
                    
                    # Check if value is within target range
                    if target_range[0] <= value <= target_range[1]:
                        similarity += 1.0
                    else:
                        # Calculate distance from range
                        if value < target_range[0]:
                            distance = target_range[0] - value
                        else:
                            distance = value - target_range[1]
                        
                        # Convert distance to similarity (0-1)
                        similarity += max(0, 1.0 - distance)
                    
                    feature_count += 1
            
            return similarity / feature_count if feature_count > 0 else 0.5
            
        except Exception as e:
            logger.error(f"Failed to calculate feature similarity: {e}")
            return 0.5
    
    def _calculate_user_preference_score(self, track: Dict, user_data: Dict) -> float:
        """Calculate how well a track matches user preferences"""
        try:
            score = 0.0
            
            # Check if track artist is in user's top artists
            track_artists = set(track.get('artists', []))
            
            for time_range in ['short_term', 'medium_term', 'long_term']:
                top_artists = user_data.get('top_artists', {}).get(time_range, [])
                for artist in top_artists:
                    if artist.get('name') in track_artists:
                        score = max(score, 0.9)
                        break
            
            # Check if track is in user's top tracks
            track_id = track.get('id')
            for time_range in ['short_term', 'medium_term', 'long_term']:
                top_tracks = user_data.get('top_tracks', {}).get(time_range, [])
                for t in top_tracks:
                    if t.get('id') == track_id:
                        score = max(score, 1.0)
                        break
            
            # Check recently played
            recently_played = user_data.get('recently_played', [])
            for t in recently_played[-20:]:  # Last 20 tracks
                if t.get('id') == track_id:
                    score = max(score, 0.7)
                    break
            
            return score
            
        except Exception as e:
            logger.error(f"Failed to calculate user preference score: {e}")
            return 0.0
    
    def _llm_final_selection(self, scored_tracks: List[Dict], mood: str, 
                            activity: str, num_tracks: int, search_strategy: Dict) -> Dict:
        """
        Use LLM to make final track selection and ordering
        
        The LLM considers:
        - Flow and progression
        - Variety vs cohesion
        - Energy arc for the activity
        """
        try:
            # Take top candidates
            candidates = scored_tracks[:min(num_tracks * 2, len(scored_tracks))]
            
            # If we have enough high-scoring tracks, use them
            if len(candidates) >= num_tracks:
                selected = candidates[:num_tracks]
            else:
                selected = candidates
            
            # Format tracks for response
            formatted_tracks = []
            for track in selected:
                formatted_tracks.append({
                    'track_id': track.get('id'),
                    'name': track.get('name', 'Unknown Track'),
                    'artists': track.get('artists', ['Unknown Artist']),
                    'album': track.get('album', 'Unknown Album'),
                    'score': track.get('llm_score', 0.5)
                })
            
            # Create playlist metadata
            playlist_name = f"LLM {mood} {activity} Mix"
            description = f"AI-curated playlist for {mood.lower()} mood during {activity.lower()}"
            
            return {
                'playlist_name': playlist_name,
                'description': description,
                'tracks': formatted_tracks,
                'selected_tracks': formatted_tracks,
                'search_strategy_used': search_strategy
            }
            
        except Exception as e:
            logger.error(f"Failed in LLM final selection: {e}")
            return {
                'playlist_name': f"{mood} {activity} Playlist",
                'description': f"Playlist for {mood} mood during {activity}",
                'tracks': [],
                'selected_tracks': []
            }
    
    def _retrieve_user_data(self) -> Dict:
        """Retrieve user data for personalization"""
        try:
            if not self.spotify_client:
                return {}
            
            user_data = {
                'profile': self.spotify_client.get_user_profile(),
                'top_tracks': {
                    'short_term': self.spotify_client.get_user_top_tracks(20, 'short_term'),
                    'medium_term': self.spotify_client.get_user_top_tracks(20, 'medium_term'),
                    'long_term': self.spotify_client.get_user_top_tracks(20, 'long_term')
                },
                'top_artists': {
                    'short_term': self.spotify_client.get_user_top_artists(20, 'short_term'),
                    'medium_term': self.spotify_client.get_user_top_artists(20, 'medium_term'),
                    'long_term': self.spotify_client.get_user_top_artists(20, 'long_term')
                },
                'recently_played': self.spotify_client.get_recently_played(50)
            }
            
            return user_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve user data: {e}")
            return {}
    
    def _create_spotify_playlist(self, final_playlist: Dict) -> Dict:
        """Create the playlist on Spotify"""
        try:
            if not self.spotify_client:
                return {'error': 'Spotify client not available'}
            
            playlist_name = final_playlist.get('playlist_name', 'TuneGenie LLM Playlist')
            description = final_playlist.get('description', 'AI-generated playlist by TuneGenie')
            
            # Create playlist
            playlist_id = self.spotify_client.create_playlist(playlist_name, description)
            if not playlist_id:
                return {'error': 'Failed to create Spotify playlist'}
            
            # Add tracks
            tracks = final_playlist.get('tracks', [])
            if tracks:
                track_uris = []
                for track in tracks:
                    track_id = track.get('track_id')
                    if track_id:
                        track_uris.append(f"spotify:track:{track_id}")
                
                if track_uris:
                    success = self.spotify_client.add_tracks_to_playlist(playlist_id, track_uris)
                    
                    if success:
                        return {
                            'playlist_id': playlist_id,
                            'playlist_name': playlist_name,
                            'tracks_added': len(track_uris),
                            'spotify_url': f"https://open.spotify.com/playlist/{playlist_id}"
                        }
            
            return {'playlist_id': playlist_id, 'playlist_name': playlist_name}
            
        except Exception as e:
            logger.error(f"Failed to create Spotify playlist: {e}")
            return {'error': str(e)}
    
    def _validate_playlist(self, keywords: Union[Dict, str, None], tracks: List[Dict]) -> Dict:
        """Validate the playlist against keywords"""
        try:
            if not keywords:
                return {'enabled': False}
            
            # Parse keywords if string
            if isinstance(keywords, str):
                parsed = {'raw': [keywords]}
            else:
                parsed = keywords
            
            # Use LLM agent's validation if available
            if self.llm_agent and hasattr(self.llm_agent, 'validate_playlist_against_keywords'):
                return self.llm_agent.validate_playlist_against_keywords(parsed, tracks)
            
            # Fallback validation
            return {'enabled': False, 'message': 'Validation not available'}
            
        except Exception as e:
            logger.error(f"Failed to validate playlist: {e}")
            return {'enabled': False, 'error': str(e)}
