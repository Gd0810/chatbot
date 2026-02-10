"""
Debug script to see full Google API token usage response
"""
import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redbot.settings')
django.setup()

from bots.models import Bot
import requests
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

bot = Bot.objects.first()
api_key = bot.ai_api_key
model = "gemini-2.5-flash"

url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

payload = {
    "contents": [{"role": "user", "parts": [{"text": "Say hello in 5 words"}]}],
    "generationConfig": {
        "temperature": 0.0,
        "maxOutputTokens": 1024
    }
}

response = requests.post(url, json=payload, timeout=30)
data = response.json()

logger.info("=" * 80)
logger.info("FULL GOOGLE API RESPONSE")
logger.info("=" * 80)
logger.info("%s", json.dumps(data, indent=2))

logger.info("\n" + "=" * 80)
logger.info("USAGE METADATA ONLY")
logger.info("=" * 80)
usage = data.get("usageMetadata", {})
logger.info("%s", json.dumps(usage, indent=2))

logger.info("\n" + "=" * 80)
logger.info("AVAILABLE FIELDS")
logger.info("=" * 80)
for key, value in usage.items():
    logger.info("%s: %s", key, value)
