import json
import logging
from typing import Dict, Any, List

from .llm_agent import LLMAgent

logger = logging.getLogger(__name__)


def _safe_default_profile() -> Dict[str, Any]:
    return {
        "preferred_genres": [],
        "sonic_profile": [],
        "lyrical_themes": [],
        "anti_preferences": [],
        "notes": "Default taste profile fallback due to unavailable LLM or parsing error."
    }


def _map_continuous_to_tags(energy: float, valence: float, acousticness: float) -> List[str]:
    tags: List[str] = []
    if energy >= 0.66:
        tags.append('high-energy')
    elif energy >= 0.33:
        tags.append('mid-energy')
    else:
        tags.append('low-energy')
    if valence >= 0.66:
        tags.append('upbeat')
    elif valence >= 0.33:
        tags.append('neutral')
    else:
        tags.append('dark')
    if acousticness >= 0.66:
        tags.append('acoustic')
    elif acousticness >= 0.33:
        tags.append('balanced')
    else:
        tags.append('produced')
    return tags


def _generate_heuristic_profile(user_spotify_data: dict) -> Dict[str, Any]:
    data = user_spotify_data or {}
    top_tracks = data.get("top_tracks", {}) or {}
    top_artists = data.get("top_artists", {}) or {}

    artist_lists = [
        *(top_artists.get("short_term", []) or []),
        *(top_artists.get("medium_term", []) or []),
        *(top_artists.get("long_term", []) or []),
    ]
    genre_counts: Dict[str, int] = {}
    for a in artist_lists:
        for g in (a.get("genres") or []):
            gnorm = str(g).strip().lower()
            if not gnorm:
                continue
            genre_counts[gnorm] = genre_counts.get(gnorm, 0) + 1
    top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    preferred_genres = [
        {"genre": g, "weight": round(c / max(1, sum(v for _, v in top_genres)), 3)}
        for g, c in top_genres
    ]

    def all_tracks() -> List[Dict[str, Any]]:
        return (
            (top_tracks.get("short_term", []) or [])
            + (top_tracks.get("medium_term", []) or [])
            + (top_tracks.get("long_term", []) or [])
        )

    tracks = all_tracks()
    sum_energy = sum_valence = sum_acoustic = 0.0
    feat_count = 0
    for t in tracks:
        feats = (t.get('audio_features') or {}) if isinstance(t, dict) else {}
        e = feats.get('energy'); v = feats.get('valence'); a = feats.get('acousticness')
        try:
            if isinstance(e, (int, float)) and isinstance(v, (int, float)) and isinstance(a, (int, float)):
                sum_energy += float(e); sum_valence += float(v); sum_acoustic += float(a)
                feat_count += 1
        except Exception:
            pass

    sonic_profile: List[str] = []
    if feat_count > 0:
        avg_e = sum_energy / feat_count
        avg_v = sum_valence / feat_count
        avg_a = sum_acoustic / feat_count
        sonic_profile = _map_continuous_to_tags(avg_e, avg_v, avg_a)

    return {
        "preferred_genres": preferred_genres,
        "sonic_profile": sonic_profile,
        "lyrical_themes": [],
        "anti_preferences": [],
        "_source": "heuristic",
        "notes": "LLM-generated profile was weak; using a heuristic profile instead."
    }


