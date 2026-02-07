"""
Debug script to see full Google API token usage response
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redbot.settings')
django.setup()

from bots.models import Bot
import requests
import json

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

print("=" * 80)
print("FULL GOOGLE API RESPONSE")
print("=" * 80)
print(json.dumps(data, indent=2))

print("\n" + "=" * 80)
print("USAGE METADATA ONLY")
print("=" * 80)
usage = data.get("usageMetadata", {})
print(json.dumps(usage, indent=2))

print("\n" + "=" * 80)
print("AVAILABLE FIELDS")
print("=" * 80)
for key, value in usage.items():
    print(f"{key}: {value}")
