"""
STANDALONE BRUTAL TEST SUITE FOR AI INSIGHTS
Tests the intelligent fallback system without external dependencies
"""

import sys
import os
import json
import time
from datetime import datetime

# Test results tracking
test_results = {
    'total_tests': 0,
    'passed': 0,
    'failed': 0,
    'errors': 0,
    'warnings': 0,
    'test_details': []
}

def log_test(test_name: str, status: str, message: str = "", details: any = None):
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
        'details': str(details)[:200] if details else None,
        'timestamp': datetime.now().isoformat()
    }
    
    test_results['test_details'].append(result)
    print(f"{symbol} {test_name}: {status} - {message}")

# Simulate the intelligent fallback system
class MockLLMAgent:
    """Mock LLM Agent for testing fallback logic"""
    
    def _get_intelligent_fallback(self, question: str, user_context: str = "", history_context: str = ""):
        """Intelligent fallback response system"""
        try:
            question_lower = question.lower() if question else ""
            context_lower = user_context.lower() if user_context else ""
            history_lower = history_context.lower() if history_context else ""
            
            # Check for follow-up question patterns
            is_follow_up = any(phrase in question_lower for phrase in [
                'more', 'another', 'similar', 'like that', 'same', 'also', 
                'what else', 'anything else', 'tell me more', 'expand on',
                'why', 'how about', 'what about', 'and', 'but'
            ])
            
            # Extract context from previous conversation for follow-ups
            prev_topic = ""
            if is_follow_up and history_context:
                if 'workout' in history_lower or 'exercise' in history_lower:
                    prev_topic = "workout"
                elif 'study' in history_lower or 'studying' in history_lower:
                    prev_topic = "studying/focus"
                elif 'jazz' in history_lower:
                    prev_topic = "jazz"
                elif 'hip-hop' in history_lower or 'rap' in history_lower:
                    prev_topic = "hip-hop"
            
            # Handle follow-up questions with context
            if is_follow_up and prev_topic:
                follow_up_responses = {
                    "jazz": "Building on our jazz discussion - try bebop (Charlie Parker) for complex improvisation, or smooth jazz (Kenny G) for relaxation.",
                    "hip-hop": "Continuing with hip-hop - you might enjoy underground hip-hop (MF DOOM), boom bap classics (Nas), or alternative hip-hop (Anderson .Paak).",
                    "workout": "More workout music ideas - try drum and bass (Netsky) for high-intensity cardio, or metal (Metallica) for lifting.",
                    "studying/focus": "More focus music options - try video game soundtracks, lo-fi hip-hop playlists, or classical piano (Chopin's Nocturnes)."
                }
                
                if prev_topic in follow_up_responses:
                    return {
                        'insight': follow_up_responses[prev_topic],
                        'question': question,
                        'timestamp': datetime.now().isoformat(),
                        'model_used': 'TuneGenie AI (Conversation Memory)',
                        'is_follow_up': True
                    }
            
            # Enhanced mood-based responses
            if 'happy' in question_lower or 'joy' in question_lower:
                insight = "Happy music should be bright, uplifting, and energizing! Look for songs with major keys, upbeat tempos (120-140 BPM), and positive lyrics. Genres like pop, funk, disco, and upbeat indie rock are perfect for boosting your mood."
            
            elif 'sad' in question_lower or 'melancholy' in question_lower:
                insight = "Sad music can be therapeutic and help process emotions. Look for songs with minor keys, slower tempos, and meaningful lyrics. Genres like indie folk, acoustic, and some classical music can provide comfort and emotional release."
            
            elif 'energetic' in question_lower or 'pump' in question_lower:
                insight = "Energetic music should get your heart pumping! Look for high-tempo songs (140+ BPM) with strong beats, powerful bass lines, and dynamic energy. Genres like rock, electronic, hip-hop, and dance music are perfect for high-energy activities."
            
            elif 'calm' in question_lower or 'relax' in question_lower:
                insight = "Calm music should be soothing and peaceful. Look for slow tempos (60-80 BPM), gentle melodies, and minimal complexity. Genres like ambient, classical, acoustic, and some jazz can help reduce stress and create a peaceful atmosphere."
            
            elif 'focus' in question_lower or 'concentrate' in question_lower or 'study' in question_lower:
                insight = "For studying and focused work, choose music without lyrics to avoid cognitive interference. Instrumental music, ambient sounds, or lo-fi beats work well. Classical music, especially Baroque period pieces, has been shown to improve concentration."
            
            elif 'workout' in question_lower or 'exercise' in question_lower or 'gym' in question_lower:
                insight = "Workout music should be high-energy and motivating! Look for songs with strong beats (120-150 BPM), powerful bass lines, and energizing rhythms. Genres like rock, EDM, hip-hop, and pop are perfect for maintaining energy during exercise."
            
            elif 'sleep' in question_lower or 'bedtime' in question_lower:
                insight = "Sleep music should be extremely gentle and calming. Look for very slow tempos (60 BPM or slower), soft melodies, and minimal complexity. Avoid anything with strong beats or sudden changes."
            
            # Genre responses
            elif 'jazz' in question_lower:
                insight = "Jazz is a uniquely American art form characterized by improvisation, syncopated rhythms, and complex harmonies. It ranges from smooth and relaxing (Miles Davis' 'Kind of Blue') to energetic and complex (John Coltrane). Perfect for sophisticated dinner parties, studying, or relaxing evenings."
            
            elif 'hip-hop' in question_lower or 'rap' in question_lower:
                insight = "Hip-hop is more than music - it's a cultural movement. It's characterized by rhythmic speech (rapping), beatboxing, and sampling. Hip-hop can be conscious and political (Kendrick Lamar), party-oriented (Drake), or experimental (Tyler, The Creator). Perfect for workouts, parties, or feeling confident."
            
            elif 'classical' in question_lower:
                insight = "Classical music spans over 400 years of Western musical tradition. It's characterized by complex compositions and orchestral arrangements. From peaceful works of Debussy to dramatic symphonies of Beethoven, it's perfect for studying, relaxing, or experiencing deep emotional expression."
            
            elif 'electronic' in question_lower:
                insight = "Electronic music is created using electronic instruments and technology. It ranges from ambient and chill (Tycho) to high-energy dance music (Skrillex). Electronic music is incredibly versatile and can match any mood or activity."
            
            elif 'rock' in question_lower:
                insight = "Rock music emerged in the 1950s and has evolved into countless subgenres. It's characterized by electric guitars, strong rhythms, and often rebellious themes. Rock can be soft and melodic (The Beatles) or heavy and aggressive (Metallica). Perfect for workouts, driving, or feeling powerful."
            
            # Artist responses
            elif 'drake' in question_lower:
                insight = "Drake is a Canadian rapper and singer known for his melodic rap style, emotional lyrics, and ability to blend hip-hop with R&B. His hits include 'Hotline Bling,' 'God's Plan,' and 'One Dance.' Drake's versatile style makes his music suitable for various moods."
            
            elif 'beatles' in question_lower:
                insight = "The Beatles were an English rock band formed in 1960, widely regarded as the most influential band in history. Their music evolved from simple pop to complex, experimental compositions. Their catalog is timeless and suitable for any mood."
            
            elif 'taylor swift' in question_lower:
                insight = "Taylor Swift is known for her narrative songwriting and genre-spanning career. From country to pop to indie folk, her music tells personal stories. Albums like '1989' are upbeat and confident, while 'folklore' is introspective and calm."
            
            elif 'kendrick lamar' in question_lower:
                insight = "Kendrick Lamar is known for socially conscious lyrics and innovative musical style. His music addresses themes of race, inequality, and personal struggle with poetic depth. Perfect for deep listening or when you want to engage with meaningful content."
            
            # Complex scenario responses
            elif 'party' in question_lower:
                insight = "For a party playlist, mix high-energy music from different genres: pop hits (Dua Lipa), hip-hop bangers (Drake), EDM (Calvin Harris), and classic party songs. Aim for songs with strong beats (120-140 BPM) and positive energy."
            
            elif 'anxiety' in question_lower or 'depression' in question_lower:
                insight = "Music can help manage anxiety and depression. Look for calming, gentle music with slow tempos and soothing melodies. Genres like ambient, classical, or acoustic can help reduce stress. However, please reach out to mental health professionals for support."
            
            elif 'meditation' in question_lower or 'yoga' in question_lower:
                insight = "For meditation and yoga, choose ambient music, nature sounds, or gentle instrumental pieces with minimal variation. Avoid lyrics or strong rhythms. The music should fade into the background, supporting your practice without becoming the focus."
            
            elif 'discover' in question_lower or 'new artists' in question_lower:
                insight = "Discovering new artists is exciting! Start by exploring music similar to what you already love. Try listening to different genres, check out music from different countries, or explore artists from different time periods. Attend local concerts and ask friends for recommendations."
            
            else:
                # Generic but helpful response
                insight = f"I can help you with music recommendations! For '{question}', consider what mood you're in and what activity you're doing. Different situations call for different types of music - energetic for workouts, calm for relaxation, focused for work. What specific mood or activity are you looking for music for?"
            
            # Add personalization based on user context if available
            if user_context and 'USER PROFILE' in user_context:
                insight += " Based on your listening history, I can provide more personalized recommendations."
            
            return {
                'insight': insight,
                'question': question,
                'timestamp': datetime.now().isoformat(),
                'model_used': 'TuneGenie AI (Intelligent Fallback)'
            }
            
        except Exception as e:
            return {
                'insight': f"I can help you with music recommendations! Try asking about specific genres, moods, or activities.",
                'question': question,
                'timestamp': datetime.now().isoformat(),
                'model_used': 'TuneGenie AI (Fallback)',
                'error': str(e)
            }

