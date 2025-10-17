from __future__ import annotations

from typing import Dict, List


class KeywordHandler:
    """
    Keyword expansion utility for niche musical intents.

    Proof-of-concept implementation that hard-codes expansion for
    'instrumental Mongolian throat-singing'. The contract is stable:
    - expand(query) -> { 'terms': List[str], 'instrumental': bool }
    """

    def expand(self, query: str) -> Dict[str, object]:
        """
        Expand a free-form query into canonical search terms and flags.

        Args:
            query: User's free-form query string.

        Returns:
            Dictionary with:
            - 'terms': list of canonical/synonym terms to search for
            - 'instrumental': boolean indicating instrumental requirement
        """
        if not isinstance(query, str) or not query.strip():
            return { 'terms': [], 'instrumental': False }

        normalized = query.strip().lower()

        # Detect instrumental intent (simple heuristic for PoC)
        instrumental = 'instrumental' in normalized

        # PoC: detect Mongolian throat-singing and expand to canonical terms/synonyms
        throat_related = (
            ('mongolian' in normalized and ('throat' in normalized or 'throat-singing' in normalized or 'throat singing' in normalized))
            or any(alias in normalized for alias in ['khöömei', 'khöömii', 'khoomei', 'overtone singing', 'tuvan'])
        )

        if throat_related:
            terms: List[str] = [
                'khöömei',
                'khöömii',
                'khoomei',
                'overtone singing',
                'tuvan',
                'mongolian folk',
                'mongolian throat singing',
            ]
            return { 'terms': terms, 'instrumental': instrumental }

        # Default: no special expansion; return the raw query as a single term
        return { 'terms': [query.strip()], 'instrumental': instrumental }


