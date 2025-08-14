"""
Collaborative Filtering Engine for TuneGenie
Uses Surprise library for baseline music recommendations
"""

import os
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from surprise import Dataset, Reader, SVD, KNNBasic, KNNWithMeans, NMF
from surprise.model_selection import train_test_split, cross_validate
from surprise.accuracy import rmse, mae
import joblib
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CollaborativeFilteringRecommender:
    """Collaborative filtering recommendation engine using Surprise library"""
    
    def __init__(self, algorithm: str = 'SVD'):
        """
        Initialize the collaborative filtering recommender
        
        Args:
            algorithm: The algorithm to use ('SVD', 'KNN', etc.)
        """
        self.algorithm = algorithm
        self.model = None
        self.trainset = None
        self.user_mapping = {}
        self.item_mapping = {}
        self.reverse_user_mapping = {}
        self.reverse_item_mapping = {}
        
        # Try to load the most recent trained model
        self._load_latest_model()
        
        logger.info(f"Initialized {algorithm} model")
    
    def _load_latest_model(self):
        """Load the most recent trained model if available"""
        try:
            if not os.path.exists('models'):
                return
            
            # Find the most recent model file
            model_files = [f for f in os.listdir('models') if f.endswith('.joblib')]
            if not model_files:
                return
            
            # Sort by modification time (most recent first)
            model_files.sort(key=lambda x: os.path.getmtime(os.path.join('models', x)), reverse=True)
            latest_model = model_files[0]
            
            # Load the most recent model
            if self.load_model(os.path.join('models', latest_model)):
                logger.info(f"Loaded latest trained model: {latest_model}")
            else:
                logger.warning(f"Failed to load latest model: {latest_model}")
                
        except Exception as e:
            logger.warning(f"Failed to load latest model: {e}")
    
    def _initialize_model(self):
        """Initialize the recommendation model based on algorithm choice"""
        if self.algorithm == 'SVD':
            self.model = SVD(n_factors=100, n_epochs=20, lr_all=0.005, reg_all=0.02)
        elif self.algorithm == 'KNN':
            self.model = KNNBasic(k=40, sim_options={'name': 'pearson', 'user_based': False})
        elif self.algorithm == 'KNNWithMeans':
            self.model = KNNWithMeans(k=40, sim_options={'name': 'pearson', 'user_based': False})
        elif self.algorithm == 'NMF':
            self.model = NMF(n_factors=100, n_epochs=50, biased=False)
        else:
            logger.warning(f"Unknown algorithm {self.algorithm}, defaulting to SVD")
            self.model = SVD()
        
        logger.info(f"Initialized {self.algorithm} model")
    
    def prepare_data(self, user_data: Dict, spotify_client) -> pd.DataFrame:
        """
        Prepare user data for collaborative filtering
        
        Args:
            user_data: User's music listening data
            spotify_client: Spotify client instance
            
        Returns:
            DataFrame with user-item interactions
        """
        try:
            interactions = []
            
            # Process top tracks with implicit ratings
            for time_range, tracks in user_data.get('top_tracks', {}).items():
                for i, track in enumerate(tracks):
                    # Higher position = higher implicit rating
                    rating = max(1, 50 - i)  # 50 for 1st, 49 for 2nd, etc.
                    interactions.append({
                        'user_id': user_data['profile']['id'],
                        'item_id': track['id'],
                        'rating': rating,
                        'timestamp': datetime.now().timestamp(),
                        'interaction_type': f'top_track_{time_range}',
                        'name': track.get('name', 'Unknown Track'),
                        'artists': track.get('artists', ['Unknown Artist'])
                    })
            
            # Process recently played tracks
            for track in user_data.get('recently_played', []):
                interactions.append({
                    'user_id': user_data['profile']['id'],
                    'item_id': track['id'],
                    'rating': 3,  # Medium rating for recently played
                    'timestamp': datetime.now().timestamp(),
                    'interaction_type': 'recently_played',
                    'name': track.get('name', 'Unknown Track'),
                    'artists': track.get('artists', ['Unknown Artist'])
                })
            
            # Process playlist tracks
            for playlist in user_data.get('playlists', []):
                playlist_tracks = spotify_client.get_playlist_tracks(playlist['id'])
                for track in playlist_tracks:
                    interactions.append({
                        'user_id': user_data['profile']['id'],
                        'item_id': track['id'],
                        'rating': 4,  # High rating for saved playlist tracks
                        'timestamp': datetime.now().timestamp(),
                        'interaction_type': 'playlist_saved',
                        'name': track.get('name', 'Unknown Track'),
                        'artists': track.get('artists', ['Unknown Artist'])
                    })
            
            # Convert to DataFrame
            df = pd.DataFrame(interactions)
            
            if df.empty:
                logger.warning("No interaction data found")
                return pd.DataFrame()
            
            # Create user and item mappings
            unique_users = df['user_id'].unique()
            unique_items = df['item_id'].unique()
            
            for i, user_id in enumerate(unique_users):
                self.user_mapping[user_id] = i
                self.reverse_user_mapping[i] = user_id
            
            for i, item_id in enumerate(unique_items):
                self.item_mapping[item_id] = i
                # Store song metadata in reverse mapping
                track_data = df[df['item_id'] == item_id].iloc[0]
                self.reverse_item_mapping[item_id] = {
                    'name': track_data.get('name', 'Unknown Track'),
                    'artists': track_data.get('artists', ['Unknown Artist'])
                }
            
            # Convert to numeric IDs for Surprise
            df['user_id'] = df['user_id'].map(self.user_mapping)
            df['item_id'] = df['item_id'].map(self.item_mapping)
            
            logger.info(f"Prepared data: {len(df)} interactions, {len(unique_users)} users, {len(unique_items)} items")
            return df
            
        except Exception as e:
            logger.error(f"Failed to prepare data: {e}")
            return pd.DataFrame()
    
    def train_model(self, data: pd.DataFrame) -> bool:
        """
        Train the collaborative filtering model
        
        Args:
            data: DataFrame with columns ['user_id', 'item_id', 'rating']
            
        Returns:
            True if training successful, False otherwise
        """
        try:
            if data.empty:
                logger.error("No data provided for training")
                return False
            
            logger.info(f"Prepared data: {len(data)} interactions, {data['user_id'].nunique()} users, {data['item_id'].nunique()} items")
            
            # Create user and item mappings
            unique_users = data['user_id'].unique()
            unique_items = data['item_id'].unique()
            
            self.user_mapping = {user_id: idx for idx, user_id in enumerate(unique_users)}
            self.item_mapping = {item_id: idx for idx, item_id in enumerate(unique_items)}
            
            # Create reverse mappings
            self.reverse_user_mapping = {idx: user_id for user_id, idx in self.user_mapping.items()}
            self.reverse_item_mapping = {item_id: idx for item_id, idx in self.item_mapping.items()}
            
            # Try to get song metadata from the data if available
            if 'name' in data.columns and 'artists' in data.columns:
                logger.info("Found song metadata in training data")
                for _, row in data.iterrows():
                    item_id = row['item_id']
                    if item_id in self.reverse_item_mapping:
                        self.reverse_item_mapping[item_id] = {
                            'name': row.get('name', 'Unknown Track'),
                            'artists': row.get('artists', ['Unknown Artist']) if isinstance(row.get('artists'), list) else [row.get('artists', 'Unknown Artist')]
                        }
            else:
                logger.info("No song metadata found, creating basic item info")
                # Create basic item info
                for item_id in unique_items:
                    self.reverse_item_mapping[item_id] = {
                        'name': f'Track {self.item_mapping[item_id]}',
                        'artists': ['Unknown Artist']
                    }
            
            # Convert to Surprise format
            reader = Reader(rating_scale=(1, 5))
            self.trainset = Dataset.load_from_df(data[['user_id', 'item_id', 'rating']], reader).build_full_trainset()
            
            # Initialize and train the model
            if self.algorithm == 'SVD':
                self.model = SVD(n_factors=100, n_epochs=20, lr_all=0.005, reg_all=0.02)
            elif self.algorithm == 'KNN':
                self.model = KNNWithMeans(k=50, sim_options={'name': 'pearson', 'user_based': False})
            elif self.algorithm == 'NMF':
                self.model = NMF(n_factors=100, n_epochs=50, lr_bu=0.005, lr_bi=0.005, reg_bu=0.02, reg_bi=0.02)
            else:
                self.model = SVD()  # Default to SVD
            
            # Train the model
            self.model.fit(self.trainset)
            
            # Evaluate the model
            predictions = self.model.test(self.trainset.build_testset())
            rmse_score = rmse(predictions)
            mae_score = mae(predictions)
            
            logger.info(f"Model training completed:")
            logger.info(f"RMSE: {rmse_score:.4f}")
            logger.info(f"MAE: {mae_score:.4f}")
            
            # Save the trained model
            self.save_model()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to train model: {e}")
            return False
    
    def get_recommendations(self, user_id: str, n_recommendations: int = 20) -> List[Dict]:
        """
        Get recommendations for a specific user
        
        Args:
            user_id: User ID to get recommendations for
            n_recommendations: Number of recommendations to return
            
        Returns:
            List of recommended tracks with scores
        """
        try:
            if not self.model:
                logger.warning("Model not trained yet")
                return []
            
            logger.info(f"Getting recommendations for user {user_id}")
            logger.info(f"User mapping size: {len(self.user_mapping)}")
            logger.info(f"Item mapping size: {len(self.item_mapping)}")
            
            # Convert user_id to internal user index
            if user_id not in self.user_mapping:
                # If user not in training data, add them with a default rating
                logger.info(f"User {user_id} not in training data, adding them")
                user_idx = len(self.user_mapping)
                self.user_mapping[user_id] = user_idx
                self.reverse_user_mapping[user_idx] = user_id
            
            user_idx = self.user_mapping[user_id]
            logger.info(f"User internal index: {user_idx}")
            
            # Get predictions for all items for this user
            predictions = []
            logger.info(f"Starting predictions for {len(self.item_mapping)} items")
            
            for item_idx in range(len(self.item_mapping)):
                try:
                    pred = self.model.predict(user_idx, item_idx)
                    predictions.append((item_idx, pred.est))
                except Exception as e:
                    logger.debug(f"Failed to predict for user {user_idx}, item {item_idx}: {e}")
                    continue
            
            logger.info(f"Generated {len(predictions)} predictions")
            
            # Sort by prediction score (highest first)
            predictions.sort(key=lambda x: x[1], reverse=True)
            
            # Get top recommendations
            recommendations = []
            logger.info(f"Processing top {n_recommendations} predictions into recommendations")
            logger.info(f"Reverse item mapping size: {len(self.reverse_item_mapping)}")
            
            for item_idx, score in predictions[:n_recommendations]:
                try:
                    # Convert back to original item ID
                    original_item_id = list(self.item_mapping.keys())[item_idx]
                    logger.debug(f"Processing item {item_idx} -> {original_item_id}")
                    
                    # Get item details from the reverse mapping
                    if original_item_id in self.reverse_item_mapping:
                        item_info = self.reverse_item_mapping[original_item_id]
                        recommendations.append({
                            'track_id': original_item_id,
                            'name': item_info.get('name', 'Unknown Track'),
                            'artists': item_info.get('artists', ['Unknown Artist']),
                            'score': round(score, 3)
                        })
                        logger.debug(f"Added recommendation: {item_info.get('name', 'Unknown Track')}")
                    else:
                        # If reverse mapping is missing, create a basic recommendation
                        logger.warning(f"Item {original_item_id} not found in reverse mapping, creating basic info")
                        recommendations.append({
                            'track_id': original_item_id,
                            'name': f'Track {item_idx}',
                            'artists': ['Unknown Artist'],
                            'score': round(score, 3)
                        })
                except Exception as e:
                    logger.error(f"Failed to process recommendation {item_idx}: {e}")
                    continue
            
            logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return []
    
    def cross_validate_model(self, data: pd.DataFrame, cv_folds: int = 5) -> Dict:
        """
        Perform cross-validation to evaluate model performance
        
        Args:
            data: DataFrame with user-item interactions
            cv_folds: Number of cross-validation folds
            
        Returns:
            Dictionary with cross-validation results
        """
        try:
            if data.empty:
                logger.error("No data provided for cross-validation")
                return {}
            
            reader = Reader(rating_scale=(1, 5))
            dataset = Dataset.load_from_df(data[['user_id', 'item_id', 'rating']], reader)
            
            # Perform cross-validation
            cv_results = cross_validate(self.model, dataset, measures=['RMSE', 'MAE'], cv=cv_folds, verbose=True)
            
            results = {
                'algorithm': self.algorithm,
                'cv_folds': cv_folds,
                'test_rmse_mean': cv_results['test_rmse'].mean(),
                'test_rmse_std': cv_results['test_rmse'].std(),
                'test_mae_mean': cv_results['test_mae'].mean(),
                'test_mae_std': cv_results['test_mae'].std(),
                'fit_time_mean': cv_results['fit_time'].mean(),
                'test_time_mean': cv_results['test_time'].mean()
            }
            
            logger.info(f"Cross-validation results for {self.algorithm}:")
            logger.info(f"Test RMSE: {results['test_rmse_mean']:.4f} (+/- {results['test_rmse_std']:.4f})")
            logger.info(f"Test MAE: {results['test_mae_mean']:.4f} (+/- {results['test_mae_std']:.4f})")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to perform cross-validation: {e}")
            return {}
    
    def save_model(self, filename: str = None) -> bool:
        """
        Save the trained model to disk
        
        Args:
            filename: Optional custom filename
            
        Returns:
            True if save successful, False otherwise
        """
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"models/collaborative_filtering_{self.algorithm}_{timestamp}.joblib"
            
            # Save model and mappings
            model_data = {
                'model': self.model,
                'algorithm': self.algorithm,
                'user_mapping': self.user_mapping,
                'item_mapping': self.item_mapping,
                'reverse_user_mapping': self.reverse_user_mapping,
                'reverse_item_mapping': self.reverse_item_mapping,
                'trainset': self.trainset,
                'training_timestamp': datetime.now().isoformat()
            }
            
            joblib.dump(model_data, filename)
            logger.info(f"Model saved to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False
    
    def load_model(self, filename: str) -> bool:
        """
        Load a trained model from disk
        
        Args:
            filename: Path to the saved model file
            
        Returns:
            True if load successful, False otherwise
        """
        try:
            if not os.path.exists(filename):
                logger.error(f"Model file {filename} not found")
                return False
            
            # Load model and mappings
            model_data = joblib.load(filename)
            
            self.model = model_data['model']
            self.algorithm = model_data['algorithm']
            self.user_mapping = model_data['user_mapping']
            self.item_mapping = model_data['item_mapping']
            self.reverse_user_mapping = model_data['reverse_user_mapping']
            self.reverse_item_mapping = model_data['reverse_item_mapping']
            self.trainset = model_data['trainset']
            
            # Ensure reverse mappings are complete
            if not self.reverse_item_mapping and self.item_mapping:
                logger.info("Rebuilding reverse item mapping...")
                self.reverse_item_mapping = {}
                for item_id, item_idx in self.item_mapping.items():
                    # Create basic item info if not available
                    self.reverse_item_mapping[item_id] = {
                        'name': f'Track {item_idx}',
                        'artists': ['Unknown Artist']
                    }
            
            if not self.reverse_user_mapping and self.user_mapping:
                logger.info("Rebuilding reverse user mapping...")
                self.reverse_user_mapping = {}
                for user_id, user_idx in self.user_mapping.items():
                    self.reverse_user_mapping[user_idx] = user_id
            
            logger.info(f"Model loaded from {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    def get_model_info(self) -> Dict:
        """Get information about the current model"""
        try:
            training_data_size = 0
            if self.trainset:
                # Convert generator to list to get length
                ratings = list(self.trainset.all_ratings())
                training_data_size = len(ratings)
            
            return {
                'algorithm': self.algorithm,
                'is_trained': self.model is not None and self.trainset is not None,
                'user_count': len(self.user_mapping),
                'item_count': len(self.item_mapping),
                'training_data_size': training_data_size
            }
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return {
                'algorithm': self.algorithm,
                'is_trained': False,
                'user_count': 0,
                'item_count': 0,
                'training_data_size': 0
            }
    
    def update_model(self, new_data: pd.DataFrame) -> bool:
        """
        Update the model with new data (incremental learning)
        
        Args:
            new_data: New user-item interactions
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            if new_data.empty:
                logger.warning("No new data provided for model update")
                return False
            
            # For now, retrain the entire model
            # In production, you might implement incremental learning
            logger.info("Updating model with new data (full retraining)")
            return self.train_model(new_data)
            
        except Exception as e:
            logger.error(f"Failed to update model: {e}")
            return False
