#!/usr/bin/env python3
"""
Test script to demonstrate the difference between traditional and LLM-driven workflows
"""

import sys
import os
from datetime import datetime

def test_workflows():
    """Compare traditional vs LLM-driven workflow architectures"""
    
    print("=" * 80)
    print("WORKFLOW ARCHITECTURE COMPARISON")
    print("=" * 80)
    
    # Test imports
    try:
        from src.workflow import MultiAgentWorkflow
        from src.llm_driven_workflow import LLMDrivenWorkflow
        print("✅ Both workflows imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return
    
    print("\n" + "=" * 80)
    print("TRADITIONAL WORKFLOW (Current Implementation)")
    print("=" * 80)
    
    print("""
    Architecture Flow:
    1. Get user data from Spotify
    2. Generate candidates using SVD collaborative filtering
    3. Apply keyword/language filters
    4. LLM enhances the pre-selected tracks (POST-PROCESSING)
    5. Create final playlist
    
    Key Characteristics:
    - SVD/Collaborative filtering drives candidate generation
    - LLM acts as a filter/enhancer at the END
    - User history is PRIMARY signal
    - Mood/context are SECONDARY signals
    """)
    
    print("\n" + "=" * 80)
    print("LLM-DRIVEN WORKFLOW (Proposed Alternative)")
    print("=" * 80)
    
    print("""
    Architecture Flow:
    1. LLM analyzes mood/context/keywords FIRST
    2. LLM generates semantic search strategy (genres, features, queries)
    3. Execute targeted Spotify searches based on LLM strategy
    4. Score tracks using LLM-derived features + user preferences
    5. LLM makes final selection with flow consideration
    
    Key Characteristics:
    - LLM understanding drives candidate generation from START
    - Search queries are mood/context-specific
    - User history is SECONDARY (for personalization)
    - Mood/context are PRIMARY signals
    """)
    
    print("\n" + "=" * 80)
    print("EXAMPLE: 'Sad Studying' Playlist")
    print("=" * 80)
    
    print("\n📌 TRADITIONAL APPROACH:")
    print("""
    1. SVD looks at user's top tracks → finds similar tracks
    2. Gets mix of genres user has listened to
    3. Filters for "studying" (maybe removes high-energy)
    4. LLM adds description: "Good for studying"
    
    Result: User's usual music, slightly filtered
    """)
    
    print("\n📌 LLM-DRIVEN APPROACH:")
    print("""
    1. LLM analyzes "Sad + Studying" →
       - Genres: ['lo-fi', 'ambient', 'neo-classical', 'indie folk']
       - Energy: 0.1-0.3, Valence: 0.2-0.4, Tempo: 60-90 BPM
       - Queries: ['sad study music', 'melancholic instrumental', 'rainy day lo-fi']
    2. Searches Spotify specifically for these characteristics
    3. Gets tracks that ACTUALLY match sad studying vibe
    4. Personalizes with user preferences (secondary)
    
    Result: Tracks specifically suited for sad studying mood
    """)
    
    print("\n" + "=" * 80)
    print("KEY DIFFERENCES")
    print("=" * 80)
    
    print("""
    1. CANDIDATE GENERATION:
       Traditional: Based on user history similarity
       LLM-Driven: Based on mood/context understanding
    
    2. LLM ROLE:
       Traditional: Post-processor (enhances pre-selected tracks)
       LLM-Driven: Primary driver (generates search strategy)
    
    3. PERSONALIZATION:
       Traditional: Dominant (everything based on user history)
       LLM-Driven: Secondary (applied after mood-based selection)
    
    4. DISCOVERY:
       Traditional: Limited (mostly user's bubble)
       LLM-Driven: High (finds new music matching mood)
    
    5. CONTEXT SENSITIVITY:
       Traditional: Low (context is afterthought)
       LLM-Driven: High (context drives everything)
    """)
    
    print("\n" + "=" * 80)
    print("TESTING THE NEW WORKFLOW")
    print("=" * 80)
    
    try:
        # Initialize LLM-driven workflow
        print("\n🔧 Initializing LLM-driven workflow...")
        llm_workflow = LLMDrivenWorkflow()
        print("✅ LLM-driven workflow initialized")
        
        # Test search strategy generation
        print("\n🧪 Testing search strategy generation for 'Energetic Exercising'...")
        
        # Simulate the internal call
        strategy = llm_workflow._generate_llm_search_strategy(
            mood="Energetic",
            activity="Exercising", 
            user_context="Morning workout at the gym",
            language_preference="English",
            keywords=None
        )
        
        print("\n📊 Generated Search Strategy:")
        print(f"Genres: {strategy.get('genres', [])}")
        print(f"Audio Features: {strategy.get('audio_features', {})}")
        print(f"Search Queries: {strategy.get('search_queries', [])[:5]}")
        print(f"Themes: {strategy.get('themes', [])}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("IMPLEMENTATION NOTES")
    print("=" * 80)
    
    print("""
    To use the LLM-driven workflow in the app:
    
    1. Import in app.py:
       from src.llm_driven_workflow import LLMDrivenWorkflow
    
    2. Add workflow selector in UI:
       workflow_mode = st.selectbox("Workflow Mode", 
           ["Traditional (User-History Based)", "LLM-Driven (Mood-First)"])
    
    3. Execute based on selection:
       if workflow_mode == "LLM-Driven (Mood-First)":
           workflow = LLMDrivenWorkflow()
           result = workflow.execute_playlist_generation(...)
       else:
           workflow = MultiAgentWorkflow()
           result = workflow.execute_workflow('playlist_generation', ...)
    
    4. Benefits for users:
       - Better mood matching
       - More music discovery
       - Context-aware selections
       - Less repetitive playlists
    """)
    
    print("\n✅ Workflow comparison complete!")
    return True

if __name__ == "__main__":
    test_workflows()
