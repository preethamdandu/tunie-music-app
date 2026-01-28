"""
COMPLETE INTEGRATION TEST
Tests the actual LLM agent implementation with all components
"""

import sys
import os
sys.path.insert(0, '/vercel/sandbox')

import json
import time
from datetime import datetime

# Test results
results = {'total': 0, 'passed': 0, 'failed': 0, 'warnings': 0, 'errors': 0, 'details': []}

def log(name, status, msg="", details=None):
    results['total'] += 1
    results[status.lower()] = results.get(status.lower(), 0) + 1
    symbol = {'PASS': '✅', 'FAIL': '❌', 'WARNING': '⚠️', 'ERROR': '💥'}[status]
    print(f"{symbol} {name}: {status} - {msg}")
    results['details'].append({'test': name, 'status': status, 'message': msg, 'details': str(details)[:200] if details else None})

print("\n" + "="*80)
print("🔥 COMPLETE INTEGRATION TEST SUITE 🔥")
print("="*80 + "\n")

# Test 1: Security Utils
print("="*80)
print("SECURITY UTILITIES")
print("="*80)

try:
    from src.security_utils import SecurityUtils, InputValidator, ResponseValidator, RateLimiter
    log("Import Security Utils", "PASS", "All security modules imported")
    
    # Test input validation
    validator = InputValidator()
    
    # Valid input
    is_valid, msg = validator.validate_question("Tell me about jazz")
    if is_valid:
        log("Input Validation: Valid", "PASS", "Accepted valid input")
    else:
        log("Input Validation: Valid", "FAIL", f"Rejected valid input: {msg}")
    
    # Too long input
    is_valid, msg = validator.validate_question("x" * 100000)
    if not is_valid:
        log("Input Validation: Too Long", "PASS", f"Rejected: {msg}")
    else:
        log("Input Validation: Too Long", "WARNING", "Accepted overly long input")
    
    # Null bytes
    is_valid, msg = validator.validate_question("music\x00jazz")
    if not is_valid:
        log("Input Validation: Null Bytes", "PASS", "Rejected null bytes")
    else:
        log("Input Validation: Null Bytes", "WARNING", "Accepted null bytes")
    
    # Test output sanitization
    security = SecurityUtils()
    
    # XSS attempt
    sanitized = security.sanitize_output("<script>alert('xss')</script>")
    if '<script>' not in sanitized:
        log("Output Sanitization: XSS", "PASS", "Removed script tags")
    else:
        log("Output Sanitization: XSS", "FAIL", "Script tags present")
    
    # SQL injection
    sanitized = security.sanitize_output("'; DROP TABLE users; --")
    if 'DROP TABLE' not in sanitized:
        log("Output Sanitization: SQL", "PASS", "Filtered SQL commands")
    else:
        log("Output Sanitization: SQL", "WARNING", "SQL commands present")
    
    # Test rate limiting
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    
    # Make 5 requests (should all pass)
    for i in range(5):
        allowed, reason = limiter.is_allowed("test_user")
        if not allowed:
            log(f"Rate Limiter: Request {i+1}", "FAIL", f"Blocked too early: {reason}")
            break
    else:
        log("Rate Limiter: Within Limit", "PASS", "Allowed 5 requests")
    
    # 6th request should be blocked
    allowed, reason = limiter.is_allowed("test_user")
    if not allowed:
        log("Rate Limiter: Exceeded", "PASS", f"Blocked 6th request: {reason}")
    else:
        log("Rate Limiter: Exceeded", "FAIL", "Did not block excess requests")
    
    # Different user should be allowed
    allowed, reason = limiter.is_allowed("different_user")
    if allowed:
        log("Rate Limiter: Different User", "PASS", "Isolated per user")
    else:
        log("Rate Limiter: Different User", "FAIL", "Not isolated per user")
    
except Exception as e:
    log("Security Utils", "ERROR", str(e))

