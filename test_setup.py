#!/usr/bin/env python3
"""
TuneGenie - Setup Test Script
Tests that all components can be imported and initialized correctly
"""

import sys
import os

def test_imports():
    """Test that all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        # Test core imports
        import pandas as pd
        print("✅ pandas imported successfully")
        
        import numpy as np
        print("✅ numpy imported successfully")
        
        import streamlit as st
        print("✅ streamlit imported successfully")
        
        import plotly.graph_objects as go
        print("✅ plotly imported successfully")
        
        # Test TuneGenie imports
        from src.spotify_client import SpotifyClient
        print("✅ SpotifyClient imported successfully")
        
        from src.recommender import CollaborativeFilteringRecommender
        print("✅ CollaborativeFilteringRecommender imported successfully")
        
        from src.llm_agent import LLMAgent
        print("✅ LLMAgent imported successfully")
        
        from src.workflow import MultiAgentWorkflow
        print("✅ MultiAgentWorkflow imported successfully")
        
        from src.utils import DataProcessor, Visualizer, FileManager, MetricsCalculator
        print("✅ Utility classes imported successfully")
        
        print("\n🎉 All imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_environment():
    """Test environment configuration"""
    print("\n🔧 Testing environment configuration...")
    
    required_vars = [
        'SPOTIFY_CLIENT_ID',
        'SPOTIFY_CLIENT_SECRET', 
        'SPOTIFY_REDIRECT_URI',
        'OPENAI_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var} is set")
        else:
            print(f"❌ {var} is not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️ Missing environment variables: {', '.join(missing_vars)}")
        print("Please create a .env file with your API credentials")
        return False
    else:
        print("\n🎉 Environment configuration complete!")
        return True

def test_component_initialization():
    """Test that components can be initialized (without API calls)"""
    print("\n🚀 Testing component initialization...")
    
    try:
        # Test recommender initialization
        from src.recommender import CollaborativeFilteringRecommender
        recommender = CollaborativeFilteringRecommender(algorithm='SVD')
        print("✅ CollaborativeFilteringRecommender initialized")
        
        # Test LLM agent initialization (will fail without API key, but that's expected)
        try:
            from src.llm_agent import LLMAgent
            llm_agent = LLMAgent()
            print("✅ LLMAgent initialized")
        except ValueError as e:
            if "OpenAI API key" in str(e):
                print("⚠️ LLMAgent requires OpenAI API key (expected)")
            else:
                raise
        
        # Test utility classes
        from src.utils import DataProcessor, Visualizer, FileManager, MetricsCalculator
        
        processor = DataProcessor()
        print("✅ DataProcessor initialized")
        
        visualizer = Visualizer()
        print("✅ Visualizer initialized")
        
        file_manager = FileManager()
        print("✅ FileManager initialized")
        
        metrics_calc = MetricsCalculator()
        print("✅ MetricsCalculator initialized")
        
        print("\n🎉 Component initialization successful!")
        return True
        
    except Exception as e:
        print(f"❌ Component initialization error: {e}")
        return False

def test_file_structure():
    """Test that all required files and directories exist"""
    print("\n📁 Testing file structure...")
    
    required_files = [
        'requirements.txt',
        'README.md',
        'app.py',
        'Dockerfile',
        'docker-compose.yml',
        'deploy_aws.sh'
    ]
    
    required_dirs = [
        'src',
        'data',
        'models',
        'prompts'
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} missing")
            missing_files.append(file)
    
    missing_dirs = []
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✅ {dir_name}/ directory exists")
        else:
            print(f"❌ {dir_name}/ directory missing")
            missing_dirs.append(dir_name)
    
    if missing_files or missing_dirs:
        print(f"\n⚠️ Missing files: {missing_files}")
        print(f"⚠️ Missing directories: {missing_dirs}")
        return False
    else:
        print("\n🎉 File structure complete!")
        return True

def main():
    """Main test function"""
    print("🎵 TuneGenie - Setup Test")
    print("=" * 40)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Imports", test_imports),
        ("Environment", test_environment),
        ("Component Initialization", test_component_initialization)
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
        print("\n🎉 All tests passed! TuneGenie is ready to use.")
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