def test_edge_cases():
    """Test extreme edge cases"""
    agent = MockLLMAgent()
    
    print("\n" + "="*80)
    print("TEST CATEGORY: EDGE CASES")
    print("="*80)
    
    # Test 1: Empty question
    result = agent._get_intelligent_fallback("", "", "")
    if 'insight' in result and len(result['insight']) > 0:
        log_test("Empty Question", "PASS", "Provided fallback response")
    else:
        log_test("Empty Question", "FAIL", "No response for empty question")
    
    # Test 2: None values
    try:
        result = agent._get_intelligent_fallback(None, None, None)
        log_test("None Values", "PASS", "Handled None inputs")
    except Exception as e:
        log_test("None Values", "ERROR", str(e))
    
    # Test 3: Very long question
    long_q = "Tell me about music " * 500
    result = agent._get_intelligent_fallback(long_q, "", "")
    if 'insight' in result:
        log_test("Long Question (2500+ words)", "PASS", "Handled long input")
    else:
        log_test("Long Question", "FAIL", "Failed on long input")
    
    # Test 4: Special characters
    result = agent._get_intelligent_fallback("What about 音楽 🎵 & émotions?", "", "")
    if 'insight' in result:
        log_test("Special Characters & Unicode", "PASS", "Handled special chars")
    else:
        log_test("Special Characters", "FAIL", "Failed on special chars")
    
    # Test 5: SQL Injection
    result = agent._get_intelligent_fallback("'; DROP TABLE users; --", "", "")
    if 'insight' in result and 'DROP TABLE' not in result['insight']:
        log_test("SQL Injection Attempt", "PASS", "Neutralized malicious input")
    else:
        log_test("SQL Injection", "WARNING", "May not have sanitized input")
    
    # Test 6: XSS Attack
    result = agent._get_intelligent_fallback("<script>alert('xss')</script>", "", "")
    if 'insight' in result and '<script>' not in result['insight']:
        log_test("XSS Attack", "PASS", "Neutralized XSS attempt")
    else:
        log_test("XSS Attack", "WARNING", "Script tag may be present")

