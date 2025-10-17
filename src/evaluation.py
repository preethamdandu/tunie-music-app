# Offline Evaluation Utilities for TuneGenie
# Measures whether LLM-improved playlists better match a user prompt

from __future__ import annotations

import math
from typing import List, Dict, Tuple, Optional

# Note: we depend on SpotifyClient for audio features and optional genre hints via artist info
from .spotify_client import SpotifyClient


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two equal-length vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _feature_vector_from_audio_features(features: Dict) -> List[float]:
    """Create a numeric vector from Spotify audio features.
    Chosen fields are stable across the API and capture mood/energy reasonably well.
    """
    if not features:
        return [0.0] * 7
    return [
        float(features.get('danceability', 0.0)),
        float(features.get('energy', 0.0)),
        float(features.get('valence', 0.0)),
        float(features.get('acousticness', 0.0)),
        float(features.get('instrumentalness', 0.0)),
        float(features.get('liveness', 0.0)),
        float(features.get('speechiness', 0.0)),
    ]


def _prompt_to_target_vector(prompt: str) -> List[float]:
    """Very lightweight heuristic to map a prompt to target audio profile.
    This avoids external embeddings and keeps evaluation deterministic offline.
    """
    p = (prompt or '').lower()
    # Defaults: neutral
    target = {
        'danceability': 0.5,
        'energy': 0.5,
        'valence': 0.5,
        'acousticness': 0.3,
        'instrumentalness': 0.2,
        'liveness': 0.2,
        'speechiness': 0.1,
    }
    if 'sad' in p or 'melanch' in p:
        target['valence'] = 0.2
        target['energy'] = 0.3
        target['acousticness'] = 0.5
        target['instrumentalness'] = 0.3
    if 'happy' in p or 'uplift' in p:
        target['valence'] = 0.8
        target['energy'] = max(target['energy'], 0.6)
        target['danceability'] = 0.6
    if 'indie' in p:
        target['acousticness'] = max(target['acousticness'], 0.4)
    if 'lo-fi' in p or 'lofi' in p:
        target['energy'] = min(target['energy'], 0.4)
        target['instrumentalness'] = max(target['instrumentalness'], 0.4)
    if 'workout' in p or 'exercise' in p:
        target['energy'] = 0.8
        target['danceability'] = 0.7
        target['valence'] = max(target['valence'], 0.6)
    if 'study' in p or 'focus' in p:
        target['energy'] = min(target['energy'], 0.4)
        target['instrumentalness'] = max(target['instrumentalness'], 0.4)
        target['speechiness'] = 0.05
    return _feature_vector_from_audio_features(target)


def _average_pairwise_similarity(vectors: List[List[float]]) -> float:
    """Cohesion = mean pairwise cosine similarity among vectors (internal consistency)."""
    if not vectors:
        return 0.0
    n = len(vectors)
    if n == 1:
        return 1.0
    total = 0.0
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += _cosine_similarity(vectors[i], vectors[j])
            count += 1
    return total / count if count else 0.0


def compute_cohesion_score(prompt: str,
                           raw_svd_tracks: List[Dict],
                           llm_tracks: List[Dict],
                           spotify_client: Optional[SpotifyClient] = None,
                           per_list_track_limit: int = 30) -> Dict[str, float]:
    """
    Offline evaluation comparing raw SVD vs LLM-refined lists.

    Scoring dimensions:
    - internal_cohesion: average pairwise similarity among tracks' audio feature vectors
    - target_alignment: similarity between list centroid and a prompt-derived target vector
    - overall: weighted sum = 0.6*internal_cohesion + 0.4*target_alignment

    Inputs:
    - prompt: user intent (e.g., "sad indie music")
    - raw_svd_tracks: list of dicts with at least 'id' or 'track_id'
    - llm_tracks: list of dicts with at least 'id' or 'track_id'
    - spotify_client: optional; if None, instantiate a new one
    - per_list_track_limit: cap tracks per list for speed

    Returns:
    { 'svd_internal': x, 'svd_alignment': y, 'svd_overall': z,
      'llm_internal': a, 'llm_alignment': b, 'llm_overall': c,
      'improvement_overall': c - z }
    """
    client = spotify_client or SpotifyClient()

    def _extract_ids(tracks: List[Dict]) -> List[str]:
        ids: List[str] = []
        for t in tracks[:per_list_track_limit]:
            tid = t.get('track_id') or t.get('id')
            if isinstance(tid, str):
                ids.append(tid)
        return ids

    def _features_for_ids(ids: List[str]) -> List[List[float]]:
        if not ids:
            return []
        feats = client.get_track_features(ids)
        vectors: List[List[float]] = []
        for f in feats:
            vectors.append(_feature_vector_from_audio_features(f or {}))
        return vectors

    # Prepare feature vectors
    svd_ids = _extract_ids(raw_svd_tracks)
    llm_ids = _extract_ids(llm_tracks)

    svd_vecs = _features_for_ids(svd_ids)
    llm_vecs = _features_for_ids(llm_ids)

    # Compute internal cohesion
    svd_internal = _average_pairwise_similarity(svd_vecs)
    llm_internal = _average_pairwise_similarity(llm_vecs)

    # Compute alignment with prompt target vector
    target_vec = _prompt_to_target_vector(prompt)

    def _centroid(vectors: List[List[float]]) -> List[float]:
        if not vectors:
            return [0.0] * len(target_vec)
        dim = len(vectors[0])
        sums = [0.0] * dim
        for v in vectors:
            for i in range(dim):
                sums[i] += v[i]
        return [s / len(vectors) for s in sums]

    svd_centroid = _centroid(svd_vecs)
    llm_centroid = _centroid(llm_vecs)

    svd_alignment = _cosine_similarity(svd_centroid, target_vec)
    llm_alignment = _cosine_similarity(llm_centroid, target_vec)

    # Combine
    def _overall(internal: float, align: float) -> float:
        return 0.6 * internal + 0.4 * align

    svd_overall = _overall(svd_internal, svd_alignment)
    llm_overall = _overall(llm_internal, llm_alignment)

    return {
        'svd_internal': round(svd_internal, 4),
        'svd_alignment': round(svd_alignment, 4),
        'svd_overall': round(svd_overall, 4),
        'llm_internal': round(llm_internal, 4),
        'llm_alignment': round(llm_alignment, 4),
        'llm_overall': round(llm_overall, 4),
        'improvement_overall': round(llm_overall - svd_overall, 4),
    }
