# chat/views.py
import json
import re
from urllib.parse import urlparse
from time import time as epoch_time

from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import requests
import numpy as np
from django.utils.text import slugify
from knowledge.models import Chunk
from sentence_transformers import SentenceTransformer
import requests
import numpy as np
from django.utils.text import slugify
from knowledge.models import Chunk
from sentence_transformers import SentenceTransformer
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from bots.models import Bot
from accounts.models import Workspace
from knowledge.models import KnowledgeSource
from .services import get_ai_response
from .greeting import _handle_greeting


def _tokenize(text: str):
    return re.findall(r"\w+", (text or "").lower())

# Load embedding model once (you can change it to match your chunk embedding model)
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str):
    """Convert text into vector embedding."""
    if not text:
        return []
    emb = embedding_model.encode(text)
    return emb.tolist()


def _get_relevant_data(bot, user_question: str, top_k: int = 3):
    """Retrieve semantically relevant chunks from Qdrant Cloud."""
    if not user_question:
        return "", []

    # ✅ FIXED: use knowledge_source__bot instead of source__bot
    chunks = Chunk.objects.filter(knowledge_source__bot=bot)
    if not chunks.exists():
        print("⚠️ No chunks found for this bot.")
        return "", []

    # Pick first chunk just to get Qdrant connection info
    first_chunk = chunks.first()
    if not first_chunk.qdrant_url or not first_chunk.qdrant_api_key:
        print("⚠️ Qdrant credentials missing for this bot.")
        return "", []

    # Step 1: Embed the user's question
    query_vector = embed_text(user_question)

    # Step 2: Build request
    headers = {
        "Content-Type": "application/json",
        "api-key": first_chunk.qdrant_api_key,
    }

    collection_name = first_chunk.collection_name or slugify(bot.name)
    search_url = f"{first_chunk.qdrant_url}/collections/{collection_name}/points/search"

    payload = {
        "vector": query_vector,
        "limit": top_k,
        "with_payload": True,
    }

    try:
        response = requests.post(search_url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        results = response.json().get("result", [])
    except Exception as e:
        print(f"❌ Qdrant query failed: {e}")
        return "", []

    # Step 3: Collect top text chunks
    retrieved_texts = []
    source_ids = []

    for match in results:
        payload = match.get("payload", {})
        txt = payload.get("text")
        src_id = payload.get("knowledge_source_id")
        if txt:
            retrieved_texts.append(txt)
        if src_id:
            source_ids.append(src_id)

    retrieved_data = "\n".join(retrieved_texts)
    return retrieved_data, source_ids





def _extract_origin(request):
    origin = request.META.get('HTTP_ORIGIN') or ''
    if not origin:
        # Try Referer
        ref = request.META.get('HTTP_REFERER') or ''
        try:
            p = urlparse(ref)
            if p.scheme and p.netloc:
                origin = f"{p.scheme}://{p.netloc}"
        except Exception:
            pass
    return origin






@csrf_exempt
def ChatAPI(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # Parse JSON
        try:
            payload_data = request.body.decode('utf-8') if request.body else "{}"
            data = json.loads(payload_data)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON body'}, status=400)

        message = data.get('message', '')
        jwt_token = data.get('jwt')

        print(f"Received chat: {message!r}")

        if not jwt_token:
            return JsonResponse({'error': 'Missing JWT'}, status=401)

        # Validate JWT with some leeway (helps dev clock skew)
        try:
            jwt_leeway = getattr(settings, 'REDBOT_JWT_LEEWAY', 300)  # seconds
            leeway = jwt_leeway if settings.DEBUG else min(jwt_leeway, 120)
            payload = jwt.decode(jwt_token, settings.SECRET_KEY, algorithms=['HS256'], leeway=leeway)

            # Optional explicit exp check for extra logging
            exp = payload.get('exp')
            if exp:
                now = int(epoch_time())
                if now > int(exp) + leeway:
                    print(f"[ChatAPI] Manual exp check failed: now={now} exp={exp} leeway={leeway}")
                    return JsonResponse({'error': 'Token expired'}, status=401)

        except ExpiredSignatureError:
            # Log details for debugging
            try:
                unverified = jwt.decode(jwt_token, options={'verify_signature': False})
                exp = unverified.get('exp')
                now = int(epoch_time())
                delta = (now - int(exp)) if exp else None
                print(f"[ChatAPI] Token expired: now={now} exp={exp} delta={delta}s")
            except Exception:
                pass
            return JsonResponse({'error': 'Token expired'}, status=401)
        except InvalidTokenError as e:
            print(f"[ChatAPI] Invalid token: {e}")
            return JsonResponse({'error': f'Invalid token: {e}'}, status=401)

        # Locate bot from token
        bot_obj = None
        if payload.get('bot_id'):
            bot_obj = Bot.objects.filter(id=payload['bot_id']).first()
        if not bot_obj and payload.get('public_key'):
            bot_obj = Bot.objects.filter(public_key=payload['public_key']).first()
        if not bot_obj:
            return JsonResponse({'error': 'Bot not found'}, status=404)

        # Enforce origin (dev-friendly + same-origin allowed)
        origin = _extract_origin(request)
        allow = True  # default allow if no origin is present
        if origin:
            try:
                origin_host = (urlparse(origin).hostname or '').lower()
            except Exception:
                origin_host = ''
            request_host = (request.get_host().split(':')[0] or '').lower()

            allow = False
            if origin_host and origin_host == request_host:
                allow = True  # same-origin
            elif bot_obj.is_origin_allowed(origin):
                allow = True  # allowed by admin list
            elif settings.DEBUG and origin_host in ('localhost', '127.0.0.1'):
                allow = True  # dev convenience

            if not allow:
                return JsonResponse({'error': 'Origin not allowed for this bot.'}, status=403)

        # Enforce workspace/bot/plan
        if not bot_obj.is_enabled:
            return JsonResponse({"answer": "Bot is disabled by the owner.", "sources": []}, status=200)

        ws = bot_obj.workspace
        if not ws.approved:
            return JsonResponse({"answer": "This workspace is not approved yet.", "sources": []}, status=200)
        if not ws.is_operational:
            return JsonResponse({"answer": "You’re out of plan. Please renew to continue.", "sources": []}, status=200)

        ap = bot_obj.active_plan
        if not ap or not ap.includes_ai:
            return JsonResponse({"answer": "AI chat is not included in this plan.", "sources": []}, status=200)

        # Greetings
        # 🗣️ Greetings Handling (from greeting.py)
        greeting_response = _handle_greeting(message, bot_obj, ws)
        if greeting_response:
            return JsonResponse({"answer": greeting_response, "sources": []})


        # Retrieve knowledge and call AI
        retrieved_data, source_ids = _get_relevant_data(bot_obj, message, top_k=1)
        answer = get_ai_response(
            user_question=message,
            retrieved_data=retrieved_data,
            api_key=bot_obj.ai_api_key,
            model=bot_obj.ai_model,
            bot_id=bot_obj.id,
        )
        return JsonResponse({"answer": answer, "sources": source_ids})

    except Exception as e:
        print(f"ChatAPI exception: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def chat_page_view(request):
    return render(request, 'chat.html')