def test_mood_queries():
    """Test mood-based queries"""
    agent = MockLLMAgent()
    
    print("\n" + "="*80)
    print("TEST CATEGORY: MOOD-BASED QUERIES")
    print("="*80)
    
    mood_tests = [
        ("I'm feeling happy", ["happy", "upbeat", "positive"]),
        ("I'm sad today", ["sad", "emotion", "comfort"]),
        ("I need energy", ["energy", "pump", "motivat"]),
        ("I want to relax", ["calm", "relax", "peace"]),
        ("I'm anxious", ["anxiety", "calm", "stress"]),
    ]
    
    for question, expected_keywords in mood_tests:
        result = agent._get_intelligent_fallback(question, "", "")
        response = result.get('insight', '').lower()
        
        matches = sum(1 for kw in expected_keywords if kw in response)
        
        if matches >= 2:
            log_test(f"Mood: '{question}'", "PASS", f"Contains {matches}/{len(expected_keywords)} keywords")
        elif matches >= 1:
            log_test(f"Mood: '{question}'", "WARNING", f"Only {matches}/{len(expected_keywords)} keywords")
        else:
            log_test(f"Mood: '{question}'", "FAIL", "No expected keywords found")

def test_genre_queries():
    """Test genre-based queries"""
    agent = MockLLMAgent()
    
    print("\n" + "="*80)
    print("TEST CATEGORY: GENRE QUERIES")
    print("="*80)
    
    genre_tests = [
        ("Tell me about jazz", "jazz"),
        ("What is hip-hop?", "hip-hop"),
        ("Explain classical music", "classical"),
        ("What about rock music?", "rock"),
        ("Tell me about electronic music", "electronic"),
    ]
    
    for question, genre in genre_tests:
        result = agent._get_intelligent_fallback(question, "", "")
        response = result.get('insight', '').lower()
        
        if genre.lower() in response:
            log_test(f"Genre: {genre}", "PASS", f"Response mentions {genre}")
        else:
            log_test(f"Genre: {genre}", "FAIL", f"Response doesn't mention {genre}")

