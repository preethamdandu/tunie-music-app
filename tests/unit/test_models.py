"""
Unit Tests for Data Models

Tests for Track, Recommendation, User, and Workflow models.
"""

import pytest
from datetime import datetime


class TestAudioFeatures:
    """Tests for AudioFeatures model"""

    def test_from_spotify_response(self, sample_audio_features):
        """Test creating AudioFeatures from Spotify API response"""
        from src.models.track import AudioFeatures
        
        features = AudioFeatures.from_spotify_response(sample_audio_features)
        
        assert features.energy == 0.75
        assert features.valence == 0.65
        assert features.danceability == 0.70
        assert features.tempo == 128.0

    def test_to_dict(self, sample_audio_features):
        """Test serialization to dictionary"""
        from src.models.track import AudioFeatures
        
        features = AudioFeatures.from_spotify_response(sample_audio_features)
        result = features.to_dict()
        
        assert isinstance(result, dict)
        assert result["energy"] == 0.75
        assert "tempo" in result

    def test_to_feature_vector(self, sample_audio_features):
        """Test conversion to numerical feature vector"""
        from src.models.track import AudioFeatures
        
        features = AudioFeatures.from_spotify_response(sample_audio_features)
        vector = features.to_feature_vector()
        
        assert isinstance(vector, list)
        assert len(vector) == 9
        assert all(isinstance(v, float) for v in vector)

    def test_feature_values_normalized(self):
        """Test that out-of-range values are normalized"""
        from src.models.track import AudioFeatures
        
        # Create with out-of-range values
        features = AudioFeatures(energy=1.5, valence=-0.5, danceability=0.5)
        
        # Values should be clamped to 0-1
        assert 0.0 <= features.energy <= 1.0
        assert 0.0 <= features.valence <= 1.0


class TestTrack:
    """Tests for Track model"""

    def test_from_spotify_response(self, sample_track_data):
        """Test creating Track from Spotify API response"""
        from src.models.track import Track
        
        track = Track.from_spotify_response(sample_track_data)
        
        assert track.id == "test_track_123"
        assert track.name == "Sample Track"
        assert "Sample Artist" in track.artists
        assert track.album == "Sample Album"
        assert track.popularity == 70

    def test_from_spotify_response_with_features(self, sample_track_data, sample_audio_features):
        """Test creating Track with audio features"""
        from src.models.track import Track
        
        track = Track.from_spotify_response(sample_track_data, sample_audio_features)
        
        assert track.audio_features is not None
        assert track.audio_features.energy == 0.75

    def test_artist_string_property(self, sample_track_data):
        """Test artist_string property"""
        from src.models.track import Track
        
        track = Track.from_spotify_response(sample_track_data)
        
        assert track.artist_string == "Sample Artist"

    def test_display_name_property(self, sample_track_data):
        """Test display_name property"""
        from src.models.track import Track
        
        track = Track.from_spotify_response(sample_track_data)
        
        assert track.display_name == "Sample Track - Sample Artist"

    def test_track_equality_by_id(self, sample_track_data):
        """Test that tracks are equal if they have the same ID"""
        from src.models.track import Track
        
        track1 = Track.from_spotify_response(sample_track_data)
        track2 = Track.from_spotify_response(sample_track_data)
        
        assert track1 == track2

    def test_track_hash(self, sample_track_data):
        """Test that tracks can be hashed (for use in sets/dicts)"""
        from src.models.track import Track
        
        track = Track.from_spotify_response(sample_track_data)
        
        # Should not raise
        track_set = {track}
        assert track in track_set

    def test_to_dict_and_from_dict_roundtrip(self, sample_track_data, sample_audio_features):
        """Test serialization roundtrip"""
        from src.models.track import Track
        
        original = Track.from_spotify_response(sample_track_data, sample_audio_features)
        serialized = original.to_dict()
        restored = Track.from_dict(serialized)
        
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.audio_features is not None


