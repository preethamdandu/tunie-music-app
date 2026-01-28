"""
Music Toolkit - Comprehensive tool suite for AI Insights
Provides function calling capabilities for real-time music data access
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class MusicToolkit:
    """Comprehensive toolkit for music intelligence with function calling"""
    
    def __init__(self, spotify_client, llm_agent=None):
        """
        Initialize music toolkit
        
        Args:
            spotify_client: Spotify API client
            llm_agent: Optional LLM agent for enhanced analysis
        """
        self.spotify = spotify_client
        self.llm = llm_agent
        self.tools = self._register_tools()
        self.tool_call_history = []
    
    def _register_tools(self) -> Dict:
        """Register all available tools with descriptions and parameters"""
        return {
            # ===== SEARCH TOOLS =====
            'search_tracks': {
                'function': self.search_tracks,
                'description': 'Search for tracks on Spotify by query string',
                'parameters': {
                    'query': {'type': 'str', 'required': True, 'description': 'Search query'},
                    'limit': {'type': 'int', 'required': False, 'default': 10, 'description': 'Number of results'}
                },
                'returns': 'List of track objects with name, artists, album, id',
                'example': 'search_tracks(query="happy songs", limit=5)'
            },
            
            'search_artists': {
                'function': self.search_artists,
                'description': 'Search for artists on Spotify by name',
                'parameters': {
                    'query': {'type': 'str', 'required': True, 'description': 'Artist name or query'},
                    'limit': {'type': 'int', 'required': False, 'default': 10, 'description': 'Number of results'}
                },
                'returns': 'List of artist objects with name, genres, popularity, id',
                'example': 'search_artists(query="Drake", limit=1)'
            },
            
            'search_albums': {
                'function': self.search_albums,
                'description': 'Search for albums on Spotify',
                'parameters': {
                    'query': {'type': 'str', 'required': True, 'description': 'Album name or query'},
                    'limit': {'type': 'int', 'required': False, 'default': 10, 'description': 'Number of results'}
                },
                'returns': 'List of album objects',
                'example': 'search_albums(query="After Hours", limit=5)'
            },
            
            # ===== ARTIST TOOLS =====
            'get_artist_info': {
                'function': self.get_artist_info,
                'description': 'Get detailed information about an artist',
                'parameters': {
                    'artist_id': {'type': 'str', 'required': True, 'description': 'Spotify artist ID'}
                },
                'returns': 'Artist object with full details including genres, popularity, followers',
                'example': 'get_artist_info(artist_id="3TVXtAsR1Inumwj472S9r4")'
            },
            
            'get_artist_top_tracks': {
                'function': self.get_artist_top_tracks,
                'description': 'Get top tracks for an artist',
                'parameters': {
                    'artist_id': {'type': 'str', 'required': True, 'description': 'Spotify artist ID'},
                    'country': {'type': 'str', 'required': False, 'default': 'US', 'description': 'Country code'}
                },
                'returns': 'List of top tracks for the artist',
                'example': 'get_artist_top_tracks(artist_id="3TVXtAsR1Inumwj472S9r4")'
            },
            
            'get_related_artists': {
                'function': self.get_related_artists,
                'description': 'Get artists similar to a given artist',
                'parameters': {
                    'artist_id': {'type': 'str', 'required': True, 'description': 'Spotify artist ID'}
                },
                'returns': 'List of related artists',
                'example': 'get_related_artists(artist_id="3TVXtAsR1Inumwj472S9r4")'
            },
            
            # ===== TRACK ANALYSIS TOOLS =====
            'analyze_track_features': {
                'function': self.analyze_track_features,
                'description': 'Get audio features and analysis for a track',
                'parameters': {
                    'track_id': {'type': 'str', 'required': True, 'description': 'Spotify track ID'}
                },
                'returns': 'Audio features including energy, valence, tempo, danceability, etc.',
                'example': 'analyze_track_features(track_id="3n3Ppam7vgaVa1iaRUc9Lp")'
            },
            
            'compare_tracks': {
                'function': self.compare_tracks,
                'description': 'Compare musical features of two tracks',
                'parameters': {
                    'track_id_1': {'type': 'str', 'required': True, 'description': 'First track ID'},
                    'track_id_2': {'type': 'str', 'required': True, 'description': 'Second track ID'}
                },
                'returns': 'Comparison of audio features between two tracks',
                'example': 'compare_tracks(track_id_1="abc123", track_id_2="def456")'
            },
            
            # ===== RECOMMENDATION TOOLS =====
            'get_recommendations': {
                'function': self.get_recommendations,
                'description': 'Get Spotify recommendations based on seed tracks, artists, or genres',
                'parameters': {
                    'seed_tracks': {'type': 'List[str]', 'required': False, 'description': 'List of track IDs'},
                    'seed_artists': {'type': 'List[str]', 'required': False, 'description': 'List of artist IDs'},
                    'seed_genres': {'type': 'List[str]', 'required': False, 'description': 'List of genres'},
                    'limit': {'type': 'int', 'required': False, 'default': 20, 'description': 'Number of recommendations'}
                },
                'returns': 'List of recommended tracks',
                'example': 'get_recommendations(seed_artists=["3TVXtAsR1Inumwj472S9r4"], limit=10)'
            },
            
            'get_new_releases': {
                'function': self.get_new_releases,
                'description': 'Get latest music releases',
                'parameters': {
                    'country': {'type': 'str', 'required': False, 'default': 'US', 'description': 'Country code'},
                    'limit': {'type': 'int', 'required': False, 'default': 20, 'description': 'Number of releases'}
                },
                'returns': 'List of new album releases',
                'example': 'get_new_releases(country="US", limit=10)'
            },
            
            # ===== USER DATA TOOLS =====
            'get_user_top_tracks': {
                'function': self.get_user_top_tracks,
                'description': 'Get user\'s top tracks',
                'parameters': {
                    'time_range': {'type': 'str', 'required': False, 'default': 'medium_term', 
                                  'description': 'Time range: short_term, medium_term, or long_term'},
                    'limit': {'type': 'int', 'required': False, 'default': 20, 'description': 'Number of tracks'}
                },
                'returns': 'List of user\'s top tracks',
                'example': 'get_user_top_tracks(time_range="short_term", limit=10)'
            },
            
            'get_user_top_artists': {
                'function': self.get_user_top_artists,
                'description': 'Get user\'s top artists',
                'parameters': {
                    'time_range': {'type': 'str', 'required': False, 'default': 'medium_term',
                                  'description': 'Time range: short_term, medium_term, or long_term'},
                    'limit': {'type': 'int', 'required': False, 'default': 20, 'description': 'Number of artists'}
                },
                'returns': 'List of user\'s top artists',
                'example': 'get_user_top_artists(time_range="medium_term", limit=10)'
            },
            
            'analyze_listening_patterns': {
                'function': self.analyze_listening_patterns,
                'description': 'Analyze user listening patterns and trends',
                'parameters': {},
                'returns': 'Analysis of user listening habits, genre preferences, and patterns',
                'example': 'analyze_listening_patterns()'
            },
            
            # ===== PLAYLIST TOOLS =====
            'create_playlist': {
                'function': self.create_playlist,
                'description': 'Create a new playlist for the user',
                'parameters': {
                    'name': {'type': 'str', 'required': True, 'description': 'Playlist name'},
                    'description': {'type': 'str', 'required': False, 'description': 'Playlist description'},
                    'tracks': {'type': 'List[str]', 'required': False, 'description': 'List of track IDs to add'}
                },
                'returns': 'Created playlist object with ID and URL',
                'example': 'create_playlist(name="My Chill Vibes", description="Relaxing music", tracks=["id1", "id2"])'
            },
            
            'get_user_playlists': {
                'function': self.get_user_playlists,
                'description': 'Get user\'s playlists',
                'parameters': {
                    'limit': {'type': 'int', 'required': False, 'default': 20, 'description': 'Number of playlists'}
                },
                'returns': 'List of user playlists',
                'example': 'get_user_playlists(limit=10)'
            },
            
            # ===== GENRE & CATEGORY TOOLS =====
            'get_available_genres': {
                'function': self.get_available_genres,
                'description': 'Get list of available genre seeds for recommendations',
                'parameters': {},
                'returns': 'List of available genres',
                'example': 'get_available_genres()'
            },
            
            'get_categories': {
                'function': self.get_categories,
                'description': 'Get Spotify browse categories',
                'parameters': {
                    'country': {'type': 'str', 'required': False, 'default': 'US', 'description': 'Country code'},
                    'limit': {'type': 'int', 'required': False, 'default': 20, 'description': 'Number of categories'}
                },
                'returns': 'List of browse categories',
                'example': 'get_categories(country="US", limit=10)'
            }
        }
    
    def execute_tool(self, tool_name: str, parameters: Dict = None) -> Any:
        """
        Execute a tool with given parameters
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
        
        Returns:
            Tool execution result
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}")
        
        tool = self.tools[tool_name]
        parameters = parameters or {}
        
        # Log tool call
        self.tool_call_history.append({
            'tool': tool_name,
            'parameters': parameters,
            'timestamp': datetime.now().isoformat()
        })
        
        try:
            result = tool['function'](**parameters)
            logger.info(f"Tool '{tool_name}' executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool '{tool_name}' execution failed: {e}")
            return {'error': str(e), 'tool': tool_name}
    
    def get_tool_descriptions(self, format: str = 'text') -> str:
        """
        Get formatted tool descriptions for LLM
        
        Args:
            format: Output format ('text', 'json', or 'markdown')
        
        Returns:
            Formatted tool descriptions
        """
        if format == 'json':
            return json.dumps(self.tools, indent=2, default=str)
        
        elif format == 'markdown':
            descriptions = ["# Available Tools\n"]
            for name, tool in self.tools.items():
                descriptions.append(f"## {name}")
                descriptions.append(f"**Description:** {tool['description']}\n")
                descriptions.append(f"**Parameters:**")
                for param, details in tool['parameters'].items():
                    req = "required" if details.get('required') else "optional"
                    descriptions.append(f"- `{param}` ({details['type']}, {req}): {details.get('description', '')}")
                descriptions.append(f"\n**Returns:** {tool['returns']}")
                descriptions.append(f"\n**Example:** `{tool['example']}`\n")
            return "\n".join(descriptions)
        
        else:  # text format
            descriptions = []
            for name, tool in self.tools.items():
                params = ", ".join([
                    f"{p}={d.get('type')}" 
                    for p, d in tool['parameters'].items()
                ])
                desc = f"• {name}({params}): {tool['description']}"
                descriptions.append(desc)
            return "\n".join(descriptions)
    
    # ===== TOOL IMPLEMENTATIONS =====
    
    def search_tracks(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for tracks on Spotify"""
        try:
            results = self.spotify.search_tracks(query, limit=limit)
            return results
        except Exception as e:
            logger.error(f"Track search failed: {e}")
            return []
    
    def search_artists(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for artists on Spotify"""
        try:
            results = self.spotify.search_artists(query, limit=limit)
            return results
        except Exception as e:
            logger.error(f"Artist search failed: {e}")
            return []
    
    def search_albums(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for albums on Spotify"""
        try:
            results = self.spotify.search_albums(query, limit=limit)
            return results
        except Exception as e:
            logger.error(f"Album search failed: {e}")
            return []
    
    def get_artist_info(self, artist_id: str) -> Dict:
        """Get detailed artist information"""
        try:
            artist = self.spotify.get_artist(artist_id)
            return artist
        except Exception as e:
            logger.error(f"Get artist info failed: {e}")
            return {'error': str(e)}
    
    def get_artist_top_tracks(self, artist_id: str, country: str = 'US') -> List[Dict]:
        """Get artist's top tracks"""
        try:
            tracks = self.spotify.get_artist_top_tracks(artist_id, country=country)
            return tracks
        except Exception as e:
            logger.error(f"Get artist top tracks failed: {e}")
            return []
    
    def get_related_artists(self, artist_id: str) -> List[Dict]:
        """Get related artists"""
        try:
            artists = self.spotify.get_related_artists(artist_id)
            return artists
        except Exception as e:
            logger.error(f"Get related artists failed: {e}")
            return []
    
    def analyze_track_features(self, track_id: str) -> Dict:
        """Get audio features for a track"""
        try:
            features = self.spotify.get_audio_features(track_id)
            return features
        except Exception as e:
            logger.error(f"Analyze track features failed: {e}")
            return {'error': str(e)}
    
    def compare_tracks(self, track_id_1: str, track_id_2: str) -> Dict:
        """Compare two tracks"""
        try:
            features_1 = self.spotify.get_audio_features(track_id_1)
            features_2 = self.spotify.get_audio_features(track_id_2)
            
            comparison = {
                'track_1': features_1,
                'track_2': features_2,
                'differences': {}
            }
            
            # Calculate differences for key features
            for key in ['energy', 'valence', 'danceability', 'tempo', 'acousticness']:
                if key in features_1 and key in features_2:
                    diff = abs(features_1[key] - features_2[key])
                    comparison['differences'][key] = {
                        'difference': diff,
                        'track_1_value': features_1[key],
                        'track_2_value': features_2[key]
                    }
            
            return comparison
        except Exception as e:
            logger.error(f"Compare tracks failed: {e}")
            return {'error': str(e)}
    
    def get_recommendations(self, seed_tracks: List[str] = None, 
                          seed_artists: List[str] = None,
                          seed_genres: List[str] = None,
                          limit: int = 20) -> List[Dict]:
        """Get Spotify recommendations"""
        try:
            recommendations = self.spotify.get_recommendations(
                seed_tracks=seed_tracks,
                seed_artists=seed_artists,
                seed_genres=seed_genres,
                limit=limit
            )
            return recommendations
        except Exception as e:
            logger.error(f"Get recommendations failed: {e}")
            return []
    
    def get_new_releases(self, country: str = 'US', limit: int = 20) -> List[Dict]:
        """Get new releases"""
        try:
            releases = self.spotify.get_new_releases(country=country, limit=limit)
            return releases
        except Exception as e:
            logger.error(f"Get new releases failed: {e}")
            return []
    
    def get_user_top_tracks(self, time_range: str = 'medium_term', limit: int = 20) -> List[Dict]:
        """Get user's top tracks"""
        try:
            tracks = self.spotify.get_user_top_tracks(limit=limit, time_range=time_range)
            return tracks
        except Exception as e:
            logger.error(f"Get user top tracks failed: {e}")
            return []
    
    def get_user_top_artists(self, time_range: str = 'medium_term', limit: int = 20) -> List[Dict]:
        """Get user's top artists"""
        try:
            artists = self.spotify.get_user_top_artists(limit=limit, time_range=time_range)
            return artists
        except Exception as e:
            logger.error(f"Get user top artists failed: {e}")
            return []
    
    def analyze_listening_patterns(self) -> Dict:
        """Analyze user listening patterns"""
        try:
            # Get user data
            top_tracks = self.get_user_top_tracks(limit=50)
            top_artists = self.get_user_top_artists(limit=50)
            
            # Extract genres
            all_genres = []
            for artist in top_artists:
                all_genres.extend(artist.get('genres', []))
            
            # Count genre frequencies
            genre_counts = {}
            for genre in all_genres:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
            
            # Get top genres
            top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Calculate diversity
            diversity = len(set(all_genres)) / len(all_genres) if all_genres else 0
            
            return {
                'top_genres': [{'genre': g, 'count': c} for g, c in top_genres],
                'total_genres': len(set(all_genres)),
                'diversity_score': diversity,
                'top_artists_count': len(top_artists),
                'top_tracks_count': len(top_tracks),
                'analysis_timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Analyze listening patterns failed: {e}")
            return {'error': str(e)}
    
    def create_playlist(self, name: str, description: str = '', tracks: List[str] = None) -> Dict:
        """Create a new playlist"""
        try:
            playlist_id = self.spotify.create_playlist(name, description)
            
            if tracks and playlist_id:
                track_uris = [f"spotify:track:{tid}" for tid in tracks]
                self.spotify.add_tracks_to_playlist(playlist_id, track_uris)
            
            return {
                'playlist_id': playlist_id,
                'name': name,
                'description': description,
                'tracks_added': len(tracks) if tracks else 0,
                'url': f"https://open.spotify.com/playlist/{playlist_id}"
            }
        except Exception as e:
            logger.error(f"Create playlist failed: {e}")
            return {'error': str(e)}
    
    def get_user_playlists(self, limit: int = 20) -> List[Dict]:
        """Get user's playlists"""
        try:
            playlists = self.spotify.get_user_playlists(limit=limit)
            return playlists
        except Exception as e:
            logger.error(f"Get user playlists failed: {e}")
            return []
    
    def get_available_genres(self) -> List[str]:
        """Get available genre seeds"""
        try:
            genres = self.spotify.get_available_genre_seeds()
            return genres
        except Exception as e:
            logger.error(f"Get available genres failed: {e}")
            return []
    
    def get_categories(self, country: str = 'US', limit: int = 20) -> List[Dict]:
        """Get browse categories"""
        try:
            categories = self.spotify.get_categories(country=country, limit=limit)
            return categories
        except Exception as e:
            logger.error(f"Get categories failed: {e}")
            return []
    
    def get_tool_call_history(self) -> List[Dict]:
        """Get history of tool calls"""
        return self.tool_call_history
    
    def clear_tool_call_history(self):
        """Clear tool call history"""
        self.tool_call_history = []
