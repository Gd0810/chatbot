"""
Diagnostic script to test API key encryption/decryption in MySQL
Run this with: python test_api_key_debug.py
"""

import os
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redbot.settings')
django.setup()

from bots.models import Bot
from django.conf import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("API KEY ENCRYPTION/DECRYPTION DIAGNOSTIC TEST")
logger.info("=" * 80)

# Get the first bot
try:
    bot = Bot.objects.first()
    if not bot:
        logger.error("No bots found in database!")
        logger.error("Please create a bot first via the admin panel.")
        exit(1)
    
    logger.info("\n✅ Found bot: %s (ID: %s)", bot.name, bot.id)
    logger.info("   Provider: %s", bot.ai_provider)
    logger.info("   Model: %s", bot.ai_model)
    
    # Check if API key exists
    logger.info("\n📊 Database Field Info:")
    logger.info("   _ai_api_key (encrypted binary): %s", bot._ai_api_key)
    logger.info("   Binary length: %s bytes", len(bot._ai_api_key) if bot._ai_api_key else 0)
    
    # Try to decrypt
    logger.info("\n🔓 Attempting to decrypt API key...")
    try:
        decrypted_key = bot.ai_api_key
        if decrypted_key:
            logger.info("   ✅ Decryption successful!")
            logger.info("   Key length: %s characters", len(decrypted_key))
            logger.info("   Key preview: %s...%s", decrypted_key[:10], decrypted_key[-10:] if len(decrypted_key) > 20 else '')
            
            # Validate key format for Google
            if bot.ai_provider == 'google':
                if decrypted_key.startswith('AIzaSy'):
                    logger.info("   ✅ Key format looks valid for Google API")
                else:
                    logger.warning("   ⚠️  WARNING: Key doesn't start with 'AIzaSy' (expected for Google)")
                    logger.warning("   Actual start: %s", decrypted_key[:10])
        else:
            logger.warning("   ⚠️  No API key set for this bot")
    except Exception as e:
        logger.error("   ❌ Decryption FAILED: %s", e)
        logger.error("   Error type: %s", type(e).__name__)
        import traceback
        traceback.print_exc()
    
    # Test re-encryption
    logger.info("\n🔄 Testing re-save (encryption roundtrip)...")
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
                logger.info("   ✅ Roundtrip successful - keys match!")
            else:
                logger.error("   ❌ Roundtrip FAILED - keys don't match!")
                logger.error("   Original:  %s...", original_key[:20])
                logger.error("   Reloaded:  %s...", reloaded_key[:20])
        else:
            logger.warning("   ⚠️  No key to test roundtrip")
    except Exception as e:
        logger.error("   ❌ Roundtrip test FAILED: %s", e)
        import traceback
        traceback.print_exc()
    
    # Test with a dummy key
    logger.info("\n🧪 Testing with dummy key...")
    try:
        test_key = "AIzaSyDummyTestKey1234567890ABCDEFGHIJ"
        logger.info("   Setting test key: %s", test_key)
        
        bot.ai_api_key = test_key
        bot.save()
        
        bot.refresh_from_db()
        retrieved_key = bot.ai_api_key
        
        logger.info("   Retrieved key: %s", retrieved_key)
        
        if test_key == retrieved_key:
            logger.info("   ✅ Test key roundtrip successful!")
        else:
            logger.error("   ❌ Test key roundtrip FAILED!")
            logger.error("   Expected: %s", test_key)
            logger.error("   Got:      %s", retrieved_key)
            
            # Check byte-by-byte
            if retrieved_key:
                for i, (c1, c2) in enumerate(zip(test_key, retrieved_key)):
                    if c1 != c2:
                        logger.error("   First difference at position %s: '%s' != '%s'", i, c1, c2)
                        break
    except Exception as e:
        logger.error("   ❌ Test key roundtrip FAILED: %s", e)
        import traceback
        traceback.print_exc()
    
    logger.info("\n" + "=" * 80)
    logger.info("DIAGNOSTIC COMPLETE")
    logger.info("=" * 80)
    
except Exception as e:
    logger.error("\n❌ Fatal error: %s", e)
    import traceback
    traceback.print_exc()
