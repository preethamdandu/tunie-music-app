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

logger = logging.getLogger(__name__)

class IDMapper:
    """
    Maintains two-way mappings between raw Spotify IDs (users/tracks) and
    Surprise inner integer IDs. Persisted as JSON alongside the trained model.
    """
    def __init__(self):
        self.user_to_inner: Dict[str, int] = {}
        self.inner_to_user: Dict[int, str] = {}
        self.item_to_inner: Dict[str, int] = {}
        self.inner_to_item: Dict[int, str] = {}

    @classmethod
    def from_trainset(cls, trainset) -> 'IDMapper':
        mapper = cls()
        try:
            for inner_uid in range(trainset.n_users):
                raw_uid = trainset.to_raw_uid(inner_uid)
                mapper.user_to_inner[raw_uid] = inner_uid
                mapper.inner_to_user[inner_uid] = raw_uid
            for inner_iid in range(trainset.n_items):
                raw_iid = trainset.to_raw_iid(inner_iid)
                mapper.item_to_inner[raw_iid] = inner_iid
                mapper.inner_to_item[inner_iid] = raw_iid
        except Exception as e:
            logger.warning(f"Failed building IDMapper from trainset: {e}")
        return mapper

    def to_inner_user(self, raw_user_id: str) -> Optional[int]:
        return self.user_to_inner.get(raw_user_id)

    def to_inner_item(self, raw_item_id: str) -> Optional[int]:
        return self.item_to_inner.get(raw_item_id)

    def to_raw_user(self, inner_id: int) -> Optional[str]:
        return self.inner_to_user.get(inner_id)

    def to_raw_item(self, inner_id: int) -> Optional[str]:
        return self.inner_to_item.get(inner_id)

    def save(self, json_path: str) -> None:
        try:
            data = {
                'user_to_inner': self.user_to_inner,
                'inner_to_user': {str(k): v for k, v in self.inner_to_user.items()},
                'item_to_inner': self.item_to_inner,
                'inner_to_item': {str(k): v for k, v in self.inner_to_item.items()},
            }
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save IDMapper to {json_path}: {e}")

    @classmethod
    def load(cls, json_path: str) -> 'IDMapper':
        mapper = cls()
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            mapper.user_to_inner = data.get('user_to_inner', {})
            mapper.inner_to_user = {int(k): v for k, v in (data.get('inner_to_user', {}) or {}).items()}
            mapper.item_to_inner = data.get('item_to_inner', {})
            mapper.inner_to_item = {int(k): v for k, v in (data.get('inner_to_item', {}) or {}).items()}
        except Exception as e:
            logger.warning(f"Failed to load IDMapper from {json_path}: {e}")
        return mapper

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
        # For UI display/metadata by raw track id
        self.reverse_item_mapping = {}
        # Stable persisted mapping between raw ids and Surprise inner ids
        self.id_mapper: Optional[IDMapper] = None
        
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

    def cold_start_recommendations(self, spotify_client, mood: str, activity: str,
                                   n_recommendations: int = 20,
                                   language_preference: str = "Any Language") -> List[Dict]:
        """Cold-start fallback: recommend globally popular tracks aligned to mood/activity.

        Strategy:
        - Build a set of search queries using mood/activity (and language if provided)
        - Fetch tracks via Spotify search
        - Retrieve audio features and score alignment to a simple mood profile
        - Rank by 0.7 * alignment + 0.3 * normalized popularity
        - Return top N tracks in our standard format
        """
        try:
            if not spotify_client:
                logger.warning("Spotify client not available for cold-start fallback")
                return []

            # Generate search queries
            mood_l = (mood or '').lower()
            activity_l = (activity or '').lower()

            queries = [
                f"{mood_l} {activity_l} music",
                f"popular {mood_l} songs",
                f"trending {mood_l} {activity_l}",
                f"{activity_l} playlist",
                f"{mood_l} vibes",
            ]

            # Add language hints if applicable (English treated as broad)
            if language_preference and language_preference != "Any Language":
                lang_q = language_preference.lower()
                queries = [f"{lang_q} {q}" for q in queries]

            # Helper to map mood to target features
            def target_profile() -> Dict[str, float]:
                profile = {
                    'energy': 0.5, 'valence': 0.5, 'danceability': 0.5,
                    'acousticness': 0.3, 'instrumentalness': 0.2
                }
                if 'sad' in mood_l or 'melanch' in mood_l:
                    profile.update({'energy': 0.3, 'valence': 0.2, 'acousticness': 0.5})
                if 'happy' in mood_l or 'uplift' in mood_l:
                    profile.update({'energy': 0.7, 'valence': 0.8, 'danceability': 0.6})
                if 'calm' in mood_l or 'relax' in mood_l:
                    profile.update({'energy': 0.3, 'valence': 0.6, 'acousticness': 0.5})
                if 'energetic' in mood_l or 'motivated' in mood_l:
                    profile.update({'energy': 0.8, 'valence': 0.6})
                if 'focus' in activity_l or 'study' in activity_l:
                    profile.update({'energy': min(profile['energy'], 0.4), 'instrumentalness': 0.4})
                if 'exercise' in activity_l or 'workout' in activity_l:
                    profile.update({'energy': 0.85, 'danceability': 0.7})
                return profile

            target = target_profile()

            def vec(features: Dict[str, float]) -> List[float]:
                return [
                    float(features.get('danceability', 0.0)),
                    float(features.get('energy', 0.0)),
                    float(features.get('valence', 0.0)),
                    float(features.get('acousticness', 0.0)),
                    float(features.get('instrumentalness', 0.0)),
                ]

            def cosine(a: List[float], b: List[float]) -> float:
                import math
                if not a or not b or len(a) != len(b):
                    return 0.0
                dot = sum(x*y for x, y in zip(a, b))
                na = math.sqrt(sum(x*x for x in a))
                nb = math.sqrt(sum(y*y for y in b))
                if na == 0 or nb == 0:
                    return 0.0
                return dot / (na * nb)

            # Aggregate tracks from queries
            seen = set()
            candidates: List[Dict] = []
            per_query = max(10, min(40, n_recommendations * 2))
            for q in queries:
                try:
                    results = spotify_client.search_tracks(q, limit=per_query)
                except Exception as e:
                    logger.debug(f"Search failed for '{q}': {e}")
                    continue
                for t in results:
                    tid = t.get('id')
                    if not tid or tid in seen:
                        continue
                    seen.add(tid)
                    candidates.append(t)
                    if len(candidates) >= n_recommendations * 5:
                        break
                if len(candidates) >= n_recommendations * 5:
                    break

            if not candidates:
                logger.info("No candidates found for cold-start fallback")
                return []

            # Fetch audio features and score
            id_list = [t.get('id') for t in candidates if t.get('id')]
            try:
                feats = spotify_client.get_track_features(id_list)
            except Exception as e:
                logger.debug(f"Failed to fetch audio features: {e}")
                feats = []

            target_vec = vec(target)
            id_to_feat = {}
            for f in feats or []:
                if not f or not f.get('id'):
                    continue
                id_to_feat[f['id']] = vec(f)

            scored: List[Tuple[float, Dict]] = []
            for t in candidates:
                tid = t.get('id')
                pop = float(t.get('popularity', 50)) / 100.0
                align = 0.0
                if tid in id_to_feat:
                    align = cosine(id_to_feat[tid], target_vec)
                final_score = 0.7 * align + 0.3 * pop
                scored.append((final_score, t))

            scored.sort(key=lambda x: x[0], reverse=True)
            top = [s for _, s in scored[:n_recommendations]]

            recs: List[Dict] = []
            for t in top:
                recs.append({
                    'track_id': t.get('id'),
                    'name': t.get('name', 'Unknown Track'),
                    'artists': t.get('artists', ['Unknown Artist']),
                    'score': round(float(t.get('popularity', 50)) / 100.0, 3)
                })

            logger.info(f"Cold-start produced {len(recs)} mood-aligned popular tracks")
            return recs
        except Exception as e:
            logger.error(f"Cold-start recommendations failed: {e}")
            return []
    
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
            
            # Build item metadata keyed by RAW Spotify track id
            unique_users = df['user_id'].unique()
            unique_items = df['item_id'].unique()
            for item_id in unique_items:
                track_data = df[df['item_id'] == item_id].iloc[0]
                self.reverse_item_mapping[item_id] = {
                    'name': track_data.get('name', 'Unknown Track'),
                    'artists': track_data.get('artists', ['Unknown Artist'])
                }
            
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

            # Try to get song metadata from the data if available
            if 'name' in data.columns and 'artists' in data.columns:
                logger.info("Found song metadata in training data")
                for _, row in data.iterrows():
                    item_id = row['item_id']
                    self.reverse_item_mapping[item_id] = {
                        'name': row.get('name', 'Unknown Track'),
                        'artists': row.get('artists', ['Unknown Artist']) if isinstance(row.get('artists'), list) else [row.get('artists', 'Unknown Artist')]
                    }
            else:
                logger.info("No song metadata found, creating basic item info")
                # Create basic item info for each RAW item id
                for item_id in data['item_id'].unique():
                    self.reverse_item_mapping[item_id] = {
                        'name': f'Track {item_id}',
                        'artists': ['Unknown Artist']
                    }
            
            # Convert to Surprise format (using RAW string ids)
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
            
            # Build stable ID mapper from trainset
            self.id_mapper = IDMapper.from_trainset(self.trainset)

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
            if self.id_mapper:
                logger.info(f"Known users: {len(self.id_mapper.user_to_inner)} | items: {len(self.id_mapper.item_to_inner)}")
            else:
                logger.warning("IDMapper missing; rebuilding from trainset if possible")
                if self.trainset:
                    self.id_mapper = IDMapper.from_trainset(self.trainset)
                else:
                    return []

            # Predict for all known RAW items for this RAW user id
            predictions = []
            all_item_raw_ids = list(self.id_mapper.item_to_inner.keys())
            logger.info(f"Starting predictions for {len(all_item_raw_ids)} items")

            for raw_iid in all_item_raw_ids:
                try:
                    pred = self.model.predict(user_id, raw_iid)
                    predictions.append((raw_iid, pred.est))
                except Exception as e:
                    logger.debug(f"Failed to predict for user {user_id}, item {raw_iid}: {e}")
                    continue
            
            logger.info(f"Generated {len(predictions)} predictions")
            
            # Sort by prediction score (highest first)
            predictions.sort(key=lambda x: x[1], reverse=True)
            
            # Get top recommendations
            recommendations = []
            logger.info(f"Processing top {n_recommendations} predictions into recommendations")
            logger.info(f"Item metadata size: {len(self.reverse_item_mapping)}")

            for raw_iid, score in predictions[:n_recommendations]:
                try:
                    item_info = self.reverse_item_mapping.get(raw_iid, {})
                    recommendations.append({
                        'track_id': raw_iid,
                        'name': item_info.get('name', f'Track {raw_iid}'),
                        'artists': item_info.get('artists', ['Unknown Artist']),
                        'score': round(score, 3)
                    })
                except Exception as e:
                    logger.error(f"Failed to process recommendation for item {raw_iid}: {e}")
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
            
            # Save model and metadata
            model_data = {
                'model': self.model,
                'algorithm': self.algorithm,
                'reverse_item_mapping': self.reverse_item_mapping,
                'trainset': self.trainset,
                'training_timestamp': datetime.now().isoformat()
            }
            
            joblib.dump(model_data, filename)
            logger.info(f"Model saved to {filename}")
            # Persist ID mapper JSON alongside the joblib
            try:
                if self.id_mapper:
                    idmap_path = filename.replace('.joblib', '_idmap.json')
                    self.id_mapper.save(idmap_path)
                    logger.info(f"ID mappings saved to {idmap_path}")
            except Exception as e:
                logger.warning(f"Failed to save ID mappings: {e}")
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
            self.reverse_item_mapping = model_data.get('reverse_item_mapping', {})
            self.trainset = model_data['trainset']
            
            # Load or rebuild IDMapper
            idmap_path = filename.replace('.joblib', '_idmap.json')
            if os.path.exists(idmap_path):
                self.id_mapper = IDMapper.load(idmap_path)
            else:
                logger.info("ID map JSON not found; rebuilding from trainset")
                if self.trainset:
                    self.id_mapper = IDMapper.from_trainset(self.trainset)
            
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
                'user_count': len(self.id_mapper.user_to_inner) if self.id_mapper else 0,
                'item_count': len(self.id_mapper.item_to_inner) if self.id_mapper else 0,
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

    def predict_scores_for_items(self, user_id: str, item_ids: List[str]) -> Dict[str, float]:
        """
        Predict scores for a given RAW user id and a list of RAW item ids.
        Order of item_ids must not affect the scores for any specific id.
        """
        try:
            if not self.model:
                return {}
            scores: Dict[str, float] = {}
            for iid in item_ids:
                try:
                    pred = self.model.predict(user_id, iid)
                    scores[iid] = float(pred.est)
                except Exception as e:
                    logger.debug(f"Predict failed for {iid}: {e}")
            return scores
        except Exception as e:
            logger.error(f"predict_scores_for_items failed: {e}")
            return {}
    
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
