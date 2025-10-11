"""
Utility functions for TuneGenie
Data processing, visualization, and common operations
"""

import os
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import logging
logger = logging.getLogger(__name__)

class DataProcessor:
    """Utility class for data processing operations"""
    
    @staticmethod
    def normalize_ratings(ratings: List[float], min_rating: float = 1.0, max_rating: float = 5.0) -> List[float]:
        """
        Normalize ratings to a 0-1 scale
        
        Args:
            ratings: List of ratings to normalize
            min_rating: Minimum rating value
            max_rating: Maximum rating value
            
        Returns:
            List of normalized ratings
        """
        if not ratings:
            return []
        
        ratings_array = np.array(ratings)
        normalized = (ratings_array - min_rating) / (max_rating - min_rating)
        return normalized.tolist()
    
    @staticmethod
    def calculate_diversity_score(tracks: List[Dict], features: List[str] = None) -> float:
        """
        Calculate diversity score for a list of tracks
        
        Args:
            tracks: List of track dictionaries
            features: List of features to consider for diversity
            
        Returns:
            Diversity score (0-1, higher = more diverse)
        """
        if not tracks or len(tracks) < 2:
            return 0.0
        
        if features is None:
            features = ['artists', 'genres', 'tempo', 'energy']
        
        diversity_scores = []
        
        for feature in features:
            if feature == 'artists':
                unique_artists = set()
                for track in tracks:
                    if 'artists' in track:
                        unique_artists.update(track['artists'])
                diversity_scores.append(len(unique_artists) / len(tracks))
            
            elif feature == 'genres':
                unique_genres = set()
                for track in tracks:
                    if 'genres' in track:
                        unique_genres.update(track['genres'])
                diversity_scores.append(len(unique_genres) / len(tracks))
            
            elif feature in ['tempo', 'energy', 'valence', 'danceability']:
                values = [track.get(feature, 0) for track in tracks if track.get(feature) is not None]
                if values:
                    std_dev = np.std(values)
                    mean_val = np.mean(values)
                    if mean_val > 0:
                        diversity_scores.append(std_dev / mean_val)
                    else:
                        diversity_scores.append(0.0)
        
        return np.mean(diversity_scores) if diversity_scores else 0.0
    
    @staticmethod
    def extract_audio_features(tracks: List[Dict], spotify_client) -> List[Dict]:
        """
        Extract audio features for tracks using Spotify API
        
        Args:
            tracks: List of track dictionaries
            spotify_client: Spotify client instance
            
        Returns:
            List of tracks with audio features
        """
        try:
            track_ids = [track['id'] for track in tracks if 'id' in track]
            if not track_ids:
                return tracks
            
            # Get audio features in batches
            features = spotify_client.get_track_features(track_ids)
            
            # Merge features with track data
            enhanced_tracks = []
            for i, track in enumerate(tracks):
                if i < len(features) and features[i]:
                    track['audio_features'] = features[i]
                enhanced_tracks.append(track)
            
            return enhanced_tracks
            
        except Exception as e:
            logger.error(f"Failed to extract audio features: {e}")
            return tracks
    
    @staticmethod
    def create_user_profile_summary(user_data: Dict) -> Dict:
        """
        Create a summary of user's music profile
        
        Args:
            user_data: User's music data from Spotify
            
        Returns:
            Dictionary with profile summary
        """
        try:
            summary = {
                'total_tracks': 0,
                'total_artists': 0,
                'top_genres': [],
                'listening_patterns': {},
                'preferences': {}
            }
            
            # Count tracks across time ranges
            for time_range, tracks in user_data.get('top_tracks', {}).items():
                summary['total_tracks'] += len(tracks)
                summary['listening_patterns'][time_range] = len(tracks)
            
            # Count artists across time ranges
            for time_range, artists in user_data.get('top_artists', {}).items():
                summary['total_artists'] += len(artists)
            
            # Extract top genres
            all_genres = []
            for time_range, artists in user_data.get('top_artists', {}).items():
                for artist in artists:
                    all_genres.extend(artist.get('genres', []))
            
            # Count genre frequencies
            genre_counts = {}
            for genre in all_genres:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
            
            # Get top 10 genres
            top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            summary['top_genres'] = [genre for genre, count in top_genres]
            
            # Analyze preferences
            summary['preferences'] = {
                'genre_diversity': len(set(all_genres)),
                'artist_diversity': summary['total_artists'],
                'listening_consistency': len(summary['listening_patterns']),
                'playlist_count': len(user_data.get('playlists', []))
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to create user profile summary: {e}")
            return {}

class Visualizer:
    """Utility class for data visualization"""
    
    @staticmethod
    def create_user_profile_chart(user_data: Dict) -> go.Figure:
        """
        Create a comprehensive user profile visualization
        
        Args:
            user_data: User's music data
            
        Returns:
            Plotly figure object
        """
        try:
            # Create subplots
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Top Genres', 'Listening Patterns', 'Artist Popularity', 'Track Distribution'),
                specs=[[{"type": "bar"}, {"type": "bar"}],
                       [{"type": "scatter"}, {"type": "pie"}]]
            )
            
            # Top Genres Chart
            all_genres = []
            for time_range, artists in user_data.get('top_artists', {}).items():
                for artist in artists:
                    all_genres.extend(artist.get('genres', []))
            
            genre_counts = {}
            for genre in all_genres:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
            
            top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            fig.add_trace(
                go.Bar(x=[genre for genre, count in top_genres], 
                       y=[count for genre, count in top_genres],
                       name="Genre Frequency"),
                row=1, col=1
            )
            
            # Listening Patterns Chart
            time_ranges = list(user_data.get('top_tracks', {}).keys())
            track_counts = [len(user_data['top_tracks'][tr]) for tr in time_ranges]
            
            fig.add_trace(
                go.Bar(x=time_ranges, y=track_counts, name="Track Count"),
                row=1, col=2
            )
            
            # Artist Popularity Chart
            all_artists = []
            for time_range, artists in user_data.get('top_artists', {}).items():
                for artist in artists:
                    all_artists.append({
                        'name': artist['name'],
                        'popularity': artist.get('popularity', 0),
                        'time_range': time_range
                    })
            
            # Sort by popularity and take top 20
            all_artists.sort(key=lambda x: x['popularity'], reverse=True)
            top_artists = all_artists[:20]
            
            fig.add_trace(
                go.Scatter(x=[artist['name'] for artist in top_artists],
                           y=[artist['popularity'] for artist in top_artists],
                           mode='markers',
                           name="Artist Popularity"),
                row=2, col=1
            )
            
            # Track Distribution Pie Chart
            total_tracks = sum(len(tracks) for tracks in user_data.get('top_tracks', {}).values())
            fig.add_trace(
                go.Pie(labels=time_ranges,
                       values=[len(tracks) for tracks in user_data.get('top_tracks', {}).values()],
                       name="Track Distribution"),
                row=2, col=2
            )
            
            # Update layout
            fig.update_layout(
                title="TuneGenie User Profile Analysis",
                height=800,
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Failed to create user profile chart: {e}")
            # Return empty figure
            return go.Figure()
    
    @staticmethod
    def create_recommendation_analysis_chart(recommendations: List[Dict], 
                                           user_profile: Dict) -> go.Figure:
        """
        Create visualization for recommendation analysis
        
        Args:
            recommendations: List of recommendations
            user_profile: User's profile data
            
        Returns:
            Plotly figure object
        """
        try:
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Recommendation Scores', 'Score Distribution', 'Algorithm Performance', 'User Preference Match'),
                specs=[[{"type": "bar"}, {"type": "histogram"}],
                       [{"type": "scatter"}, {"type": "bar"}]]
            )
            
            if not recommendations:
                return go.Figure()
            
            # Recommendation Scores
            track_names = [f"Track {i+1}" for i in range(len(recommendations))]
            scores = [rec.get('score', 0) for rec in recommendations]
            
            fig.add_trace(
                go.Bar(x=track_names, y=scores, name="Recommendation Scores"),
                row=1, col=1
            )
            
            # Score Distribution
            fig.add_trace(
                go.Histogram(x=scores, name="Score Distribution", nbinsx=10),
                row=1, col=2
            )
            
            # Algorithm Performance (if multiple algorithms)
            algorithms = [rec.get('algorithm', 'Unknown') for rec in recommendations]
            algorithm_counts = {}
            for algo in algorithms:
                algorithm_counts[algo] = algorithm_counts.get(algo, 0) + 1
            
            fig.add_trace(
                go.Bar(x=list(algorithm_counts.keys()), 
                       y=list(algorithm_counts.values()),
                       name="Algorithm Usage"),
                row=2, col=1
            )
            
            # User Preference Match (simplified)
            preference_match = [min(score / 5.0, 1.0) for score in scores]  # Normalize to 0-1
            fig.add_trace(
                go.Bar(x=track_names, y=preference_match, name="Preference Match"),
                row=2, col=2
            )
            
            fig.update_layout(
                title="TuneGenie Recommendation Analysis",
                height=800,
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Failed to create recommendation analysis chart: {e}")
            return go.Figure()
    
    @staticmethod
    def create_workflow_performance_chart(workflow_history: List[Dict]) -> go.Figure:
        """
        Create visualization for workflow performance
        
        Args:
            workflow_history: List of workflow execution records
            
        Returns:
            Plotly figure object
        """
        try:
            if not workflow_history:
                return go.Figure()
            
            # Convert timestamps to datetime
            for record in workflow_history:
                record['start_time'] = datetime.fromisoformat(record['start_time'])
                record['end_time'] = datetime.fromisoformat(record['end_time'])
                record['duration'] = (record['end_time'] - record['start_time']).total_seconds()
            
            # Group by workflow type
            workflow_types = {}
            for record in workflow_history:
                wf_type = record['workflow_type']
                if wf_type not in workflow_types:
                    workflow_types[wf_type] = []
                workflow_types[wf_type].append(record)
            
            # Create subplots
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Workflow Execution Count', 'Execution Duration', 'Success Rate', 'Recent Activity'),
                specs=[[{"type": "bar"}, {"type": "box"}],
                       [{"type": "bar"}, {"type": "scatter"}]]
            )
            
            # Workflow Execution Count
            wf_names = list(workflow_types.keys())
            wf_counts = [len(workflow_types[name]) for name in wf_names]
            
            fig.add_trace(
                go.Bar(x=wf_names, y=wf_counts, name="Execution Count"),
                row=1, col=1
            )
            
            # Execution Duration
            all_durations = [record['duration'] for record in workflow_history]
            fig.add_trace(
                go.Box(y=all_durations, name="Duration Distribution"),
                row=1, col=2
            )
            
            # Success Rate
            success_counts = {}
            for wf_type, records in workflow_types.items():
                success_count = sum(1 for record in records if record.get('status') == 'success')
                success_counts[wf_type] = success_count / len(records) * 100
            
            fig.add_trace(
                go.Bar(x=list(success_counts.keys()), 
                       y=list(success_counts.values()),
                       name="Success Rate (%)"),
                row=2, col=1
            )
            
            # Recent Activity Timeline
            recent_records = sorted(workflow_history, key=lambda x: x['start_time'])[-20:]
            fig.add_trace(
                go.Scatter(x=[record['start_time'] for record in recent_records],
                           y=[record['duration'] for record in recent_records],
                           mode='markers',
                           name="Recent Executions"),
                row=2, col=2
            )
            
            fig.update_layout(
                title="TuneGenie Workflow Performance Analysis",
                height=800,
                showlegend=True
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Failed to create workflow performance chart: {e}")
            return go.Figure()

class FileManager:
    """Utility class for file operations"""
    
    @staticmethod
    def save_json(data: Dict, filename: str, directory: str = 'data') -> bool:
        """
        Save data to JSON file
        
        Args:
            data: Data to save
            filename: Name of the file
            directory: Directory to save in
            
        Returns:
            True if successful, False otherwise
        """
        try:
            os.makedirs(directory, exist_ok=True)
            filepath = os.path.join(directory, filename)
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Data saved to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save data to {filename}: {e}")
            return False
    
    @staticmethod
    def load_json(filename: str, directory: str = 'data') -> Optional[Dict]:
        """
        Load data from JSON file
        
        Args:
            filename: Name of the file
            directory: Directory to load from
            
        Returns:
            Loaded data or None if failed
        """
        try:
            filepath = os.path.join(directory, filename)
            
            if not os.path.exists(filepath):
                logger.warning(f"File {filepath} not found")
                return None
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            logger.info(f"Data loaded from {filepath}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to load data from {filename}: {e}")
            return None
    
    @staticmethod
    def backup_file(filename: str, directory: str = 'data', backup_suffix: str = '.backup') -> bool:
        """
        Create a backup of a file
        
        Args:
            filename: Name of the file to backup
            directory: Directory containing the file
            backup_suffix: Suffix for backup files
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filepath = os.path.join(directory, filename)
            backup_path = filepath + backup_suffix
            
            if os.path.exists(filepath):
                import shutil
                shutil.copy2(filepath, backup_path)
                logger.info(f"Backup created: {backup_path}")
                return True
            else:
                logger.warning(f"File {filepath} not found for backup")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create backup of {filename}: {e}")
            return False

class MetricsCalculator:
    """Utility class for calculating various metrics"""
    
    @staticmethod
    def calculate_recommendation_metrics(recommendations: List[Dict], 
                                      user_feedback: List[Dict]) -> Dict:
        """
        Calculate recommendation quality metrics
        
        Args:
            recommendations: List of recommendations
            user_feedback: User feedback on recommendations
            
        Returns:
            Dictionary with calculated metrics
        """
        try:
            if not recommendations or not user_feedback:
                return {}
            
            metrics = {
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0,
                'user_satisfaction': 0.0,
                'diversity_score': 0.0
            }
            
            # Calculate precision and recall (simplified)
            relevant_recommendations = sum(1 for feedback in user_feedback if feedback.get('rating', 0) >= 3)
            total_recommendations = len(recommendations)
            
            if total_recommendations > 0:
                metrics['precision'] = relevant_recommendations / total_recommendations
            
            # Calculate user satisfaction
            ratings = [feedback.get('rating', 0) for feedback in user_feedback]
            if ratings:
                metrics['user_satisfaction'] = sum(ratings) / len(ratings)
            
            # Calculate diversity score
            metrics['diversity_score'] = DataProcessor.calculate_diversity_score(recommendations)
            
            # Calculate F1 score
            if metrics['precision'] + metrics['recall'] > 0:
                metrics['f1_score'] = 2 * (metrics['precision'] * metrics['recall']) / (metrics['precision'] + metrics['recall'])
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate recommendation metrics: {e}")
            return {}
    
    @staticmethod
    def calculate_performance_metrics(workflow_history: List[Dict]) -> Dict:
        """
        Calculate workflow performance metrics
        
        Args:
            workflow_history: List of workflow execution records
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            if not workflow_history:
                return {}
            
            metrics = {
                'total_executions': len(workflow_history),
                'success_rate': 0.0,
                'avg_execution_time': 0.0,
                'workflow_distribution': {},
                'error_rate': 0.0
            }
            
            # Calculate success rate
            successful_executions = sum(1 for record in workflow_history if record.get('status') == 'success')
            metrics['success_rate'] = successful_executions / len(workflow_history)
            metrics['error_rate'] = 1 - metrics['success_rate']
            
            # Calculate average execution time
            execution_times = []
            for record in workflow_history:
                if 'start_time' in record and 'end_time' in record:
                    start = datetime.fromisoformat(record['start_time'])
                    end = datetime.fromisoformat(record['end_time'])
                    duration = (end - start).total_seconds()
                    execution_times.append(duration)
            
            if execution_times:
                metrics['avg_execution_time'] = sum(execution_times) / len(execution_times)
            
            # Calculate workflow distribution
            for record in workflow_history:
                wf_type = record.get('workflow_type', 'unknown')
                metrics['workflow_distribution'][wf_type] = metrics['workflow_distribution'].get(wf_type, 0) + 1
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate performance metrics: {e}")
            return {}