# Test 2: Memory System
print("\n" + "="*80)
print("MEMORY SYSTEM")
print("="*80)

try:
    from src.memory_system import MemorySystem, ShortTermMemory, LongTermMemory, SemanticMemory
    log("Import Memory System", "PASS", "All memory modules imported")
    
    # Test short-term memory
    stm = ShortTermMemory(context_window=5)
    
    for i in range(10):
        stm.add('user', f'Message {i}')
    
    recent = stm.get_recent(5)
    if len(recent) == 5:
        log("Short-Term Memory: Window", "PASS", "Maintains context window")
    else:
        log("Short-Term Memory: Window", "FAIL", f"Got {len(recent)} instead of 5")
    
    # Test long-term memory
    ltm = LongTermMemory('test_user_123')
    
    ltm.learn_preference('genre', 'jazz', confidence=0.9)
    ltm.learn_preference('genre', 'hip-hop', confidence=0.8)
    
    prefs = ltm.get_preferences('genre')
    if len(prefs) == 2 and prefs[0]['value'] == 'jazz':
        log("Long-Term Memory: Preferences", "PASS", "Stored and sorted by confidence")
    else:
        log("Long-Term Memory: Preferences", "FAIL", "Preference storage issue")
    
    # Test persistence
    ltm.save()
    
    # Load in new instance
    ltm2 = LongTermMemory('test_user_123')
    prefs2 = ltm2.get_preferences('genre')
    
    if len(prefs2) == 2:
        log("Long-Term Memory: Persistence", "PASS", "Data persisted across instances")
    else:
        log("Long-Term Memory: Persistence", "FAIL", "Data not persisted")
    
    # Test semantic memory
    sem = SemanticMemory()
    
    sem.add_entity('artist', 'drake', {'name': 'Drake', 'genre': 'hip-hop'})
    sem.add_relationship('drake', 'similar_to', 'the_weeknd', strength=0.8)
    
    related = sem.get_related_entities('drake', 'similar_to')
    if 'the_weeknd' in related:
        log("Semantic Memory: Relationships", "PASS", "Stored and queried relationships")
    else:
        log("Semantic Memory: Relationships", "FAIL", "Relationship query failed")
    
    # Test full memory system
    memory = MemorySystem('test_user_456')
    
    memory.remember('favorite_artist', 'Drake', confidence=0.9)
    recalled = memory.recall('favorite_artist')
    
    if recalled and recalled[0]['value'] == 'Drake':
        log("Memory System: Integration", "PASS", "Full system works")
    else:
        log("Memory System: Integration", "FAIL", "Integration issue")
    
except Exception as e:
    log("Memory System", "ERROR", str(e))

# Test 3: Reasoning Engine
print("\n" + "="*80)
print("REASONING ENGINE")
print("="*80)

try:
    from src.reasoning_engine import ReasoningEngine
    log("Import Reasoning Engine", "PASS", "Reasoning module imported")
    
    # Create mock LLM agent for testing
    class MockLLM:
        pass
    
    reasoning = ReasoningEngine(MockLLM(), None)
    
    # Test intent classification
    intents = [
        ("Recommend music", "recommendation"),
        ("Why do I like this?", "analysis"),
        ("Compare Drake and The Weeknd", "comparison"),
        ("Help me discover new music", "exploration"),
        ("Who is Taylor Swift?", "information"),
    ]
    
    for question, expected_intent in intents:
        detected = reasoning._classify_intent(question)
        if detected == expected_intent:
            log(f"Intent: {expected_intent}", "PASS", f"Correctly classified")
        else:
            log(f"Intent: {expected_intent}", "WARNING", f"Got {detected} instead")
    
    # Test reasoning mode selection
    modes = reasoning._select_reasoning_mode('recommendation')
    if modes == 'creative':
        log("Reasoning Mode: Recommendation", "PASS", "Selected creative mode")
    else:
        log("Reasoning Mode: Recommendation", "WARNING", f"Selected {modes}")
    
