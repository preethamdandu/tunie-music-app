import os
import unittest
from unittest.mock import patch, MagicMock

from src.spotify_client import SpotifyClient


class TestSpotifyClient(unittest.TestCase):
    def setUp(self):
        # Ensure required env vars exist to allow SpotifyClient construction
        self.env_patch = patch.dict(os.environ, {
            'SPOTIFY_CLIENT_ID': 'dummy',
            'SPOTIFY_CLIENT_SECRET': 'dummy',
            'SPOTIFY_REDIRECT_URI': 'http://localhost/callback'
        }, clear=False)
        self.env_patch.start()

        # Avoid real authentication during tests
        self.auth_patch = patch.object(SpotifyClient, '_authenticate', return_value=None)
        self.auth_patch.start()

        # Create client and inject a mocked spotipy client
        self.client = SpotifyClient()
        self.client.sp = MagicMock()

    def tearDown(self):
        self.auth_patch.stop()
        self.env_patch.stop()

    def test_get_user_top_tracks_basic_and_cache(self):
        # Arrange: mock current_user_top_tracks to return predictable data
        mock_tracks = {
            'items': [
                {
                    'id': 't1',
                    'name': 'Song One',
                    'artists': [{'name': 'Artist A'}],
                    'album': {'name': 'Album A'},
                    'popularity': 80,
                    'duration_ms': 210000,
                    'uri': 'spotify:track:t1'
                },
                {
                    'id': 't2',
                    'name': 'Song Two',
                    'artists': [{'name': 'Artist B'}],
                    'album': {'name': 'Album B'},
                    'popularity': 70,
                    'duration_ms': 200000,
                    'uri': 'spotify:track:t2'
                }
            ]
        }
        self.client.sp.current_user_top_tracks.return_value = mock_tracks

        # Act: call twice with same args to hit the cache
        out1 = self.client.get_user_top_tracks(limit=5, time_range='short_term')
        out2 = self.client.get_user_top_tracks(limit=5, time_range='short_term')

        # Assert: underlying API called only once due to caching
        self.client.sp.current_user_top_tracks.assert_called_once_with(
            limit=5, offset=0, time_range='short_term'
        )

        self.assertEqual(len(out1), 2)
        self.assertEqual(out1, out2)
        self.assertEqual(out1[0]['id'], 't1')
        self.assertEqual(out1[0]['artists'], ['Artist A'])

    def test_add_tracks_to_playlist_chunking(self):
        # Arrange: 150 URIs -> should call playlist_add_items twice (100 + 50)
        playlist_id = 'pl_123'
        track_uris = [f"spotify:track:{i:04d}" for i in range(150)]

        # Act
        success = self.client.add_tracks_to_playlist(playlist_id, track_uris)

        # Assert
        self.assertTrue(success)
        self.assertEqual(self.client.sp.playlist_add_items.call_count, 2)

        # First call with first 100
        first_call_args, first_call_kwargs = self.client.sp.playlist_add_items.call_args_list[0]
        self.assertEqual(first_call_args[0], playlist_id)
        self.assertEqual(first_call_args[1], track_uris[:100])

        # Second call with remaining 50
        second_call_args, second_call_kwargs = self.client.sp.playlist_add_items.call_args_list[1]
        self.assertEqual(second_call_args[0], playlist_id)
        self.assertEqual(second_call_args[1], track_uris[100:])


if __name__ == '__main__':
    unittest.main()


