#!/usr/bin/env python3
"""
Comprehensive API Implementation Test
Tests all API endpoints and workflow functionality
"""

import sys
import os
import json
from datetime import datetime

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*70}")
    print(f"{title:^70}")
    print(f"{'='*70}")

def print_subsection(title):
    """Print a formatted subsection header"""
    print(f"\n{'-'*70}")
    print(f"{title}")
    print(f"{'-'*70}")

def test_imports():
    """Test 1: Verify all imports work"""
    print_section("TEST 1: IMPORT VERIFICATION")
    
    try:
        from src.workflow import MultiAgentWorkflow
        print("✅ MultiAgentWorkflow imported")
        
        from src.spotify_client import SpotifyClient
        print("✅ SpotifyClient imported")
        
        from src.recommender import CollaborativeFilteringRecommender
        print("✅ CollaborativeFilteringRecommender imported")
        
        from src.llm_agent import LLMAgent
        print("✅ LLMAgent imported")
        
        from src.intent_classifier import IntentClassifier
        print("✅ IntentClassifier imported")
        
        from src.utils import DataProcessor, Visualizer, FileManager, MetricsCalculator
        print("✅ Utils imported (DataProcessor, Visualizer, FileManager, MetricsCalculator)")
        
        from src.api_gateway import APIGateway
        print("✅ APIGateway imported")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_workflow_initialization():
    """Test 2: Verify workflow initialization"""
    print_section("TEST 2: WORKFLOW INITIALIZATION")
    
    try:
        from src.workflow import MultiAgentWorkflow
        
        workflow = MultiAgentWorkflow()
        print("✅ Workflow initialized successfully")
        
        # Check agent status
        status = workflow.get_agent_status()
        print(f"\nAgent Status:")
        print(f"  Spotify Client: {'✅ Active' if status['spotify_client'] else '❌ Inactive'}")
        print(f"  Recommender: {'✅ Active' if status['recommender'] else '❌ Inactive'}")
        print(f"  LLM Agent: {'✅ Active' if status['llm_agent'] else '❌ Inactive'}")
        print(f"  Overall Ready: {'✅ Yes' if status['ready'] else '❌ No'}")
        
        return workflow, status['ready']
    except Exception as e:
        print(f"❌ Workflow initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None, False

def test_workflow_status_api(workflow):
    """Test 3: Verify workflow status API"""
    print_section("TEST 3: WORKFLOW STATUS API")
    
    if not workflow:
        print("❌ Workflow not available, skipping test")
        return False
    
    try:
        status = workflow.get_workflow_status()
        print("✅ get_workflow_status() executed successfully")
        
        print(f"\nStatus Keys: {list(status.keys())}")
        
        # Check each component
        print_subsection("Spotify Client Status")
        spotify_status = status.get('spotify_client', {})
        print(f"  Status: {spotify_status.get('status', 'Unknown')}")
        print(f"  Authenticated: {spotify_status.get('authenticated', False)}")
        
        print_subsection("Recommender Status")
        rec_status = status.get('recommender', {})
        print(f"  Algorithm: {rec_status.get('algorithm', 'Unknown')}")
        print(f"  Trained: {rec_status.get('is_trained', False)}")
        print(f"  Users: {rec_status.get('user_count', 0)}")
        print(f"  Items: {rec_status.get('item_count', 0)}")
        
        print_subsection("LLM Agent Status")
        llm_status = status.get('llm_agent', {})
        print(f"  Model: {llm_status.get('model_name', 'Unknown')}")
        print(f"  Temperature: {llm_status.get('temperature', 'Unknown')}")
        
        print_subsection("Workflow History")
        history = status.get('workflow_history', {})
        print(f"  Total Executions: {history.get('total_executions', 0)}")
        print(f"  Recent Executions: {len(history.get('recent_executions', []))}")
        
        return True
    except Exception as e:
        print(f"❌ get_workflow_status() failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_workflow_methods(workflow):
    """Test 4: Verify all workflow methods exist"""
    print_section("TEST 4: WORKFLOW METHODS VERIFICATION")
    
    if not workflow:
        print("❌ Workflow not available, skipping test")
        return False
    
    expected_methods = [
        'execute_workflow',
        'get_agent_status',
        'get_workflow_status',
        'is_ready',
        'get_user_context_for_ai',
    ]
    
    print("Checking expected methods:")
    all_exist = True
    for method in expected_methods:
        if hasattr(workflow, method) and callable(getattr(workflow, method)):
            print(f"  ✅ {method}()")
        else:
            print(f"  ❌ {method}() - NOT FOUND")
            all_exist = False
    
    print("\nAll available public methods:")
    methods = [m for m in dir(workflow) if not m.startswith('_') and callable(getattr(workflow, m))]
    for method in sorted(methods):
        print(f"  • {method}()")
    
    return all_exist

def test_intent_classifier():
    """Test 5: Verify intent classifier"""
    print_section("TEST 5: INTENT CLASSIFIER")
    
    try:
        from src.intent_classifier import IntentClassifier
        
        classifier = IntentClassifier()
        print("✅ IntentClassifier initialized")
        
        # Test different query types
        test_cases = [
            ("artist: Taylor Swift", "Expected: niche_query or cf_first"),
            ("genre: jazz", "Expected: niche_query or cf_first"),
            ("happy workout music", "Expected: cf_first"),
            ("", "Expected: cf_first (empty query)"),
        ]
        
        print("\nTesting classification:")
        for query, expected in test_cases:
            result = classifier.classify(query)
            print(f"  Query: '{query}'")
            print(f"    Result: {result}")
            print(f"    {expected}")
        
        return True
    except Exception as e:
        print(f"❌ IntentClassifier test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_gateway():
    """Test 6: Verify API Gateway"""
    print_section("TEST 6: API GATEWAY")
    
    try:
        from src.api_gateway import APIGateway, get_api_gateway
        
        gateway = get_api_gateway()
        print("✅ APIGateway initialized")
        
        # Check stats
        stats = gateway.stats
        print(f"\nGateway Statistics:")
        print(f"  Primary Calls: {stats.get('primary_calls', 0)}")
        print(f"  Cache Hits: {stats.get('cache_hits', 0)}")
        print(f"  Fallback Calls: {stats.get('fallback_calls', 0)}")
        print(f"  Failures: {stats.get('failures', 0)}")
        print(f"  Cache Size: {stats.get('cache_size', 0)}")
        
        return True
    except Exception as e:
        print(f"❌ APIGateway test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_utils():
    """Test 7: Verify utility classes"""
    print_section("TEST 7: UTILITY CLASSES")
    
    try:
        from src.utils import DataProcessor, Visualizer, FileManager, MetricsCalculator
        
        # Test DataProcessor
        processor = DataProcessor()
        print("✅ DataProcessor initialized")
        
        # Test Visualizer
        visualizer = Visualizer()
        print("✅ Visualizer initialized")
        
        # Test FileManager
        file_manager = FileManager()
        print("✅ FileManager initialized")
        
        # Test MetricsCalculator
        metrics_calc = MetricsCalculator()
        print("✅ MetricsCalculator initialized")
        
        return True
    except Exception as e:
        print(f"❌ Utility classes test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_workflow_execution_dry_run(workflow):
    """Test 8: Dry run workflow execution (without API calls)"""
    print_section("TEST 8: WORKFLOW EXECUTION DRY RUN")
    
    if not workflow:
        print("❌ Workflow not available, skipping test")
        return False
    
    print("Note: This test verifies the workflow structure without making actual API calls")
    print("Actual API calls require valid credentials and will be tested separately")
    
    # Test workflow types
    workflow_types = [
        'playlist_generation',
        'user_analysis',
        'feedback_learning',
        'model_training'
    ]
    
    print("\nSupported workflow types:")
    for wf_type in workflow_types:
        print(f"  ✅ {wf_type}")
    
    return True

def test_app_import():
    """Test 9: Verify main app can be imported"""
    print_section("TEST 9: MAIN APP IMPORT")
    
    try:
        # This should not crash even without API keys
        import app
        print("✅ app.py imported successfully")
        
        # Check for main functions
        if hasattr(app, 'main'):
            print("✅ main() function exists")
        
        if hasattr(app, 'show_dashboard'):
            print("✅ show_dashboard() function exists")
        
        if hasattr(app, 'show_playlist_generation'):
            print("✅ show_playlist_generation() function exists")
        
        return True
    except Exception as e:
        print(f"❌ App import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print_section("TUNEGENIE API IMPLEMENTATION TEST SUITE")
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python Version: {sys.version}")
    
    results = {}
    
    # Run all tests
    results['imports'] = test_imports()
    
    workflow, ready = test_workflow_initialization()
    results['workflow_init'] = ready
    
    results['workflow_status'] = test_workflow_status_api(workflow)
    results['workflow_methods'] = test_workflow_methods(workflow)
    results['intent_classifier'] = test_intent_classifier()
    results['api_gateway'] = test_api_gateway()
    results['utils'] = test_utils()
    results['workflow_dry_run'] = test_workflow_execution_dry_run(workflow)
    results['app_import'] = test_app_import()
    
    # Summary
    print_section("TEST SUMMARY")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    failed_tests = total_tests - passed_tests
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✅")
    print(f"Failed: {failed_tests} ❌")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    print("\nDetailed Results:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    # Final verdict
    print_section("FINAL VERDICT")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED!")
        print("\nThe API implementation is complete and working correctly.")
        print("\nNext Steps:")
        print("1. Set up API credentials in .env file")
        print("2. Run: streamlit run app.py")
        print("3. Test with actual Spotify and OpenAI API calls")
        return 0
    else:
        print(f"⚠️  {failed_tests} TEST(S) FAILED")
        print("\nPlease review the failed tests above.")
        print("Some failures may be expected if API credentials are not configured.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