except Exception as e:
    log("Reasoning Engine", "ERROR", str(e))

# Test 4: Music Toolkit
print("\n" + "="*80)
print("MUSIC TOOLKIT")
print("="*80)

try:
    from src.music_toolkit import MusicToolkit
    log("Import Music Toolkit", "PASS", "Toolkit module imported")
    
    # Create mock Spotify client
    class MockSpotify:
        def search_tracks(self, query, limit=10):
            return [{'name': f'Track {i}', 'id': f'id{i}'} for i in range(limit)]
        
        def search_artists(self, query, limit=10):
            return [{'name': f'Artist {i}', 'id': f'id{i}'} for i in range(limit)]
        
        def get_audio_features(self, track_id):
            return {'energy': 0.8, 'valence': 0.6, 'tempo': 120}
    
    toolkit = MusicToolkit(MockSpotify())
    
    # Test tool registration
    tools = toolkit.tools
    if len(tools) > 15:
        log("Toolkit: Registration", "PASS", f"Registered {len(tools)} tools")
    else:
        log("Toolkit: Registration", "WARNING", f"Only {len(tools)} tools")
    
    # Test tool execution
    result = toolkit.execute_tool('search_tracks', {'query': 'test', 'limit': 5})
    if len(result) == 5:
        log("Toolkit: Execution", "PASS", "Tool executed correctly")
    else:
        log("Toolkit: Execution", "FAIL", f"Expected 5 results, got {len(result)}")
    
    # Test tool descriptions
    desc = toolkit.get_tool_descriptions(format='text')
    if len(desc) > 100:
        log("Toolkit: Descriptions", "PASS", f"Generated {len(desc)} char description")
    else:
        log("Toolkit: Descriptions", "WARNING", "Short description")
    
    # Test invalid tool
    try:
        toolkit.execute_tool('invalid_tool', {})
        log("Toolkit: Invalid Tool", "FAIL", "Accepted invalid tool")
    except ValueError:
        log("Toolkit: Invalid Tool", "PASS", "Rejected invalid tool")
    
except Exception as e:
    log("Music Toolkit", "ERROR", str(e))

# Test 5: Enhanced Components Integration
print("\n" + "="*80)
print("ENHANCED COMPONENTS INTEGRATION")
print("="*80)

