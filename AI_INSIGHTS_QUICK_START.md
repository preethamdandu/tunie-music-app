# AI Insights Enhancement - Quick Start Guide

## 🚀 Quick Integration (5 Minutes)

### Step 1: Import New Components

Add to `src/llm_agent.py`:

```python
from src.reasoning_engine import ReasoningEngine
from src.music_toolkit import MusicToolkit
from src.memory_system import MemorySystem
```

### Step 2: Initialize in LLMAgent

```python
class LLMAgent:
    def __init__(self, model_name: str = "auto", temperature: float = 0.7):
        # ... existing code ...
        
        # NEW: Initialize enhanced components
        self.reasoning_engine = None  # Lazy init
        self.toolkit = None  # Lazy init
        self.memory_systems = {}  # Per-user memory
    
    def _init_enhanced_features(self, spotify_client):
        """Initialize enhanced features (call once)"""
        if self.reasoning_engine is None:
            self.reasoning_engine = ReasoningEngine(self, spotify_client)
        if self.toolkit is None:
            self.toolkit = MusicToolkit(spotify_client, self)
    
    def _get_user_memory(self, user_id: str) -> MemorySystem:
        """Get or create memory system for user"""
        if user_id not in self.memory_systems:
            self.memory_systems[user_id] = MemorySystem(user_id)
        return self.memory_systems[user_id]
```

### Step 3: Add Enhanced Method

```python
def get_music_insights_enhanced(self, question: str, user_id: str, 
                               context: Dict, spotify_client=None,
                               show_reasoning: bool = True) -> Dict:
    """
    Enhanced insights with reasoning, tools, and memory
    
    Args:
        question: User's question
        user_id: User identifier
        context: User context data
        spotify_client: Spotify client for tools
        show_reasoning: Whether to include reasoning steps
    
    Returns:
        Dict with response, reasoning, confidence, sources
    """
    try:
        # Initialize enhanced features
        if spotify_client:
            self._init_enhanced_features(spotify_client)
        
        # Get user memory
        memory = self._get_user_memory(user_id)
        
        # Add question to short-term memory
        memory.short_term.add('user', question)
        
        # Get conversation history for context
        conversation_history = [
            {'role': msg['role'], 'content': msg['content']}
            for msg in memory.short_term.get_recent(5)
        ]
        
        # Use reasoning engine if available
        if self.reasoning_engine:
            result = self.reasoning_engine.reason_about_query(
                query=question,
                context=context,
                show_reasoning=show_reasoning
            )
        else:
            # Fallback to standard insights
            result = self.get_music_insights(
                question=question,
                user_context=str(context),
                conversation_history=conversation_history
            )
            result = {
                'response': result.get('insight', result.get('answer', 'No response')),
                'confidence': 0.7,
                'sources': ['llm'],
                'reasoning_steps': []
            }
        
        # Add response to memory
        memory.short_term.add('assistant', result['response'])
        
        # Learn from interaction
        memory.long_term.add_interaction(
            interaction_type='ai_insights_query',
            details={
                'query': question,
                'response_length': len(result['response']),
                'confidence': result.get('confidence', 0),
                'reasoning_type': result.get('reasoning_type', 'standard')
            }
        )
        
        # Add memory context to result
        result['memory_stats'] = memory.get_context_summary()
        
        return result
        
    except Exception as e:
        logger.error(f"Enhanced insights failed: {e}")
        # Fallback to standard method
        return {
            'response': f"I encountered an issue: {str(e)}",
            'confidence': 0.0,
            'sources': [],
            'reasoning_steps': [],
            'error': str(e)
        }
```

### Step 4: Update UI (app.py)

Replace the AI Insights button handler:

