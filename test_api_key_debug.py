"""
Diagnostic script to test API key encryption/decryption in MySQL
Run this with: python test_api_key_debug.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redbot.settings')
django.setup()

from bots.models import Bot
from django.conf import settings

print("=" * 80)
print("API KEY ENCRYPTION/DECRYPTION DIAGNOSTIC TEST")
print("=" * 80)

# Get the first bot
try:
    bot = Bot.objects.first()
    if not bot:
        print("❌ No bots found in database!")
        print("Please create a bot first via the admin panel.")
        exit(1)
    
    print(f"\n✅ Found bot: {bot.name} (ID: {bot.id})")
    print(f"   Provider: {bot.ai_provider}")
    print(f"   Model: {bot.ai_model}")
    
    # Check if API key exists
    print(f"\n📊 Database Field Info:")
    print(f"   _ai_api_key (encrypted binary): {bot._ai_api_key}")
    print(f"   Binary length: {len(bot._ai_api_key) if bot._ai_api_key else 0} bytes")
    
    # Try to decrypt
    print(f"\n🔓 Attempting to decrypt API key...")
    try:
        decrypted_key = bot.ai_api_key
        if decrypted_key:
            print(f"   ✅ Decryption successful!")
            print(f"   Key length: {len(decrypted_key)} characters")
            print(f"   Key preview: {decrypted_key[:10]}...{decrypted_key[-10:] if len(decrypted_key) > 20 else ''}")
            
            # Validate key format for Google
            if bot.ai_provider == 'google':
                if decrypted_key.startswith('AIzaSy'):
                    print(f"   ✅ Key format looks valid for Google API")
                else:
                    print(f"   ⚠️  WARNING: Key doesn't start with 'AIzaSy' (expected for Google)")
                    print(f"   Actual start: {decrypted_key[:10]}")
        else:
            print(f"   ⚠️  No API key set for this bot")
    except Exception as e:
        print(f"   ❌ Decryption FAILED: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
    
    # Test re-encryption
    print(f"\n🔄 Testing re-save (encryption roundtrip)...")
    try:
        # Save current key
        original_key = bot.ai_api_key
        if original_key:
            # Re-save the same key
            bot.ai_api_key = original_key
            bot.save()
            
            # Reload from database
            bot.refresh_from_db()
            reloaded_key = bot.ai_api_key
            
            if original_key == reloaded_key:
                print(f"   ✅ Roundtrip successful - keys match!")
            else:
                print(f"   ❌ Roundtrip FAILED - keys don't match!")
                print(f"   Original:  {original_key[:20]}...")
                print(f"   Reloaded:  {reloaded_key[:20]}...")
        else:
            print(f"   ⚠️  No key to test roundtrip")
    except Exception as e:
        print(f"   ❌ Roundtrip test FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    # Test with a dummy key
    print(f"\n🧪 Testing with dummy key...")
    try:
        test_key = "AIzaSyDummyTestKey1234567890ABCDEFGHIJ"
        print(f"   Setting test key: {test_key}")
        
        bot.ai_api_key = test_key
        bot.save()
        
        bot.refresh_from_db()
        retrieved_key = bot.ai_api_key
        
        print(f"   Retrieved key: {retrieved_key}")
        
        if test_key == retrieved_key:
            print(f"   ✅ Test key roundtrip successful!")
        else:
            print(f"   ❌ Test key roundtrip FAILED!")
            print(f"   Expected: {test_key}")
            print(f"   Got:      {retrieved_key}")
            
            # Check byte-by-byte
            if retrieved_key:
                for i, (c1, c2) in enumerate(zip(test_key, retrieved_key)):
                    if c1 != c2:
                        print(f"   First difference at position {i}: '{c1}' != '{c2}'")
                        break
    except Exception as e:
        print(f"   ❌ Test key roundtrip FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ Fatal error: {e}")
    import traceback
    traceback.print_exc()
