#!/usr/bin/env python3
"""
Simple test script to verify TuneGenie app functionality
"""

import sys
import os

def test_basic_functionality():
    """Test basic app functionality without API calls"""
    print("🧪 Testing basic TuneGenie functionality...")
    
    try:
        # Test imports
        from src.workflow import MultiAgentWorkflow
        print("✅ MultiAgentWorkflow imported successfully")
        
        # Test workflow creation (should not crash even without API keys)
        try:
            workflow = MultiAgentWorkflow()
            print("✅ MultiAgentWorkflow created successfully")
            
            # Test workflow status
            status = workflow.get_agent_status()
            print(f"✅ Workflow status: {status}")
            
            # Test if workflow is ready
            ready = workflow.is_ready()
            print(f"✅ Workflow ready: {ready}")
            
        except Exception as e:
            print(f"⚠️ Workflow creation failed (expected without API keys): {e}")
        
        # Test utility classes
        from src.utils import DataProcessor, Visualizer, FileManager, MetricsCalculator
        
        processor = DataProcessor()
        print("✅ DataProcessor created")
        
        visualizer = Visualizer()
        print("✅ Visualizer created")
        
        file_manager = FileManager()
        print("✅ FileManager created")
        
        metrics_calc = MetricsCalculator()
        print("✅ MetricsCalculator created")
        
        print("\n🎉 Basic functionality test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def test_app_import():
    """Test that the main app can be imported"""
    print("\n🧪 Testing app import...")
    
    try:
        # This should not crash even without API keys
        import app
        print("✅ App imported successfully")
        return True
        
    except Exception as e:
        print(f"❌ App import failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🎵 TuneGenie - Basic Functionality Test")
    print("=" * 50)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("App Import", test_app_import)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! TuneGenie is ready for use.")
        print("\nNext steps:")
        print("1. Set up your API credentials in a .env file")
        print("2. Run: streamlit run app.py")
        print("3. Or use Docker: docker-compose up")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
