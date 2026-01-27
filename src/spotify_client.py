"""
Spotify API Client for TuneGenie
Handles authentication, user data retrieval, and playlist management
"""

from __future__ import annotations

import os
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import List, Dict, Optional, Tuple
import pandas as pd
from datetime import datetime
import logging
from dotenv import load_dotenv
import time
import random
import requests
from cachetools import TTLCache, cached
from functools import lru_cache
from cachetools.keys import hashkey

logger = logging.getLogger(__name__)

# 15-minute TTL cache for expensive Spotify reads
cache = TTLCache(maxsize=100, ttl=900)

def spotify_retry_handler(func):
    """
    Decorator that retries Spotify API calls with exponential backoff.

    - Retries up to 3 times on:
      * spotipy.exceptions.SpotifyException with 429 or 5xx http_status
      * requests.exceptions.RequestException (network errors)
    - Logs a clear warning before each retry
    - Honors Retry-After header for 429 when available; otherwise uses backoff
    """
    def wrapper(*args, **kwargs):
        max_retries = 3
        base_delay = 1.0  # seconds
        attempt = 0
        while True:
            try:
                return func(*args, **kwargs)
            except spotipy.exceptions.SpotifyException as e:
                status = getattr(e, 'http_status', None)
                should_retry = status == 429 or (isinstance(status, int) and status >= 500)
                if not should_retry or attempt >= max_retries:
                    raise

                attempt += 1

                # Compute delay: Retry-After for 429, else exponential backoff with jitter
                delay = None
                if status == 429:
                    # Try to read Retry-After header
                    retry_after = None
                    try:
                        headers = getattr(e, 'headers', {}) or {}
                        retry_after = headers.get('Retry-After') or headers.get('retry-after')
                    except Exception:
                        retry_after = None
                    try:
                        delay = float(retry_after)
                    except Exception:
                        delay = None

                if delay is None:
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.25)

                logger.warning(
                    f"Spotify API call {func.__name__} failed with status {status}. "
                    f"Retry attempt {attempt}/{max_retries} in {delay:.2f}s"
                )
                time.sleep(delay)
                continue
            except requests.exceptions.RequestException as e:
                if attempt >= max_retries:
                    raise
                attempt += 1
                delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
                logger.warning(
                    f"Network error during Spotify call {func.__name__}: {e}. "
                    f"Retry attempt {attempt}/{max_retries} in {delay:.2f}s"
                )
                time.sleep(delay)
                continue
    
    return wrapper