def generate_taste_profile(user_spotify_data: dict) -> dict:
    """
    Generate a structured Taste Profile for a user using the LLM as a world-class music analyst.

    The profile includes at minimum:
      - preferred_genres: list of {genre, weight} or plain strings
      - sonic_profile: list of descriptive sonic tags
      - lyrical_themes: list of common lyrical themes
      - anti_preferences: list of genres/qualities the user avoids

    Returns a dict; falls back to a safe default on any error.
    """
    try:
        # Prepare concise but rich context for the LLM
        data = user_spotify_data or {}
        profile = data.get("profile", {})
        top_tracks = data.get("top_tracks", {})
        top_artists = data.get("top_artists", {})
        recently_played = data.get("recently_played", [])
        playlists = data.get("playlists", [])

        # Trim large arrays for prompt efficiency while keeping enough signal
        def short(arr, n=100):
            try:
                return arr[:n]
            except Exception:
                return arr

        prompt_payload = {
            "user_profile": profile,
            "top_tracks": {
                "short_term": short(top_tracks.get("short_term", []), 75),
                "medium_term": short(top_tracks.get("medium_term", []), 75),
                "long_term": short(top_tracks.get("long_term", []), 75),
            },
            "top_artists": {
                "short_term": short(top_artists.get("short_term", []), 75),
                "medium_term": short(top_artists.get("medium_term", []), 75),
                "long_term": short(top_artists.get("long_term", []), 75),
            },
            "recently_played": short(recently_played, 100),
            "playlists": short(playlists, 50),
        }

        system_instructions = (
            "You are a world-class music analyst and personalization scientist. "
            "You will receive a Spotify user data bundle (profile, top tracks/artists across horizons, "
            "recently played, and saved playlists). Your job is to infer a rigorous, structured 'Taste Profile'.\n\n"
            "Rules:\n"
            "- Think step-by-step but RETURN ONLY a final JSON object.\n"
            "- Be conservative: when uncertain, include fewer inferences rather than hallucinating.\n"
            "- Prefer concrete genres/sub-genres and sonic attributes tied to evidence in the data.\n\n"
            "Output JSON schema (keys only, in this order):\n"
            "{\n"
            "  \"preferred_genres\": array // items can be strings or {genre, weight: 0-1},\n"
            "  \"sonic_profile\": array // e.g., 'acoustic', 'lo-fi', 'high-energy',\n"
            "  \"lyrical_themes\": array // e.g., 'love', 'protest', 'introspection',\n"
            "  \"anti_preferences\": array // disliked genres/qualities\n"
            "}"
        )

        user_message = (
            "Analyze the following Spotify user data and produce ONLY the JSON object described.\n\n"
            f"UserData JSON:\n{json.dumps(prompt_payload, ensure_ascii=False)}\n\n"
            "Return ONLY the JSON with the exact keys specified (no extra commentary)."
        )

        agent = LLMAgent()
        if getattr(agent, "model_type", "huggingface") == "openai":
            # Use the OpenAI chat for better structure
            from langchain.schema import SystemMessage, HumanMessage
            try:
                messages = [
                    SystemMessage(content=system_instructions),
                    HumanMessage(content=user_message),
                ]
                resp = agent.llm(messages)
                text = getattr(resp, "content", "") or getattr(resp, "text", "")
                parsed = json.loads(text)
                # Basic sanity
                parsed.setdefault("preferred_genres", [])
                parsed.setdefault("sonic_profile", [])
                parsed.setdefault("lyrical_themes", [])
                parsed.setdefault("anti_preferences", [])
                if not parsed.get("preferred_genres") and not parsed.get("sonic_profile"):
                    return _generate_heuristic_profile(user_spotify_data)
                return parsed
            except Exception as e:
                logger.warning(f"OpenAI taste profiling failed, falling back: {e}")
        else:
            # Hugging Face inference API (text completion)
            import requests
            try:
                payload = {
                    "inputs": f"System:\n{system_instructions}\n\nUser:\n{user_message}\n\nAssistant:"  # steer towards JSON
                }
                response = requests.post(getattr(agent, "model_url", ""), headers=getattr(agent, "headers", {}), json=payload, timeout=15)
                text = ""
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and result:
                        text = result[0].get("generated_text") or result[0].get("text") or str(result[0])
                    elif isinstance(result, dict):
                        text = result.get("generated_text") or result.get("text") or str(result)
                # Try parse JSON substring
                try:
                    start = text.find("{")
                    end = text.rfind("}")
                    json_str = text[start:end + 1] if start != -1 and end != -1 else ""
                    parsed = json.loads(json_str) if json_str else {}
                    parsed.setdefault("preferred_genres", [])
                    parsed.setdefault("sonic_profile", [])
                    parsed.setdefault("lyrical_themes", [])
                    parsed.setdefault("anti_preferences", [])
                    if parsed:
                        if not parsed.get("preferred_genres") and not parsed.get("sonic_profile"):
                            return _generate_heuristic_profile(user_spotify_data)
                        return parsed
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"Hugging Face taste profiling failed: {e}")

        # Final fallback
        return _generate_heuristic_profile(user_spotify_data)
    except Exception as e:
        logger.error(f"generate_taste_profile failed: {e}")
        return _safe_default_profile()
