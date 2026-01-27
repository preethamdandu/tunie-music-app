#!/usr/bin/env python3
"""
Test script to verify all API keys are properly configured
"""

import os
from pathlib import Path

def test_env_file():
    """Test if .env file exists and contains API keys"""
    print("=" * 60)
    print("🔍 TESTING API KEY CONFIGURATION")
    print("=" * 60)
    print()
    
    env_path = Path(".env")
    
    if not env_path.exists():
        print("❌ ERROR: .env file not found!")
        print("   Location: /vercel/sandbox/.env")
        return False
    
    print("✅ .env file found")
    print()
    
    # Read .env file
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Check for API keys
    api_keys = {
        "GROQ_API_KEY": "Groq (Primary - Ultra Fast)",
        "GOOGLE_API_KEY": "Google Gemini (Backup - High Quality)",
        "OPENROUTER_API_KEY": "OpenRouter (Flexible - Multiple Models)",
        "DEEPSEEK_API_KEY": "DeepSeek (Best Value)",
        "HUGGINGFACE_API_KEY": "HuggingFace (Fallback)"
    }
    
    print("📋 API Key Status:")
    print("-" * 60)
    
    configured_count = 0
    for key, description in api_keys.items():
        if f"{key}=" in content:
            # Check if it has a real value (not placeholder)
            for line in content.split('\n'):
                if line.startswith(f"{key}="):
                    value = line.split('=', 1)[1].strip()
                    if value and not value.startswith('your_') and value != '':
                        print(f"✅ {description}")
                        print(f"   Key: {key}")
                        print(f"   Value: {value[:20]}... (redacted)")
                        configured_count += 1
                    else:
                        print(f"⚠️  {description}")
                        print(f"   Key: {key}")
                        print(f"   Status: Placeholder - needs real key")
                    print()
                    break
        else:
            print(f"❌ {description}")
            print(f"   Key: {key}")
            print(f"   Status: Not found in .env")
            print()
    
    print("-" * 60)
    print(f"📊 Summary: {configured_count}/{len(api_keys)} API keys configured")
    print()
    
    if configured_count >= 2:
        print("✅ SUFFICIENT: At least 2 API keys configured")
        print("   Your app will work with automatic fallback")
        return True
    elif configured_count == 1:
        print("⚠️  WARNING: Only 1 API key configured")
        print("   App will work but no fallback available")
        return True
    else:
        print("❌ ERROR: No API keys configured")
        print("   App will not work - please add at least one API key")
        return False

def test_imports():
    """Test if required modules can be imported"""
    print()
    print("=" * 60)
    print("🔍 TESTING MODULE IMPORTS")
    print("=" * 60)
    print()
    
    modules = [
        ("src.ai_providers", "Multi-Provider AI Client"),
        ("src.zero_cost_enforcer", "Zero-Cost Enforcer"),
        ("src.config", "Configuration Manager")
    ]
    
    success_count = 0
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"✅ {description} ({module_name})")
            success_count += 1
        except ImportError as e:
            print(f"❌ {description} ({module_name})")
            print(f"   Error: {e}")
        except Exception as e:
            print(f"⚠️  {description} ({module_name})")
            print(f"   Warning: {e}")
    
    print()
    print(f"📊 Summary: {success_count}/{len(modules)} modules imported successfully")
    print()
    
    return success_count == len(modules)

def main():
    """Run all tests"""
    print()
    print("🚀 TuneGenie API Configuration Test")
    print()
    
    env_ok = test_env_file()
    imports_ok = test_imports()
    
    print()
    print("=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)
    print()
    
    if env_ok and imports_ok:
        print("✅ ALL TESTS PASSED")
        print()
        print("🎉 Your TuneGenie app is ready to use!")
        print()
        print("To start the app:")
        print("  streamlit run app.py")
        print()
        return 0
    elif env_ok:
        print("⚠️  PARTIAL SUCCESS")
        print()
        print("API keys are configured but some modules have import issues.")
        print("This may be due to missing dependencies.")
        print()
        print("Try installing dependencies:")
        print("  pip install -r requirements.txt")
        print()
        return 1
    else:
        print("❌ TESTS FAILED")
        print()
        print("Please check the errors above and fix them.")
        print()
        return 1

if __name__ == "__main__":
    exit(main())