class TestRecommendation:
    """Tests for Recommendation model"""

    def test_create_recommendation(self, sample_track_data):
        """Test creating a recommendation"""
        from src.models.track import Track
        from src.models.recommendation import Recommendation, RecommendationSource
        
        track = Track.from_spotify_response(sample_track_data)
        rec = Recommendation(
            track=track,
            score=0.85,
            source=RecommendationSource.COLLABORATIVE,
            rank=1,
        )
        
        assert rec.track.id == "test_track_123"
        assert rec.score == 0.85
        assert rec.source == RecommendationSource.COLLABORATIVE

    def test_confidence_property(self, sample_track_data):
        """Test confidence level categorization"""
        from src.models.track import Track
        from src.models.recommendation import Recommendation
        
        track = Track.from_spotify_response(sample_track_data)
        
        high_conf = Recommendation(track=track, score=0.9)
        assert high_conf.confidence == "High"
        
        med_conf = Recommendation(track=track, score=0.6)
        assert med_conf.confidence == "Medium"
        
        low_conf = Recommendation(track=track, score=0.3)
        assert low_conf.confidence == "Low"

    def test_recommendation_equality_by_track_id(self, sample_track_data):
        """Test recommendations equal if same track"""
        from src.models.track import Track
        from src.models.recommendation import Recommendation
        
        track = Track.from_spotify_response(sample_track_data)
        rec1 = Recommendation(track=track, score=0.8)
        rec2 = Recommendation(track=track, score=0.5)  # Different score
        
        assert rec1 == rec2


class TestRecommendationBatch:
    """Tests for RecommendationBatch model"""

    def test_batch_tracks_property(self, sample_track_data):
        """Test extracting tracks from batch"""
        from src.models.track import Track
        from src.models.recommendation import Recommendation, RecommendationBatch
        
        track = Track.from_spotify_response(sample_track_data)
        rec = Recommendation(track=track, score=0.8)
        batch = RecommendationBatch(recommendations=[rec])
        
        tracks = batch.tracks
        assert len(tracks) == 1
        assert tracks[0].id == "test_track_123"

    def test_batch_average_score(self, sample_track_data):
        """Test average score calculation"""
        from src.models.track import Track
        from src.models.recommendation import Recommendation, RecommendationBatch
        
        track = Track.from_spotify_response(sample_track_data)
        recs = [
            Recommendation(track=track, score=0.8),
            Recommendation(track=track, score=0.6),
        ]
        batch = RecommendationBatch(recommendations=recs)
        
        assert batch.average_score == 0.7


class TestTasteProfile:
    """Tests for TasteProfile model"""

    def test_to_context_string(self, sample_taste_profile):
        """Test generating LLM context string"""
        from src.models.user import TasteProfile
        
        profile = TasteProfile.from_dict(sample_taste_profile)
        context = profile.to_context_string()
        
        assert isinstance(context, str)
        assert "Artist 1" in context or "pop" in context

    def test_to_dict_and_from_dict_roundtrip(self, sample_taste_profile):
        """Test serialization roundtrip"""
        from src.models.user import TasteProfile
        
        original = TasteProfile.from_dict(sample_taste_profile)
        serialized = original.to_dict()
        restored = TasteProfile.from_dict(serialized)
        
        assert restored.top_artists == original.top_artists
        assert restored.preferred_energy == original.preferred_energy


class TestWorkflowExecution:
    """Tests for WorkflowExecution model"""

    def test_workflow_lifecycle(self):
        """Test workflow start, step, complete lifecycle"""
        from src.models.workflow import WorkflowExecution, WorkflowStatus
        
        workflow = WorkflowExecution(
            workflow_id="test-123",
            workflow_type="playlist_generation",
        )
        
        assert workflow.status == WorkflowStatus.PENDING
        
        workflow.start()
        assert workflow.status == WorkflowStatus.RUNNING
        assert workflow.started_at is not None
        
        step = workflow.add_step("fetch_data")
        assert len(workflow.steps) == 1
        assert step.status == WorkflowStatus.RUNNING
        
        step.complete({"tracks_fetched": 50})
        assert step.status == WorkflowStatus.COMPLETED
        
        workflow.complete({"playlist_id": "new_playlist"})
        assert workflow.status == WorkflowStatus.COMPLETED
        assert workflow.is_successful

    def test_workflow_failure(self):
        """Test workflow failure handling"""
        from src.models.workflow import WorkflowExecution, WorkflowStatus
        
        workflow = WorkflowExecution(
            workflow_id="test-456",
            workflow_type="playlist_generation",
        )
        
        workflow.start()
        step = workflow.add_step("api_call")
        step.fail("API error")
        workflow.fail("Workflow failed at api_call", "api_call")
        
        assert workflow.status == WorkflowStatus.FAILED
        assert workflow.error == "Workflow failed at api_call"
        assert not workflow.is_successful

    def test_to_dict_serialization(self):
        """Test workflow serialization"""
        from src.models.workflow import WorkflowExecution
        
        workflow = WorkflowExecution(
            workflow_id="test-789",
            workflow_type="feedback_learning",
            parameters={"mood": "happy"},
        )
        workflow.start()
        workflow.complete()
        
        data = workflow.to_dict()
        
        assert isinstance(data, dict)
        assert data["workflow_id"] == "test-789"
        assert data["status"] == "completed"
