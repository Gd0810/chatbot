"""
Test actual API call to Google to verify which key is being used
Run this with: python test_google_api_call.py
"""

import os
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redbot.settings')
django.setup()

from bots.models import Bot
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("GOOGLE API CALL TEST")
logger.info("=" * 80)

# Get the bot
bot = Bot.objects.first()
if not bot:
    logger.error("No bot found!")
    exit(1)

logger.info("\n✅ Bot: %s", bot.name)
logger.info("   Provider: %s", bot.ai_provider)
logger.info("   Model: %s", bot.ai_model)

# Get the API key
api_key = bot.ai_api_key
if not api_key:
    logger.error("No API key set!")
    exit(1)

logger.info("\n🔑 API Key Info:")
logger.info("   Length: %s characters", len(api_key))
logger.info("   Preview: %s...%s", api_key[:15], api_key[-10:])

# Test the API call
logger.info("\n🌐 Testing Google API call...")
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
    logger.debug("URL: %s...", url[:80])
    logger.debug("Making request...")
    
    response = requests.post(url, json=payload, timeout=30)
    
    logger.info("\n📊 Response:")
    logger.info("   Status Code: %s", response.status_code)
    
    if response.status_code == 200:
        logger.info("   ✅ SUCCESS! API key is valid and working!")
        data = response.json()
        
        # Try to extract the response text
        try:
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "")
                    logger.debug("   Response text: %s", text)
        except:
            pass
            
        logger.info("\n   Full response: %s...", response.text[:200])
        
    elif response.status_code == 429:
        logger.warning("   QUOTA EXCEEDED!")
        logger.warning("\n   This confirms the API key is valid but quota is exhausted.")
        logger.debug("   Response: %s", response.text[:500])
        
        # Check if it's the same error
        data = response.json()
        error = data.get("error", {})
        message = error.get("message", "")
        
        if "free_tier" in message:
            logger.warning("\n   ⚠️  FREE TIER QUOTA EXHAUSTED")
            logger.warning("   Solutions:")
            logger.warning("   1. Wait for quota reset (usually midnight Pacific Time)")
            logger.warning("   2. Create a NEW Google Cloud Project (not just new API key)")
            logger.warning("   3. Enable billing on your Google Cloud Project")
            logger.warning("   4. Switch to a different AI provider (OpenAI, Anthropic, etc.)")
        
    elif response.status_code == 400:
        logger.error("   BAD REQUEST")
        logger.error("   The API key might be invalid or the request format is wrong")
        logger.debug("   Response: %s", response.text[:500])
        
    elif response.status_code == 403:
        logger.error("   FORBIDDEN")
        logger.error("   The API key might be invalid or doesn't have permission")
        logger.debug("   Response: %s", response.text[:500])
        
    else:
        logger.error("   UNEXPECTED ERROR")
        logger.debug("   Response: %s", response.text[:500])
        
except requests.exceptions.Timeout:
    logger.error("   Request timed out")
except requests.exceptions.RequestException as e:
    logger.error("   Request failed: %s", e)
except Exception as e:
    logger.error("   Unexpected error: %s", e)
    import traceback
    traceback.print_exc()

logger.info("\n" + "=" * 80)
logger.info("TEST COMPLETE")
logger.info("=" * 80)