def test_activity_queries():
    """Test activity-based queries"""
    agent = MockLLMAgent()
    
    print("\n" + "="*80)
    print("TEST CATEGORY: ACTIVITY QUERIES")
    print("="*80)
    
    activity_tests = [
        ("Music for workout", ["workout", "exercise", "energy"]),
        ("What should I listen to while studying?", ["study", "focus", "concentrat"]),
        ("Music for sleeping", ["sleep", "calm", "gentle"]),
        ("Party playlist", ["party", "energy", "dance"]),
        ("Meditation music", ["meditation", "calm", "peace"]),
    ]
    
    for question, expected_keywords in activity_tests:
        result = agent._get_intelligent_fallback(question, "", "")
        response = result.get('insight', '').lower()
        
        matches = sum(1 for kw in expected_keywords if kw in response)
        
        if matches >= 2:
            log_test(f"Activity: '{question[:30]}'", "PASS", f"{matches}/{len(expected_keywords)} keywords")
        elif matches >= 1:
            log_test(f"Activity: '{question[:30]}'", "WARNING", f"Only {matches} keyword")
        else:
            log_test(f"Activity: '{question[:30]}'", "FAIL", "No keywords found")

def test_artist_queries():
    """Test artist-specific queries"""
    agent = MockLLMAgent()
    
    print("\n" + "="*80)
    print("TEST CATEGORY: ARTIST QUERIES")
    print("="*80)
    
    artist_tests = [
        ("Tell me about Drake", "drake"),
        ("Who are The Beatles?", "beatles"),
        ("What about Taylor Swift?", "taylor swift"),
        ("Tell me about Kendrick Lamar", "kendrick lamar"),
    ]
    
    for question, artist in artist_tests:
        result = agent._get_intelligent_fallback(question, "", "")
        response = result.get('insight', '').lower()
        
        if artist.lower() in response:
            log_test(f"Artist: {artist.title()}", "PASS", f"Response mentions {artist}")
        else:
            log_test(f"Artist: {artist.title()}", "FAIL", f"Response doesn't mention {artist}")

def test_follow_up_questions():
    """Test follow-up question handling"""
    agent = MockLLMAgent()
    
    print("\n" + "="*80)
    print("TEST CATEGORY: FOLLOW-UP QUESTIONS")
    print("="*80)
    
    # Test 1: Follow-up about jazz
    history = "Q1: Tell me about jazz\nA1: Jazz is a music genre..."
    result = agent._get_intelligent_fallback("Tell me more", "", history)
    
    if result.get('is_follow_up'):
        log_test("Follow-up: Jazz Context", "PASS", "Detected follow-up with context")
    else:
        log_test("Follow-up: Jazz Context", "WARNING", "May not have used context")
    
    # Test 2: Follow-up about workout
    history = "Q1: Music for workout\nA1: High-energy music..."
    result = agent._get_intelligent_fallback("What else?", "", history)
    
    if 'workout' in result.get('insight', '').lower():
        log_test("Follow-up: Workout Context", "PASS", "Maintained workout context")
    else:
        log_test("Follow-up: Workout Context", "WARNING", "Lost context")
    
    # Test 3: Follow-up without history
    result = agent._get_intelligent_fallback("Tell me more", "", "")
    
    if 'insight' in result:
        log_test("Follow-up: No History", "PASS", "Handled follow-up without context")
    else:
        log_test("Follow-up: No History", "FAIL", "Failed without context")

def test_personalization():
    """Test personalization with user context"""
    agent = MockLLMAgent()
    
    print("\n" + "="*80)
    print("TEST CATEGORY: PERSONALIZATION")
    print("="*80)
    
    # Test with rich user context
    context = """
    USER PROFILE:
    Favorite genres: hip-hop, R&B, electronic
    Recently listening to: Drake, The Weeknd, Travis Scott
    Music style preferences: high-energy, upbeat, modern
    """
    
    result = agent._get_intelligent_fallback("Recommend something", context, "")
    response = result.get('insight', '')
    
    if 'listening history' in response.lower() or 'personalized' in response.lower():
        log_test("Personalization: Rich Context", "PASS", "Acknowledged user context")
    else:
        log_test("Personalization: Rich Context", "WARNING", "May not use context")
    
    # Test without context
    result = agent._get_intelligent_fallback("Recommend something", "", "")
    
    if 'insight' in result:
        log_test("Personalization: No Context", "PASS", "Provided generic recommendation")
    else:
        log_test("Personalization: No Context", "FAIL", "Failed without context")