```python
if st.button("🎵 Get AI Insights", key="get_insights"):
    with st.spinner("🧠 Analyzing your question..."):
        try:
            # Get user ID
            user_profile = workflow.spotify_client.get_user_profile()
            user_id = user_profile.get('id', 'anonymous')
            
            # Get user context
            user_context_dict = {
                'top_artists': workflow.spotify_client.get_user_top_artists(20),
                'top_tracks': workflow.spotify_client.get_user_top_tracks(20),
                'profile': user_profile
            }
            
            # Get enhanced insights
            result = workflow.llm_agent.get_music_insights_enhanced(
                question=user_query,
                user_id=user_id,
                context=user_context_dict,
                spotify_client=workflow.spotify_client,
                show_reasoning=True
            )
            
            # Display response
            st.markdown("### 💡 AI Response")
            st.markdown(result['response'])
            
            # Show reasoning steps (collapsible)
            if result.get('reasoning_steps'):
                with st.expander("🧠 View Reasoning Process", expanded=False):
                    for step in result['reasoning_steps']:
                        st.markdown(f"**Step {step['step']}: {step['action']}**")
                        st.markdown(step['description'])
            
            # Show confidence and sources
            col1, col2 = st.columns(2)
            with col1:
                confidence = result.get('confidence', 0) * 100
                st.metric("Confidence", f"{confidence:.0f}%")
            with col2:
                sources = ', '.join(result.get('sources', ['unknown']))
                st.caption(f"📚 Sources: {sources}")
            
            # Show memory stats
            if result.get('memory_stats'):
                with st.expander("🧠 Memory Stats", expanded=False):
                    st.json(result['memory_stats'])
                    
        except Exception as e:
            st.error(f"Failed to get insights: {str(e)}")
```

---

## 🎯 Feature Flags (Gradual Rollout)

Add to your `.env` or config:

```bash
# Feature flags for AI Insights enhancements
AI_INSIGHTS_REASONING_ENABLED=true
AI_INSIGHTS_TOOLS_ENABLED=true
AI_INSIGHTS_MEMORY_ENABLED=true
AI_INSIGHTS_SHOW_REASONING=true
```

Use in code:

```python
import os

# Check feature flags
REASONING_ENABLED = os.getenv('AI_INSIGHTS_REASONING_ENABLED', 'false').lower() == 'true'
TOOLS_ENABLED = os.getenv('AI_INSIGHTS_TOOLS_ENABLED', 'false').lower() == 'true'
MEMORY_ENABLED = os.getenv('AI_INSIGHTS_MEMORY_ENABLED', 'false').lower() == 'true'

# Use enhanced features only if enabled
if REASONING_ENABLED:
    result = llm_agent.get_music_insights_enhanced(...)
else:
    result = llm_agent.get_music_insights(...)
```

---

## 🧪 Testing Your Integration

### Test 1: Basic Reasoning

```python
# test_enhanced_insights.py
from src.llm_agent import LLMAgent
from src.workflow import MultiAgentWorkflow

def test_basic_reasoning():
    workflow = MultiAgentWorkflow()
    
    result = workflow.llm_agent.get_music_insights_enhanced(
        question="Why do I like hip-hop?",
        user_id="test_user",
        context={'top_genres': ['hip-hop', 'rap']},
        spotify_client=workflow.spotify_client
    )
    
    assert 'response' in result
    assert 'confidence' in result
    assert result['confidence'] > 0
    print(f"✅ Basic reasoning test passed")
    print(f"Response: {result['response'][:100]}...")
```

### Test 2: Tool Usage

```python
def test_tool_usage():
    from src.music_toolkit import MusicToolkit
    
    toolkit = MusicToolkit(spotify_client)
    
    # Test search
    tracks = toolkit.execute_tool('search_tracks', {
        'query': 'Drake',
        'limit': 5
    })
    
    assert len(tracks) > 0
    print(f"✅ Tool usage test passed")
    print(f"Found {len(tracks)} tracks")
```

### Test 3: Memory Persistence

```python
def test_memory_persistence():
    from src.memory_system import MemorySystem
    
    # Create memory
    memory = MemorySystem('test_user_123')
    
    # Remember something
    memory.remember('favorite_genre', 'jazz', confidence=0.9)
    
    # Create new instance (simulates new session)
    memory2 = MemorySystem('test_user_123')
    
    # Recall
    prefs = memory2.recall('favorite_genre')
    
    assert len(prefs) > 0
    assert prefs[0]['value'] == 'jazz'
    print(f"✅ Memory persistence test passed")
```