class SpotifyClient:
    """Spotify API client for music data retrieval and playlist management"""
    
    def __init__(self):
        """Initialize Spotify client with OAuth authentication"""
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')
        
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("Missing Spotify API credentials in environment variables")
        
        # Initialize Spotify client with OAuth
        self.scope = [
            'user-read-private',
            'user-read-email',
            'user-top-read',
            'user-read-recently-played',
            'playlist-read-private',
            'playlist-modify-public',
            'playlist-modify-private'
        ]
        
        self.sp = None
        self.authenticated = False
        # Don't authenticate immediately - wait for user interaction
        try:
            self._authenticate()
        except Exception as e:
            logger.warning(f"Spotify authentication deferred: {e}")
            # This is expected - user needs to authorize first
    
    def _authenticate(self):
        """Authenticate with Spotify using OAuth"""
        try:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=' '.join(self.scope)
            ))
            # Test the connection
            self.sp.current_user()
            self.authenticated = True
            logger.info("Successfully authenticated with Spotify")
        except Exception as e:
            logger.warning(f"Spotify authentication failed: {e}")
            self.authenticated = False
            # Don't raise - this is expected for first-time users
    
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated"""
        if not self.sp:
            return False
        try:
            # Test the connection
            self.sp.current_user()
            self.authenticated = True
            return True
        except:
            self.authenticated = False
            return False
    
    def get_user_profile(self) -> Dict:
        """Get current user's profile information"""
        try:
            user = self.sp.current_user()
            return {
                'id': user['id'],
                'display_name': user['display_name'],
                'email': user.get('email', ''),
                'country': user.get('country', ''),
                'followers': user['followers']['total'] if user['followers'] else 0
            }
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return {}
    
    # cache key that isolates by client instance and parameters
    def _cache_key_ignore_self(self, *args, **kwargs):
        return hashkey(id(self), *args, **kwargs)

    @cached(cache, key=_cache_key_ignore_self)
    @spotify_retry_handler
    def get_user_top_tracks(self, limit: int = 50, time_range: str = 'medium_term') -> List[Dict]:
        """Get user's top tracks"""
        
        try:
            # Spotify API limit is 50
            actual_limit = min(limit, 50)
            top_tracks = self.sp.current_user_top_tracks(
                limit=actual_limit, 
                offset=0, 
                time_range=time_range
            )
            
            tracks = []
            for track in top_tracks['items']:
                track_info = {
                    'id': track['id'],
                    'name': track['name'],
                    'artists': [artist['name'] for artist in track['artists']],
                    'album': track['album']['name'],
                    'popularity': track['popularity'],
                    'duration_ms': track['duration_ms'],
                    'uri': track['uri']
                }
                tracks.append(track_info)
            # Enrich with audio features so downstream heuristic profiler has sufficient data
            try:
                track_ids = [t['id'] for t in tracks if t.get('id')]
                features_by_id = self.get_audio_features_for_tracks(track_ids)
                for t in tracks:
                    fid = t.get('id')
                    feats = features_by_id.get(fid, {}) if fid else {}
                    # Attach a compact subset commonly used by heuristics and filters
                    t['audio_features'] = {
                        'energy': feats.get('energy'),
                        'valence': feats.get('valence'),
                        'acousticness': feats.get('acousticness'),
                        'danceability': feats.get('danceability'),
                        'instrumentalness': feats.get('instrumentalness'),
                        'tempo': feats.get('tempo')
                    }
            except Exception as enrich_e:
                logger.warning(f"Failed to enrich top tracks with audio features: {enrich_e}")

            return tracks
        except Exception as e:
            logger.error(f"Failed to get top tracks: {e}")
            return []
    
    @cached(cache, key=_cache_key_ignore_self)
    @spotify_retry_handler
    def get_user_top_artists(self, limit: int = 50, time_range: str = 'medium_term') -> List[Dict]:
        """Get user's top artists"""
        try:
            # Spotify API limit is 50
            actual_limit = min(limit, 50)
            top_artists = self.sp.current_user_top_artists(
                limit=actual_limit, 
                offset=0, 
                time_range=time_range
            )
            
            artists = []
            for artist in top_artists['items']:
                artist_info = {
                    'id': artist['id'],
                    'name': artist['name'],
                    'genres': artist.get('genres', []),
                    'popularity': artist['popularity'],
                    'uri': artist['uri']
                }
                artists.append(artist_info)
            # Ensure full artist objects with genres by refetching details in batch if needed
            try:
                missing_or_empty = any(not a.get('genres') for a in artists)
                if artists and missing_or_empty:
                    ids = [a['id'] for a in artists if a.get('id')]
                    for i in range(0, len(ids), 50):
                        batch = ids[i:i+50]
                        try:
                            full = self.sp.artists(batch) or {}
                        except Exception as inner:
                            logger.debug(f"Batch artists() lookup failed: {inner}")
                            continue
                        by_id = {a.get('id'): a for a in full.get('artists', [])}
                        for a in artists:
                            fa = by_id.get(a.get('id')) if a.get('id') else None
                            if fa and (not a.get('genres')):
                                a['genres'] = fa.get('genres', []) or []
            except Exception as enrich_e:
                logger.debug(f"Failed to enrich top artists with full objects: {enrich_e}")

            return artists
        except Exception as e:
            logger.error(f"Failed to get top artists: {e}")
            return []
    
    @cached(cache, key=_cache_key_ignore_self)
    @spotify_retry_handler
    def get_recently_played(self, limit: int = 50) -> List[Dict]:
        """Get user's recently played tracks"""
        try:
            # Spotify API limit is 50
            actual_limit = min(limit, 50)
            recent_tracks = self.sp.current_user_recently_played(limit=actual_limit)
            
            tracks = []
            for item in recent_tracks['items']:
                track = item['track']
                track_info = {
                    'id': track['id'],
                    'name': track['name'],
                    'artists': [artist['name'] for artist in track['artists']],
                    'album': track['album']['name'],
                    'played_at': item['played_at'],
                    'uri': track['uri']
                }
                tracks.append(track_info)
            
            return tracks
        except Exception as e:
            logger.error(f"Failed to get recently played: {e}")
            return []
    
    def get_track_features(self, track_ids: List[str]) -> List[Dict]:
        """Get audio features for multiple tracks"""
        try:
            if not track_ids:
                return []
            
            # Spotify API allows max 100 tracks per request
            features = []
            for i in range(0, len(track_ids), 100):
                batch = track_ids[i:i+100]
                batch_features = self.sp.audio_features(batch)
                features.extend(batch_features)
            
            return features
        except Exception as e:
            logger.error(f"Failed to get track features: {e}")
            return []

    def get_audio_features_for_tracks(self, track_ids: List[str]) -> Dict[str, Dict]:
        """
        Public entrypoint that normalizes a list of track IDs and leverages a
        memoized helper keyed by a stable tuple of IDs for single-session speedups.
        """
        try:
            if not track_ids:
                return {}
            # Build a stable cache key: normalize, dedupe, sort
            key = tuple(sorted({str(t).strip() for t in track_ids if isinstance(t, str) and str(t).strip()}))
            return self._get_audio_features_for_tracks_cached(key)
        except Exception as e:
            logger.error(f"Failed to retrieve audio features for tracks: {e}")
            return {}

    # This in-memory LRU cache (per-process, per-session) complements our cross-session TTLCache.
    # TTLCache reduces redundant API reads across calls with time-based expiry; LRU here accelerates
    # repeated lookups of the same immutable-by-ID payload within a single app session.
    @lru_cache(maxsize=128)
    def _get_audio_features_for_tracks_cached(self, cleaned_ids_key: tuple) -> Dict[str, Dict]:
        try:
            cleaned_ids: List[str] = list(cleaned_ids_key)
            features_by_id: Dict[str, Dict] = {}

            for i in range(0, len(cleaned_ids), 100):
                batch = cleaned_ids[i:i+100]
                try:
                    results = self.sp.audio_features(batch)
                except Exception as e:
                    logger.warning(f"audio_features request failed for batch starting with {batch[0] if batch else 'empty'}: {e}")
                    continue

                if not results:
                    logger.warning("audio_features returned no data for a batch")
                    for tid in batch:
                        features_by_id.setdefault(tid, {})
                    continue

                for idx, feat in enumerate(results):
                    tid = batch[idx] if idx < len(batch) else None
                    if not tid:
                        continue
                    if feat is None:
                        logger.debug(f"No audio features available for track id {tid}")
                        features_by_id.setdefault(tid, {})
                    else:
                        features_by_id[tid] = feat

            for tid in cleaned_ids:
                features_by_id.setdefault(tid, {})

            return features_by_id
        except Exception as e:
            logger.error(f"_get_audio_features_for_tracks_cached failed: {e}")
            return {}
    
    def get_track_analysis(self, track_id: str) -> Dict:
        """Get detailed audio analysis for a single track"""
        try:
            analysis = self.sp.audio_analysis(track_id)
            return analysis
        except Exception as e:
            logger.error(f"Failed to get track analysis: {e}")
            return {}
    
    def search_tracks(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for tracks by query"""
        try:
            results = self.sp.search(q=query, type='track', limit=limit)
            
            tracks = []
            for track in results['tracks']['items']:
                track_info = {
                    'id': track['id'],
                    'name': track['name'],
                    'artists': [artist['name'] for artist in track['artists']],
                    'album': track['album']['name'],
                    'popularity': track['popularity'],
                    'uri': track['uri']
                }
                tracks.append(track_info)
            
            return tracks
        except Exception as e:
            logger.error(f"Failed to search tracks: {e}")
            return []

    def search_tracks_by_keywords(self, keywords, limit: int = 50) -> List[Dict]:
        """
        Search Spotify for tracks using parsed keywords. Supports artist, title/track, album, genre, and raw terms.
        If a string is provided, it's treated as a raw query.
        """
        try:
            # Normalize input
            if isinstance(keywords, str):
                queries = [keywords]
            else:
                queries = []
                artists = keywords.get('artists', [])
                titles = keywords.get('titles', [])
                albums = keywords.get('albums', [])
                genres = keywords.get('genres', [])
                raw_terms = keywords.get('raw', [])

                # Build specific operator queries to improve precision
                for artist in artists:
                    queries.append(f'artist:"{artist}"')
                for title in titles:
                    # Spotify supports both "track:" and "title:"; use track for better coverage
                    queries.append(f'track:"{title}"')
                for album in albums:
                    queries.append(f'album:"{album}"')
                for genre in genres:
                    # genre operator is primarily for artist search but still helpful as a signal
                    queries.append(f'genre:"{genre}"')
                for term in raw_terms:
                    queries.append(term)

                # If mood/activity context is provided inside keywords, include as broaders
                context_terms = keywords.get('context', [])
                for term in context_terms:
                    queries.append(term)

            # Execute searches and merge results
            seen: set[str] = set()
            combined: List[Dict] = []
            per_query_limit = max(5, min(50, limit))

            for q in queries:
                try:
                    results = self.sp.search(q=q, type='track', limit=per_query_limit)
                    for item in results.get('tracks', {}).get('items', []):
                        track_id = item.get('id')
                        if not track_id or track_id in seen:
                            continue
                        seen.add(track_id)
                        combined.append({
                            'id': track_id,
                            'name': item.get('name'),
                            'artists': [a.get('name') for a in item.get('artists', [])],
                            'album': (item.get('album') or {}).get('name'),
                            'popularity': item.get('popularity'),
                            'uri': item.get('uri')
                        })
                        if len(combined) >= limit:
                            break
                except Exception as inner_e:
                    logger.warning(f"Keyword search failed for query '{q}': {inner_e}")
                if len(combined) >= limit:
                    break

            return combined[:limit]
        except Exception as e:
            logger.error(f"Failed keyword track search: {e}")
            return []
    
    def create_playlist(self, name: str, description: str = "", public: bool = True) -> Optional[str]:
        """Create a new playlist for the current user"""
        try:
            user = self.sp.current_user()
            playlist = self.sp.user_playlist_create(
                user=user['id'],
                name=name,
                description=description,
                public=public
            )
            return playlist['id']
        except Exception as e:
            logger.error(f"Failed to create playlist: {e}")
            return None
    
    def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]) -> bool:
        """Add tracks to an existing playlist"""
        try:
            if not track_uris:
                logger.info(f"No tracks to add for playlist {playlist_id}")
                return True

            # Clean and deduplicate URIs
            cleaned = []
            seen = set()
            for uri in track_uris:
                if not isinstance(uri, str):
                    continue
                u = uri.strip()
                if not u or u in seen:
                    continue
                seen.add(u)
                cleaned.append(u)

            # Spotify accepts up to 100 items per request
            batch_size = 100
            total = len(cleaned)
            added = 0

            for i in range(0, total, batch_size):
                chunk = cleaned[i:i + batch_size]
                # Perform the API call for this chunk
                self.sp.playlist_add_items(playlist_id, chunk)
                added += len(chunk)
                logger.debug(f"Added chunk of {len(chunk)} tracks to {playlist_id} ({added}/{total})")

            logger.info(f"Successfully added {added} tracks to playlist {playlist_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add tracks to playlist: {e}")
            return False
    
    def get_user_playlists(self, limit: int = 50) -> List[Dict]:
        """Get user's playlists"""
        try:
            # Spotify API limit is 50
            actual_limit = min(limit, 50)
            playlists = self.sp.current_user_playlists(limit=actual_limit)
            
            playlist_list = []
            for playlist in playlists['items']:
                playlist_info = {
                    'id': playlist['id'],
                    'name': playlist['name'],
                    'description': playlist.get('description', ''),
                    'tracks_total': playlist['tracks']['total'],
                    'uri': playlist['uri']
                }
                playlist_list.append(playlist_info)
            
            return playlist_list
        except Exception as e:
            logger.error(f"Failed to get user playlists: {e}")
            return []
    
    def get_playlist_tracks(self, playlist_id: str, limit: int = 100) -> List[Dict]:
        """Get tracks from a specific playlist"""
        try:
            tracks = self.sp.playlist_tracks(playlist_id, limit=limit)
            
            track_list = []
            for item in tracks['items']:
                track = item['track']
                if track:
                    track_info = {
                        'id': track['id'],
                        'name': track['name'],
                        'artists': [artist['name'] for artist in track['artists']],
                        'album': track['album']['name'],
                        'uri': track['uri']
                    }
                    track_list.append(track_info)
            
            return track_list
        except Exception as e:
            logger.error(f"Failed to get playlist tracks: {e}")
            return []
    
    def export_user_data(self) -> Dict:
        """Export comprehensive user data for analysis"""
        try:
            user_data = {
                'profile': self.get_user_profile(),
                'top_tracks': {
                    'short_term': self.get_user_top_tracks(50, 'short_term'),
                    'medium_term': self.get_user_top_tracks(50, 'medium_term'),
                    'long_term': self.get_user_top_tracks(50, 'long_term')
                },
                'top_artists': {
                    'short_term': self.get_user_top_artists(50, 'short_term'),
                    'medium_term': self.get_user_top_artists(50, 'medium_term'),
                    'long_term': self.get_user_top_artists(50, 'long_term')
                },
                'recently_played': self.get_recently_played(100),
                'playlists': self.get_user_playlists(100),
                'exported_at': datetime.now().isoformat()
            }
            
            # Save to file
            os.makedirs('data', exist_ok=True)
            with open('data/user_data.json', 'w') as f:
                json.dump(user_data, f, indent=2)
            
            logger.info("User data exported successfully")
            return user_data
            
        except Exception as e:
            logger.error(f"Failed to export user data: {e}")
            return {}
    
    def get_recommendation_seeds(self, limit: int = 5) -> Dict:
        """Get seed tracks, artists, and genres for recommendations"""
        try:
            # Get top tracks and artists as seeds
            top_tracks = self.get_user_top_tracks(limit, 'medium_term')
            top_artists = self.get_user_top_artists(limit, 'medium_term')
            
            # Get user's top genres
            genres = []
            for artist in top_artists:
                genres.extend(artist['genres'])
            
            # Get most common genres
            genre_counts = {}
            for genre in genres:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
            
            top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
            
            return {
                'seed_tracks': [track['id'] for track in top_tracks[:limit]],
                'seed_artists': [artist['id'] for artist in top_artists[:limit]],
                'seed_genres': [genre[0] for genre in top_genres]
            }
        except Exception as e:
            logger.error(f"Failed to get recommendation seeds: {e}")
            return {}

    def search_tracks_by_artist(self, artist_name: str, limit: int = 50) -> List[Dict]:
        """
        Search Spotify for tracks by a specific artist
        
        Args:
            artist_name: Name of the artist to search for
            limit: Maximum number of tracks to return
            
        Returns:
            List of track dictionaries with id, name, artists, etc.
        """
        try:
            if not self.is_authenticated():
                logger.warning("Spotify client not authenticated")
                return []
            
            # Search for the artist first
            artist_results = self.sp.search(q=artist_name, type='artist', limit=1)
            if not artist_results['artists']['items']:
                logger.warning(f"Artist '{artist_name}' not found on Spotify")
                return []
            
            artist_id = artist_results['artists']['items'][0]['id']
            artist_name_actual = artist_results['artists']['items'][0]['name']
            logger.info(f"Found artist: {artist_name_actual} (ID: {artist_id})")
            
            # Get top tracks by the artist (Spotify returns max 10, so we need to get more)
            top_tracks = self.sp.artist_top_tracks(artist_id)
            tracks = []
            
            # Add top tracks
            for track in top_tracks['tracks']:
                track_info = {
                    'id': track['id'],
                    'name': track['name'],
                    'artists': [artist['name'] for artist in track['artists']],
                    'album': track['album']['name'],
                    'popularity': track['popularity'],
                    'duration_ms': track['duration_ms'],
                    'external_urls': track['external_urls'],
                    'uri': track['uri']
                }
                tracks.append(track_info)
            
            # If we need more tracks, search for additional tracks by the artist
            if len(tracks) < limit:
                logger.info(f"Need more tracks, searching for additional {artist_name_actual} songs")
                
                # Search for tracks by artist name
                search_results = self.sp.search(
                    q=f"artist:{artist_name_actual}", 
                    type='track', 
                    limit=min(50, limit * 2)  # Get more to filter from
                )
                
                for track in search_results['tracks']['items']:
                    # Check if this track is already in our list
                    if not any(t['id'] == track['id'] for t in tracks):
                        track_info = {
                            'id': track['id'],
                            'name': track['name'],
                            'artists': [artist['name'] for artist in track['artists']],
                            'album': track['album']['name'],
                            'popularity': track['popularity'],
                            'duration_ms': track['duration_ms'],
                            'external_urls': track['external_urls'],
                            'uri': track['uri']
                        }
                        tracks.append(track_info)
                        
                        if len(tracks) >= limit:
                            break
            
            logger.info(f"Found {len(tracks)} tracks by {artist_name_actual} (requested: {limit})")
            return tracks[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search tracks by artist '{artist_name}': {e}")
            return []
    
    def search_tracks_by_artist_and_mood(self, artist_name: str, mood: str, limit: int = 50) -> List[Dict]:
        """
        Search Spotify for tracks by artist and filter by mood characteristics
        
        Args:
            artist_name: Name of the artist to search for
            mood: Mood to filter by (energetic, calm, happy, sad, etc.)
            limit: Maximum number of tracks to return
            
        Returns:
            List of track dictionaries filtered by mood
        """
        try:
            # Get all tracks by the artist
            all_tracks = self.search_tracks_by_artist(artist_name, limit * 2)  # Get more to filter from
            
            if not all_tracks:
                return []
            
            # Try to get audio features for mood filtering
            try:
                track_ids = [track['id'] for track in all_tracks]
                audio_features = self.sp.audio_features(track_ids)
                
                if audio_features and len(audio_features) > 0:
                    # Define mood characteristics for filtering
                    mood_filters = {
                        'energetic': {
                            'min_tempo': 120,
                            'min_energy': 0.7,
                            'min_danceability': 0.6,
                            'max_valence': 0.9
                        },
                        'calm': {
                            'max_tempo': 100,
                            'max_energy': 0.4,
                            'max_danceability': 0.5,
                            'min_acousticness': 0.3
                        },
                        'happy': {
                            'min_tempo': 100,
                            'min_energy': 0.5,
                            'min_valence': 0.7,
                            'min_danceability': 0.5
                        },
                        'sad': {
                            'max_tempo': 90,
                            'max_energy': 0.4,
                            'max_valence': 0.4,
                            'min_acousticness': 0.2
                        },
                        'focused': {
                            'max_tempo': 110,
                            'max_energy': 0.6,
                            'min_instrumentalness': 0.1,
                            'max_speechiness': 0.3
                        }
                    }
                    
                    # Filter tracks based on mood
                    filtered_tracks = []
                    mood_filter = mood_filters.get(mood.lower(), {})
                    
                    for i, track in enumerate(all_tracks):
                        if i >= len(audio_features) or not audio_features[i]:
                            continue
                            
                        features = audio_features[i]
                        matches_mood = True
                        
                        # Apply mood filters
                        for feature, threshold in mood_filter.items():
                            if feature == 'min_tempo' and features.get('tempo', 0) < threshold:
                                matches_mood = False
                                break
                            elif feature == 'max_tempo' and features.get('tempo', 0) > threshold:
                                matches_mood = False
                                break
                            elif feature == 'min_energy' and features.get('energy', 0) < threshold:
                                matches_mood = False
                                break
                            elif feature == 'max_energy' and features.get('energy', 0) > threshold:
                                matches_mood = False
                                break
                            elif feature == 'min_valence' and features.get('valence', 0) < threshold:
                                matches_mood = False
                                break
                            elif feature == 'max_valence' and features.get('valence', 0) > threshold:
                                matches_mood = False
                                break
                            elif feature == 'min_danceability' and features.get('danceability', 0) < threshold:
                                matches_mood = False
                                break
                            elif feature == 'max_danceability' and features.get('danceability', 0) > threshold:
                                matches_mood = False
                                break
                            elif feature == 'min_acousticness' and features.get('acousticness', 0) < threshold:
                                matches_mood = False
                                break
                            elif feature == 'min_instrumentalness' and features.get('instrumentalness', 0) < threshold:
                                matches_mood = False
                                break
                            elif feature == 'max_speechiness' and features.get('speechiness', 0) > threshold:
                                matches_mood = False
                                break
                        
                        if matches_mood:
                            filtered_tracks.append(track)
                            if len(filtered_tracks) >= limit:
                                break
                    
                    if filtered_tracks:
                        logger.info(f"Mood filtering successful: {len(filtered_tracks)} tracks by {artist_name} for {mood} mood")
                        return filtered_tracks[:limit]
                    else:
                        logger.info(f"No tracks matched mood filter for {mood}, returning top tracks")
                        return all_tracks[:limit]
                        
                else:
                    logger.info("Audio features not available, returning top tracks without mood filtering")
                    return all_tracks[:limit]
                    
            except Exception as e:
                logger.warning(f"Audio features filtering failed: {e}, returning top tracks")
                return all_tracks[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search tracks by artist and mood '{artist_name}' + '{mood}': {e}")
            return []

    def search_for_artists(self, keywords: List[str], per_keyword_limit: int = 5) -> List[Dict]:
        """
        Search Spotify for artists using a list of keyword terms and return unique artist objects.

        Args:
            keywords: List of search terms (artist names, synonyms, niche terms)
            per_keyword_limit: Max artists to fetch per keyword

        Returns:
            List of artist dicts with keys: id, name, genres, popularity, followers, uri
        """
        try:
            if not keywords:
                return []

            seen_ids: set[str] = set()
            artists: List[Dict] = []

            for term in keywords:
                if not term or not isinstance(term, str):
                    continue
                q = term.strip()
                if not q:
                    continue
                try:
                    results = self.sp.search(q=q, type='artist', limit=max(1, min(50, per_keyword_limit)))
                except Exception as e:
                    logger.debug(f"Artist search failed for term '{q}': {e}")
                    continue

                items = (results or {}).get('artists', {}).get('items', [])
                for a in items:
                    aid = a.get('id')
                    if not aid or aid in seen_ids:
                        continue
                    seen_ids.add(aid)
                    artists.append({
                        'id': aid,
                        'name': a.get('name', ''),
                        'genres': a.get('genres', []) or [],
                        'popularity': a.get('popularity', 0),
                        'followers': (a.get('followers') or {}).get('total', 0),
                        'uri': a.get('uri', '')
                    })

            return artists
        except Exception as e:
            logger.error(f"Failed to search for artists: {e}")
            return []

    def get_top_tracks_for_artists(self, artist_ids: List[str], market: str = 'US', limit: int = 10) -> Dict[str, List[Dict]]:
        """
        Public entrypoint that normalizes a list of artist IDs and delegates to a
        memoized helper keyed by a stable tuple of IDs.
        """
        try:
            if not artist_ids:
                return {}
            key = tuple(sorted({str(a).strip() for a in artist_ids if isinstance(a, str) and str(a).strip()}))
            return self._get_top_tracks_for_artists_cached(key, market, int(limit))
        except Exception as e:
            logger.error(f"Failed to retrieve top tracks for artists: {e}")
            return {}

    @lru_cache(maxsize=128)
    def _get_top_tracks_for_artists_cached(self, artist_ids_key: tuple, market: str, limit: int) -> Dict[str, List[Dict]]:
        results: Dict[str, List[Dict]] = {}
        try:
            artist_ids: List[str] = list(artist_ids_key)
            for aid in artist_ids:
                if not isinstance(aid, str) or not aid.strip():
                    results[aid] = [] if aid is not None else []
                    continue
                artist_id = aid.strip()
                try:
                    top = self.sp.artist_top_tracks(artist_id, country=market)
                except TypeError:
                    try:
                        top = self.sp.artist_top_tracks(artist_id)
                    except Exception as e:
                        logger.debug(f"artist_top_tracks failed for {artist_id}: {e}")
                        results[artist_id] = []
                        continue
                except Exception as e:
                    logger.debug(f"artist_top_tracks failed for {artist_id}: {e}")
                    results[artist_id] = []
                    continue

                tracks_out: List[Dict] = []
                for t in (top or {}).get('tracks', [])[:max(1, min(10, limit))]:
                    tracks_out.append({
                        'id': t.get('id'),
                        'name': t.get('name', ''),
                        'artists': [ar.get('name') for ar in (t.get('artists') or [])],
                        'album': (t.get('album') or {}).get('name', ''),
                        'popularity': t.get('popularity', 0),
                        'duration_ms': t.get('duration_ms', 0),
                        'uri': t.get('uri', ''),
                        'external_urls': (t.get('external_urls') or {})
                    })

                results[artist_id] = tracks_out

            return results
        except Exception as e:
            logger.error(f"_get_top_tracks_for_artists_cached failed: {e}")
            return results
