"""
Advanced Memory System for TuneGenie AI Insights
Multi-tier memory: Short-term (session), Long-term (persistent), Semantic (knowledge graph)
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class MemorySystem:
    """Multi-tier memory system for personalization and learning"""
    
    def __init__(self, user_id: str):
        """
        Initialize memory system
        
        Args:
            user_id: Unique user identifier
        """
        self.user_id = user_id
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory(user_id)
        self.semantic = SemanticMemory()
    
    def remember(self, category: str, value: Any, confidence: float = 0.8, context: Dict = None):
        """
        Remember something across all memory tiers
        
        Args:
            category: Category of memory (preference, pattern, fact, etc.)
            value: The value to remember
            confidence: Confidence score (0-1)
            context: Additional context
        """
        # Add to short-term
        self.short_term.add('system', f"Learned: {category} = {value}")
        
        # Add to long-term if confidence is high
        if confidence >= 0.7:
            self.long_term.learn_preference(category, value, confidence)
        
        # Add to semantic if it's a relationship
        if context and 'relation' in context:
            self.semantic.add_relationship(
                entity1=context.get('entity1', category),
                relation=context.get('relation'),
                entity2=str(value)
            )
    
    def recall(self, category: str, limit: int = 10) -> List[Dict]:
        """
        Recall memories from long-term storage
        
        Args:
            category: Category to recall
            limit: Maximum number of memories
        
        Returns:
            List of memories
        """
        return self.long_term.get_preferences(category)[:limit]
    
    def get_context_summary(self) -> Dict:
        """Get a summary of all memory tiers"""
        return {
            'short_term': {
                'conversation_length': len(self.short_term.conversation_history),
                'recent_topics': self.short_term.get_recent_topics()
            },
            'long_term': {
                'total_preferences': len(self.long_term.memory.get('preferences', {})),
                'learned_patterns': len(self.long_term.memory.get('learned_patterns', {})),
                'interaction_count': len(self.long_term.memory.get('interaction_history', []))
            },
            'semantic': {
                'total_relationships': len(self.semantic.relationships),
                'entity_count': len(self.semantic.graph['artists']) + len(self.semantic.graph['genres'])
            }
        }


class ShortTermMemory:
    """Session-based conversation memory"""
    
    def __init__(self, context_window: int = 10):
        """
        Initialize short-term memory
        
        Args:
            context_window: Number of recent exchanges to keep
        """
        self.conversation_history = []
        self.context_window = context_window
        self.session_start = datetime.now()
        self.topics_discussed = set()
    
    def add(self, role: str, content: str, metadata: Dict = None):
        """
        Add a message to conversation history
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Additional metadata
        """
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        self.conversation_history.append(message)
        
        # Extract topics
        self._extract_topics(content)
    
    def get_recent(self, n: int = None) -> List[Dict]:
        """
        Get recent conversation history
        
        Args:
            n: Number of recent messages (default: context_window)
        
        Returns:
            List of recent messages
        """
        n = n or self.context_window
        return self.conversation_history[-n:]
    
    def get_recent_topics(self) -> List[str]:
        """Get recently discussed topics"""
        return list(self.topics_discussed)[-10:]
    
    def _extract_topics(self, content: str):
        """Extract topics from content"""
        # Simple keyword extraction
        music_keywords = [
            'artist', 'song', 'album', 'genre', 'playlist', 'music',
            'track', 'band', 'singer', 'rapper', 'producer'
        ]
        
        content_lower = content.lower()
        for keyword in music_keywords:
            if keyword in content_lower:
                self.topics_discussed.add(keyword)
    
    def clear(self):
        """Clear short-term memory"""
        self.conversation_history = []
        self.topics_discussed = set()
        self.session_start = datetime.now()
    
    def get_session_duration(self) -> float:
        """Get session duration in minutes"""
        duration = datetime.now() - self.session_start
        return duration.total_seconds() / 60


class LongTermMemory:
    """Persistent user preferences and patterns"""
    
    def __init__(self, user_id: str):
        """
        Initialize long-term memory
        
        Args:
            user_id: Unique user identifier
        """
        self.user_id = user_id
        self.db_path = f"data/memory/{user_id}.json"
        self.memory = self._load()
    
    def _load(self) -> Dict:
        """Load memory from disk"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load memory: {e}")
        
        # Initialize empty memory structure
        return {
            'user_id': self.user_id,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'preferences': {},
            'learned_patterns': {},
            'interaction_history': [],
            'favorite_genres': [],
            'disliked_genres': [],
            'favorite_artists': [],
            'mood_patterns': {},
            'activity_preferences': {},
            'listening_personality': {},
            'feedback_history': []
        }
    
    def save(self):
        """Save memory to disk"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self.memory['last_updated'] = datetime.now().isoformat()
            
            with open(self.db_path, 'w') as f:
                json.dump(self.memory, f, indent=2)
            
            logger.info(f"Memory saved for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def learn_preference(self, category: str, value: Any, confidence: float):
        """
        Learn a new preference with confidence scoring
        
        Args:
            category: Preference category
            value: Preference value
            confidence: Confidence score (0-1)
        """
        if category not in self.memory['preferences']:
            self.memory['preferences'][category] = []
        
        # Check if preference already exists
        existing = None
        for pref in self.memory['preferences'][category]:
            if pref['value'] == value:
                existing = pref
                break
        
        if existing:
            # Reinforce existing preference
            existing['reinforcement_count'] += 1
            existing['confidence'] = min(1.0, existing['confidence'] + 0.1)
            existing['last_reinforced'] = datetime.now().isoformat()
        else:
            # Add new preference
            self.memory['preferences'][category].append({
                'value': value,
                'confidence': confidence,
                'learned_at': datetime.now().isoformat(),
                'reinforcement_count': 1,
                'last_reinforced': datetime.now().isoformat()
            })
        
        self.save()
    
    def get_preferences(self, category: str) -> List[Dict]:
        """
        Get learned preferences for a category
        
        Args:
            category: Preference category
        
        Returns:
            List of preferences sorted by confidence
        """
        prefs = self.memory['preferences'].get(category, [])
        return sorted(prefs, key=lambda x: x['confidence'], reverse=True)
    
    def update_mood_pattern(self, mood: str, time_of_day: str, music_preferences: Dict):
        """
        Learn mood-based listening patterns
        
        Args:
            mood: User's mood
            time_of_day: Time of day (morning, afternoon, evening, night)
            music_preferences: Music preferences for this mood/time
        """
        key = f"{mood}_{time_of_day}"
        
        if key not in self.memory['mood_patterns']:
            self.memory['mood_patterns'][key] = {
                'count': 0,
                'preferences': [],
                'first_observed': datetime.now().isoformat()
            }
        
        self.memory['mood_patterns'][key]['count'] += 1
        self.memory['mood_patterns'][key]['preferences'].append({
            'timestamp': datetime.now().isoformat(),
            'preferences': music_preferences
        })
        self.memory['mood_patterns'][key]['last_observed'] = datetime.now().isoformat()
        
        self.save()
    
    def get_mood_pattern(self, mood: str, time_of_day: str) -> Optional[Dict]:
        """Get learned pattern for mood and time"""
        key = f"{mood}_{time_of_day}"
        return self.memory['mood_patterns'].get(key)
    
    def add_interaction(self, interaction_type: str, details: Dict):
        """
        Record an interaction
        
        Args:
            interaction_type: Type of interaction
            details: Interaction details
        """
        self.memory['interaction_history'].append({
            'type': interaction_type,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 1000 interactions
        if len(self.memory['interaction_history']) > 1000:
            self.memory['interaction_history'] = self.memory['interaction_history'][-1000:]
        
        self.save()
    
    def add_feedback(self, feedback_type: str, content: str, rating: float = None):
        """
        Record user feedback
        
        Args:
            feedback_type: Type of feedback (positive, negative, neutral)
            content: Feedback content
            rating: Optional rating (0-1)
        """
        self.memory['feedback_history'].append({
            'type': feedback_type,
            'content': content,
            'rating': rating,
            'timestamp': datetime.now().isoformat()
        })
        
        self.save()
    
    def get_listening_personality(self) -> Dict:
        """Get user's listening personality profile"""
        return self.memory.get('listening_personality', {})
    
    def update_listening_personality(self, traits: Dict):
        """
        Update listening personality traits
        
        Args:
            traits: Personality traits (e.g., explorer, curator, casual, enthusiast)
        """
        if 'listening_personality' not in self.memory:
            self.memory['listening_personality'] = {}
        
        self.memory['listening_personality'].update(traits)
        self.memory['listening_personality']['last_updated'] = datetime.now().isoformat()
        
        self.save()
    
    def get_statistics(self) -> Dict:
        """Get memory statistics"""
        return {
            'total_preferences': sum(len(prefs) for prefs in self.memory['preferences'].values()),
            'total_interactions': len(self.memory['interaction_history']),
            'total_feedback': len(self.memory['feedback_history']),
            'mood_patterns_learned': len(self.memory['mood_patterns']),
            'favorite_genres_count': len(self.memory['favorite_genres']),
            'favorite_artists_count': len(self.memory['favorite_artists']),
            'memory_age_days': (
                datetime.now() - datetime.fromisoformat(self.memory['created_at'])
            ).days
        }


