"""
Test actual API call to Google to verify which key is being used
Run this with: python test_google_api_call.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redbot.settings')
django.setup()

from bots.models import Bot
import requests

print("=" * 80)
print("GOOGLE API CALL TEST")
print("=" * 80)

# Get the bot
bot = Bot.objects.first()
if not bot:
    print("❌ No bot found!")
    exit(1)

print(f"\n✅ Bot: {bot.name}")
print(f"   Provider: {bot.ai_provider}")
print(f"   Model: {bot.ai_model}")

# Get the API key
api_key = bot.ai_api_key
if not api_key:
    print("❌ No API key set!")
    exit(1)

print(f"\n🔑 API Key Info:")
print(f"   Length: {len(api_key)} characters")
print(f"   Preview: {api_key[:15]}...{api_key[-10:]}")

# Test the API call
print(f"\n🌐 Testing Google API call...")
model = bot.ai_model or "gemini-2.0-flash"
full_model = model if model.startswith("models/") else f"models/{model}"
url = f"https://generativelanguage.googleapis.com/v1beta/{full_model}:generateContent?key={api_key}"

payload = {
    "contents": [{"role": "user", "parts": [{"text": "Say 'Hello' in one word"}]}],
    "generationConfig": {
        "temperature": 0.0,
        "maxOutputTokens": 10
    }
}

try:
    print(f"   URL: {url[:80]}...")
    print(f"   Making request...")
    
    response = requests.post(url, json=payload, timeout=30)
    
    print(f"\n📊 Response:")
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"   ✅ SUCCESS! API key is valid and working!")
        data = response.json()
        
        # Try to extract the response text
        try:
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "")
                    print(f"   Response text: {text}")
        except:
            pass
            
        print(f"\n   Full response: {response.text[:200]}...")
        
    elif response.status_code == 429:
        print(f"   ❌ QUOTA EXCEEDED!")
        print(f"\n   This confirms the API key is valid but quota is exhausted.")
        print(f"   Response: {response.text[:500]}")
        
        # Check if it's the same error
        data = response.json()
        error = data.get("error", {})
        message = error.get("message", "")
        
        if "free_tier" in message:
            print(f"\n   ⚠️  FREE TIER QUOTA EXHAUSTED")
            print(f"   Solutions:")
            print(f"   1. Wait for quota reset (usually midnight Pacific Time)")
            print(f"   2. Create a NEW Google Cloud Project (not just new API key)")
            print(f"   3. Enable billing on your Google Cloud Project")
            print(f"   4. Switch to a different AI provider (OpenAI, Anthropic, etc.)")
        
    elif response.status_code == 400:
        print(f"   ❌ BAD REQUEST")
        print(f"   The API key might be invalid or the request format is wrong")
        print(f"   Response: {response.text[:500]}")
        
    elif response.status_code == 403:
        print(f"   ❌ FORBIDDEN")
        print(f"   The API key might be invalid or doesn't have permission")
        print(f"   Response: {response.text[:500]}")
        
    else:
        print(f"   ❌ UNEXPECTED ERROR")
        print(f"   Response: {response.text[:500]}")
        
except requests.exceptions.Timeout:
    print(f"   ❌ Request timed out")
except requests.exceptions.RequestException as e:
    print(f"   ❌ Request failed: {e}")
except Exception as e:
    print(f"   ❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
