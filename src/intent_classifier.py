"""
Intent classifier for selecting recommendation strategy based on user keywords.

- If any normalized segment of the keywords exactly matches a curated lexicon
  entry, we pick the 'niche_query' strategy.
- Otherwise, we fall back to the feature-flag-defined default: 'llm_driven' when
  FEATURE_FLAG_LLM_DRIVEN is truthy, else 'cf_first'.
"""

import os
from typing import List


class IntentClassifier:
    def __init__(self):
        # Curated minimal lexicon of entities and niche indicators
        # All entries are stored normalized (lowercase, stripped)
        self.lexicon = {
            'bad bunny',
            'the weeknd',
            'synthpop',
            'khöömei',  # Mongolian throat singing
            # Expanded popular artists for robust entity recognition
            'drake',
            'kendrick lamar',
            'billie eilish',
            'taylor swift',
            'ed sheeran',
            'ariana grande',
            'dua lipa',
            'the beatles',
            'queen',
            'coldplay',
            'post malone',
            'eminem',
            'rihanna',
            'lady gaga',
            'bruno mars',
            'beyoncé',
            'jay-z',
            'adele',
            'justin bieber',
            'the rolling stones',
            'metallica',
            'pink floyd',
            'imagine dragons',
            'weeknd',  # common miss without 'the'
            'badbunny',  # common misspelling without space
        }

    def _normalize_segments(self, keywords: str) -> List[str]:
        if not keywords:
            return []
        text = (keywords or '').lower()
        # Split primarily by commas; trim and remove known prefixes like artist:, title:, album:, genre:
        raw_parts = [p.strip() for p in text.split(',') if p.strip()]
        cleaned_parts: List[str] = []
        prefixes = ('artist:', 'title:', 'track:', 'album:', 'genre:')
        for part in raw_parts:
            cleaned = part
            for pref in prefixes:
                if cleaned.startswith(pref):
                    cleaned = cleaned[len(pref):].strip()
                    break
            if cleaned:
                cleaned_parts.append(cleaned)
        # If no commas were used, consider the whole string as a single segment
        if not cleaned_parts and text:
            cleaned_parts = [text.strip()]
        return cleaned_parts

    def _default_strategy(self) -> str:
        flag = os.getenv('FEATURE_FLAG_LLM_DRIVEN', 'False').strip().lower() in ('1', 'true', 'yes', 'on')
        return 'llm_driven' if flag else 'cf_first'

    def classify(self, keywords: str) -> str:
        segments = self._normalize_segments(keywords)
        for seg in segments:
            if seg in self.lexicon:
                return 'niche_query'
        return self._default_strategy()