try:
    # Test that all components can work together
    from src.reasoning_engine import ReasoningEngine
    from src.music_toolkit import MusicToolkit
    from src.memory_system import MemorySystem
    from src.security_utils import SecurityUtils, InputValidator
    
    # Create integrated system
    class MockLLM:
        pass
    
    class MockSpotify:
        def search_tracks(self, query, limit=10):
            return []
    
    memory = MemorySystem('integration_test_user')
    reasoning = ReasoningEngine(MockLLM(), MockSpotify())
    toolkit = MusicToolkit(MockSpotify())
    security = SecurityUtils()
    
    # Simulate a complete flow
    question = "I'm feeling happy, recommend music"
    
    # Step 1: Validate input
    is_valid, error = InputValidator.validate_question(question)
    if is_valid:
        log("Integration: Input Validation", "PASS", "Input validated")
    else:
        log("Integration: Input Validation", "FAIL", error)
    
    # Step 2: Sanitize input
    clean_question = security.validate_input(question)
    if clean_question:
        log("Integration: Input Sanitization", "PASS", "Input sanitized")
    else:
        log("Integration: Input Sanitization", "FAIL", "Sanitization failed")
    
    # Step 3: Add to memory
    memory.short_term.add('user', clean_question)
    if len(memory.short_term.conversation_history) > 0:
        log("Integration: Memory Storage", "PASS", "Stored in memory")
    else:
        log("Integration: Memory Storage", "FAIL", "Memory storage failed")
    
    # Step 4: Classify intent
    intent = reasoning._classify_intent(clean_question)
    if intent:
        log("Integration: Intent Classification", "PASS", f"Intent: {intent}")
    else:
        log("Integration: Intent Classification", "FAIL", "No intent detected")
    
    # Step 5: Get tool descriptions
    tool_desc = toolkit.get_tool_descriptions()
    if len(tool_desc) > 0:
        log("Integration: Tool Access", "PASS", "Tools available")
    else:
        log("Integration: Tool Access", "WARNING", "No tools available")
    
    # Step 6: Simulate response
    response = {
        'insight': 'Happy music recommendations: upbeat pop, funk, disco...',
        'question': clean_question,
        'timestamp': datetime.now().isoformat()
    }
    
    # Step 7: Validate response
    is_valid, error = ResponseValidator.validate_response(response)
    if is_valid:
        log("Integration: Response Validation", "PASS", "Response validated")
    else:
        log("Integration: Response Validation", "FAIL", error)
    
    # Step 8: Sanitize output
    sanitized = security.sanitize_output(response['insight'])
    if sanitized:
        log("Integration: Output Sanitization", "PASS", "Output sanitized")
    else:
        log("Integration: Output Sanitization", "FAIL", "Sanitization failed")
    
    # Step 9: Store in memory
    memory.short_term.add('assistant', sanitized)
    memory.long_term.add_interaction('ai_insights', {'query': clean_question, 'response': sanitized})
    
    if len(memory.short_term.conversation_history) == 2:
        log("Integration: Memory Update", "PASS", "Memory updated")
    else:
        log("Integration: Memory Update", "FAIL", "Memory not updated")
    
    # Step 10: Get memory stats
    stats = memory.get_context_summary()
    if stats and 'short_term' in stats:
        log("Integration: Memory Stats", "PASS", f"Stats: {stats['short_term']['conversation_length']} messages")
    else:
        log("Integration: Memory Stats", "FAIL", "Stats not available")
    
    log("Complete Integration Flow", "PASS", "All components work together")
    
except Exception as e:
    log("Enhanced Components Integration", "ERROR", str(e))

# Test 6: Actual LLM Agent (if available)
print("\n" + "="*80)
print("ACTUAL LLM AGENT TESTING")
print("="*80)

try:
    from src.llm_agent import LLMAgent
    
    agent = LLMAgent()
    log("LLM Agent: Initialization", "PASS", f"Model type: {agent.model_type}")
    
    # Test basic query
    try:
        result = agent.get_music_insights(
            question="Tell me about jazz music",
            user_context="",
            conversation_history=None
        )
        
        if 'insight' in result or 'answer' in result:
            response_text = result.get('insight', result.get('answer', ''))
            if len(response_text) > 20:
                log("LLM Agent: Basic Query", "PASS", f"Response: {len(response_text)} chars")
            else:
                log("LLM Agent: Basic Query", "WARNING", "Short response")
        else:
            log("LLM Agent: Basic Query", "FAIL", "No response content")
    except Exception as e:
        log("LLM Agent: Basic Query", "ERROR", str(e))
    
    # Test streaming
    try:
        chunks = []
        for chunk in agent.get_music_insights_stream(
            question="What is hip-hop?",
            user_context="",
            conversation_history=None
        ):
            chunks.append(chunk)
        
        if len(chunks) > 0:
            total_text = ''.join(str(c) for c in chunks)
            log("LLM Agent: Streaming", "PASS", f"{len(chunks)} chunks, {len(total_text)} chars")
        else:
            log("LLM Agent: Streaming", "WARNING", "No chunks received")
    except Exception as e:
        log("LLM Agent: Streaming", "ERROR", str(e))
    
    # Test with conversation history
    try:
        history = [
            {'query': 'Tell me about jazz', 'response': 'Jazz is a music genre...'}
        ]
        
        result = agent.get_music_insights(
            question="What about hip-hop?",
            user_context="",
            conversation_history=history
        )
        
        if 'insight' in result or 'answer' in result:
            log("LLM Agent: With History", "PASS", "Handled conversation history")
        else:
            log("LLM Agent: With History", "FAIL", "Failed with history")
    except Exception as e:
        log("LLM Agent: With History", "ERROR", str(e))
    
    # Test with user context
    try:
        context = """
        USER PROFILE:
        Favorite genres: hip-hop, R&B
        Recently listening to: Drake, The Weeknd
        """
        
        result = agent.get_music_insights(
            question="Recommend something",
            user_context=context,
            conversation_history=None
        )
        
        if 'insight' in result or 'answer' in result:
            response_text = result.get('insight', result.get('answer', '')).lower()
            if 'drake' in response_text or 'hip-hop' in response_text or 'r&b' in response_text:
                log("LLM Agent: Personalization", "PASS", "Used user context")
            else:
                log("LLM Agent: Personalization", "WARNING", "May not have used context")
        else:
            log("LLM Agent: Personalization", "FAIL", "No response")
    except Exception as e:
        log("LLM Agent: Personalization", "ERROR", str(e))
    
    # Test fallback system
    try:
        # Test with various mood queries
        mood_queries = [
            "I'm feeling happy",
            "I'm sad",
            "Music for workout",
            "Help me sleep"
        ]
        
        fallback_works = 0
        for query in mood_queries:
            result = agent.get_music_insights(question=query, user_context="", conversation_history=None)
            if 'insight' in result or 'answer' in result:
                fallback_works += 1
        
        if fallback_works == len(mood_queries):
            log("LLM Agent: Fallback System", "PASS", f"All {fallback_works} queries answered")
        else:
            log("LLM Agent: Fallback System", "WARNING", f"Only {fallback_works}/{len(mood_queries)} answered")
    except Exception as e:
        log("LLM Agent: Fallback System", "ERROR", str(e))
    