---

## 📊 Monitoring & Analytics

### Add Logging

```python
import logging

logger = logging.getLogger(__name__)

# Log enhanced insights usage
logger.info(f"Enhanced insights query: {question[:50]}...")
logger.info(f"Reasoning type: {result.get('reasoning_type')}")
logger.info(f"Confidence: {result.get('confidence')}")
logger.info(f"Tools used: {len(toolkit.get_tool_call_history())}")
```

### Track Metrics

```python
# Add to your analytics
metrics = {
    'enhanced_insights_queries': 0,
    'reasoning_steps_shown': 0,
    'tools_called': 0,
    'avg_confidence': 0.0,
    'memory_interactions': 0
}

# Update after each query
metrics['enhanced_insights_queries'] += 1
metrics['reasoning_steps_shown'] += len(result.get('reasoning_steps', []))
metrics['avg_confidence'] = (
    (metrics['avg_confidence'] * (metrics['enhanced_insights_queries'] - 1) + 
     result.get('confidence', 0)) / metrics['enhanced_insights_queries']
)
```

---

## 🐛 Troubleshooting

### Issue: "ReasoningEngine not found"
**Solution**: Ensure `src/reasoning_engine.py` is in your Python path

```python
import sys
sys.path.append('src')
from reasoning_engine import ReasoningEngine
```

### Issue: "Memory file not found"
**Solution**: Create data directory

```bash
mkdir -p data/memory
```

### Issue: "Tool execution failed"
**Solution**: Check Spotify client initialization

```python
if not spotify_client or not spotify_client.sp:
    logger.warning("Spotify client not available, tools disabled")
    toolkit = None
```

### Issue: "Reasoning takes too long"
**Solution**: Add timeout

```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Reasoning timeout")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(10)  # 10 second timeout

try:
    result = reasoning_engine.reason_about_query(...)
finally:
    signal.alarm(0)  # Cancel timeout
```

---

## 🎨 UI Customization

### Custom Reasoning Display

```python
def display_reasoning_steps(steps: List[Dict]):
    """Custom reasoning step display"""
    for i, step in enumerate(steps, 1):
        with st.container():
            st.markdown(f"### Step {i}: {step['action']}")
            st.markdown(step['description'])
            
            # Progress bar
            progress = i / len(steps)
            st.progress(progress)
            
            # Expandable details
            if 'data' in step:
                with st.expander("View Details"):
                    st.json(step['data'])
```

### Confidence Visualization

```python
def display_confidence(confidence: float):
    """Visual confidence indicator"""
    color = 'green' if confidence > 0.8 else 'orange' if confidence > 0.6 else 'red'
    
    st.markdown(f"""
    <div style="
        background: {color};
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    ">
        <h3 style="color: white; margin: 0;">
            {confidence*100:.0f}% Confident
        </h3>
    </div>
    """, unsafe_allow_html=True)
```

---

## 📚 Additional Resources

- **Full Enhancement Plan**: `AI_INSIGHTS_ENHANCEMENT_PLAN.md`
- **Implementation Summary**: `AI_INSIGHTS_IMPLEMENTATION_SUMMARY.md`
- **Source Code**:
  - Reasoning Engine: `src/reasoning_engine.py`
  - Music Toolkit: `src/music_toolkit.py`
  - Memory System: `src/memory_system.py`

---

## 🎯 Next Steps

1. ✅ **Test Integration**: Run the test functions above
2. ✅ **Enable Features**: Set feature flags to `true`
3. ✅ **Monitor Performance**: Track metrics and logs
4. ✅ **Gather Feedback**: A/B test with users
5. ✅ **Iterate**: Improve based on feedback

---

**Questions?** Check the full documentation in `AI_INSIGHTS_ENHANCEMENT_PLAN.md`

**Ready to deploy?** Follow the integration steps above and you're good to go! 🚀
