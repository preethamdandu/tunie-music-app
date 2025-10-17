import os
import unittest
import random
import pandas as pd

from src.recommender import CollaborativeFilteringRecommender


class TestRecommenderIDMapping(unittest.TestCase):
    def setUp(self):
        os.makedirs('models', exist_ok=True)
        self.model_path = 'models/recommender_idmap_test.joblib'
        self.idmap_path = self.model_path.replace('.joblib', '_idmap.json')
        # Clean any previous artifacts
        for p in [self.model_path, self.idmap_path]:
            if os.path.exists(p):
                os.remove(p)

    def tearDown(self):
        for p in [self.model_path, self.idmap_path]:
            if os.path.exists(p):
                os.remove(p)

    def test_prediction_invariant_to_item_order(self):
        # Create tiny training data with RAW Spotify ids
        user_id = 'spotify:user:test_user_1'
        items = [
            'spotify:track:123',
            'spotify:track:456',
            'spotify:track:789',
        ]
        ratings = [5, 4, 3]
        rows = []
        for iid, r in zip(items, ratings):
            rows.append({
                'user_id': user_id,
                'item_id': iid,
                'rating': r,
                'name': f'Track {iid}',
                'artists': ['Test Artist']
            })
        df = pd.DataFrame(rows)

        # Train and persist
        rec = CollaborativeFilteringRecommender(algorithm='SVD')
        ok = rec.train_model(df)
        self.assertTrue(ok, 'Training failed')

        # Save to a fixed path so we can reload deterministically
        self.assertTrue(rec.save_model(self.model_path))
        self.assertTrue(os.path.exists(self.model_path))
        self.assertTrue(os.path.exists(self.idmap_path))

        # Load back
        rec2 = CollaborativeFilteringRecommender(algorithm='SVD')
        self.assertTrue(rec2.load_model(self.model_path))

        # Predict scores for a target track in two different item orders
        target_track = 'spotify:track:123'
        list_a = ['spotify:track:123', 'spotify:track:456', 'spotify:track:789']
        list_b = list(list_a)
        random.shuffle(list_b)

        scores_a = rec2.predict_scores_for_items(user_id, list_a)
        scores_b = rec2.predict_scores_for_items(user_id, list_b)

        self.assertIn(target_track, scores_a)
        self.assertIn(target_track, scores_b)

        # Order of provided items must not change the predicted value
        self.assertAlmostEqual(scores_a[target_track], scores_b[target_track], places=7)


if __name__ == '__main__':
    unittest.main()