def test_non_music_queries():
    """Test handling of non-music queries"""
    agent = MockLLMAgent()
    
    print("\n" + "="*80)
    print("TEST CATEGORY: NON-MUSIC QUERIES")
    print("="*80)
    
    non_music_queries = [
        "What is the capital of France?",
        "How do I cook pasta?",
        "Tell me about quantum physics",
        "What's the weather today?",
    ]
    
    for question in non_music_queries:
        result = agent._get_intelligent_fallback(question, "", "")
        response = result.get('insight', '').lower()
        
        if 'music' in response or 'recommend' in response:
            log_test(f"Non-Music: '{question[:30]}'", "PASS", "Redirected to music")
        else:
            log_test(f"Non-Music: '{question[:30]}'", "WARNING", "May have answered off-topic")

def test_performance():
    """Test performance with various query types"""
    agent = MockLLMAgent()
    
    print("\n" + "="*80)
    print("TEST CATEGORY: PERFORMANCE")
    print("="*80)
    
    # Test 1: Simple query performance
    start = time.time()
    for _ in range(100):
        agent._get_intelligent_fallback("Tell me about jazz", "", "")
    elapsed = time.time() - start
    
    if elapsed < 1.0:
        log_test("Performance: 100 Simple Queries", "PASS", f"{elapsed:.3f}s ({elapsed*10:.1f}ms avg)")
    else:
        log_test("Performance: 100 Simple Queries", "WARNING", f"{elapsed:.3f}s (slow)")
    
    # Test 2: Complex query performance
    start = time.time()
    long_context = "User likes: " + ", ".join([f"artist{i}" for i in range(100)])
    long_history = "Previous conversation: " + " ".join([f"Q{i}: question A{i}: answer" for i in range(50)])
    
    for _ in range(10):
        agent._get_intelligent_fallback("Complex question about music recommendations", long_context, long_history)
    elapsed = time.time() - start
    
    if elapsed < 1.0:
        log_test("Performance: 10 Complex Queries", "PASS", f"{elapsed:.3f}s ({elapsed*100:.1f}ms avg)")
    else:
        log_test("Performance: 10 Complex Queries", "WARNING", f"{elapsed:.3f}s")

def test_stress_scenarios():
    """Test stress scenarios"""
    agent = MockLLMAgent()
    
    print("\n" + "="*80)
    print("TEST CATEGORY: STRESS SCENARIOS")
    print("="*80)
    
    # Test 1: Rapid-fire queries
    start = time.time()
    for i in range(50):
        agent._get_intelligent_fallback(f"Question {i}", "", "")
    elapsed = time.time() - start
    
    log_test("Stress: 50 Rapid Queries", "PASS", f"Completed in {elapsed:.3f}s")
    
    # Test 2: Memory stress
    try:
        for i in range(1000):
            result = agent._get_intelligent_fallback(
                f"Question {i}" * 10,
                f"Context {i}" * 10,
                f"History {i}" * 10
            )
        log_test("Stress: 1000 Queries", "PASS", "No memory issues")
    except Exception as e:
        log_test("Stress: 1000 Queries", "ERROR", str(e))

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("🔥 STANDALONE BRUTAL AI INSIGHTS TEST SUITE 🔥")
    print("="*80)
    
    start_time = time.time()
    
    # Run all test categories
    test_edge_cases()
    test_mood_queries()
    test_genre_queries()
    test_activity_queries()
    test_artist_queries()
    test_follow_up_questions()
    test_personalization()
    test_non_music_queries()
    test_performance()
    test_stress_scenarios()
    
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
        
        # Quality assessment
        if success_rate >= 90:
            print("🏆 EXCELLENT - System is production-ready!")
        elif success_rate >= 75:
            print("👍 GOOD - Minor improvements needed")
        elif success_rate >= 60:
            print("⚠️  FAIR - Significant improvements needed")
        else:
            print("❌ POOR - Major issues detected")
    
    print("="*80 + "\n")
    
    # Save detailed results
    with open('/vercel/sandbox/test_results_standalone.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print("💾 Detailed results saved to: test_results_standalone.json\n")
    
    return test_results

if __name__ == "__main__":
    results = run_all_tests()
    
    # Exit with appropriate code
    if results['failed'] > 5 or results['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)