class SemanticMemory:
    """Knowledge graph of music relationships"""
    
    def __init__(self):
        """Initialize semantic memory"""
        self.graph = {
            'artists': {},
            'genres': {},
            'tracks': {},
            'albums': {},
            'moods': {},
            'activities': {}
        }
        self.relationships = []
    
    def add_entity(self, entity_type: str, entity_id: str, properties: Dict):
        """
        Add an entity to the knowledge graph
        
        Args:
            entity_type: Type of entity (artist, genre, track, etc.)
            entity_id: Unique identifier
            properties: Entity properties
        """
        if entity_type not in self.graph:
            self.graph[entity_type] = {}
        
        self.graph[entity_type][entity_id] = {
            'id': entity_id,
            'properties': properties,
            'added_at': datetime.now().isoformat()
        }
    
    def add_relationship(self, entity1: str, relation: str, entity2: str, 
                        strength: float = 1.0, metadata: Dict = None):
        """
        Add a semantic relationship
        
        Args:
            entity1: First entity
            relation: Relationship type (similar_to, influenced_by, etc.)
            entity2: Second entity
            strength: Relationship strength (0-1)
            metadata: Additional metadata
        """
        relationship = {
            'from': entity1,
            'relation': relation,
            'to': entity2,
            'strength': strength,
            'metadata': metadata or {},
            'created_at': datetime.now().isoformat()
        }
        
        self.relationships.append(relationship)
    
    def query(self, entity: str, relation: str = None, limit: int = 10) -> List[Dict]:
        """
        Query the knowledge graph
        
        Args:
            entity: Entity to query
            relation: Optional relation filter
            limit: Maximum results
        
        Returns:
            List of matching relationships
        """
        results = []
        
        for rel in self.relationships:
            if rel['from'] == entity:
                if relation is None or rel['relation'] == relation:
                    results.append(rel)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_related_entities(self, entity: str, relation: str = None) -> List[str]:
        """
        Get entities related to a given entity
        
        Args:
            entity: Source entity
            relation: Optional relation filter
        
        Returns:
            List of related entity IDs
        """
        relationships = self.query(entity, relation)
        return [rel['to'] for rel in relationships]
    
    def find_path(self, start: str, end: str, max_depth: int = 3) -> Optional[List[str]]:
        """
        Find a path between two entities
        
        Args:
            start: Start entity
            end: End entity
            max_depth: Maximum path depth
        
        Returns:
            Path as list of entities, or None if no path found
        """
        # Simple BFS implementation
        queue = [(start, [start])]
        visited = {start}
        
        while queue:
            current, path = queue.pop(0)
            
            if len(path) > max_depth:
                continue
            
            if current == end:
                return path
            
            # Get related entities
            related = self.get_related_entities(current)
            
            for entity in related:
                if entity not in visited:
                    visited.add(entity)
                    queue.append((entity, path + [entity]))
        
        return None
    
    def get_statistics(self) -> Dict:
        """Get semantic memory statistics"""
        return {
            'total_entities': sum(len(entities) for entities in self.graph.values()),
            'total_relationships': len(self.relationships),
            'entity_types': {k: len(v) for k, v in self.graph.items()},
            'relationship_types': self._count_relationship_types()
        }
    
    def _count_relationship_types(self) -> Dict[str, int]:
        """Count relationships by type"""
        counts = defaultdict(int)
        for rel in self.relationships:
            counts[rel['relation']] += 1
        return dict(counts)