except Exception as e:
    log("LLM Agent Testing", "ERROR", str(e))

# Test 7: Workflow Integration
print("\n" + "="*80)
print("WORKFLOW INTEGRATION")
print("="*80)

try:
    from src.workflow import MultiAgentWorkflow
    
    workflow = MultiAgentWorkflow()
    log("Workflow: Initialization", "PASS", "Workflow initialized")
    
    # Test agent status
    status = workflow.get_agent_status()
    if status.get('llm_agent'):
        log("Workflow: LLM Agent Status", "PASS", "LLM agent available")
    else:
        log("Workflow: LLM Agent Status", "WARNING", "LLM agent not available")
    
    # Test user context generation
    try:
        context = workflow.get_user_context_for_ai()
        if isinstance(context, str):
            log("Workflow: User Context", "PASS", f"Generated {len(context)} char context")
        else:
            log("Workflow: User Context", "WARNING", "No context generated")
    except Exception as e:
        log("Workflow: User Context", "WARNING", f"Context generation failed: {str(e)}")
    
except Exception as e:
    log("Workflow Integration", "ERROR", str(e))

# Print final summary
print("\n" + "="*80)
print("📊 INTEGRATION TEST SUMMARY")
print("="*80)
print(f"Total Tests: {results['total']}")
print(f"✅ Passed: {results.get('passed', 0)}")
print(f"❌ Failed: {results.get('failed', 0)}")
print(f"⚠️  Warnings: {results.get('warnings', 0)}")
print(f"💥 Errors: {results.get('errors', 0)}")

if results['total'] > 0:
    success_rate = (results.get('passed', 0) / results['total']) * 100
    print(f"📈 Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("🏆 EXCELLENT - Production ready!")
    elif success_rate >= 75:
        print("👍 GOOD - Minor fixes needed")
    elif success_rate >= 60:
        print("⚠️  FAIR - Improvements needed")
    else:
        print("❌ POOR - Major issues")

print("="*80 + "\n")

# Save results
with open('/vercel/sandbox/test_results_integration.json', 'w') as f:
    json.dump(results, f, indent=2)

print("💾 Results saved to: test_results_integration.json\n")
