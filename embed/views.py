# embed/views.py
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_exempt

import jwt
from datetime import timedelta, datetime, timezone as dt_timezone
from urllib.parse import urlparse

from bots.models import Bot


def _host_from_url(url: str) -> str:
    try:
        return (urlparse(url).hostname or '').lower()
    except Exception:
        return ''


def _is_local_host(host: str) -> bool:
    return host in ('localhost', '127.0.0.1')


@xframe_options_exempt
def widget_iframe(request, public_key):
    """
    Embeddable widget:
    - Same-origin always allowed
    - In DEBUG, localhost/127.0.0.1 allowed
    - Else, origin must match Bot.allowed_domains (hostnames only)
    - Blocks if bot disabled, workspace not approved, or plan inactive
    - Issues short-lived JWT for /api/chat/ when allowed
    """
    try:
        bot = Bot.objects.get(public_key=public_key)
        ws = bot.workspace

        origin = request.GET.get('origin', '') or ''
        origin_host = _host_from_url(origin)
        request_host = (request.get_host().split(':')[0] or '').lower()

        # Domain allowance
        allowed = False
        allowed_by = None
        if origin and bot.is_origin_allowed(origin):
            allowed = True
            allowed_by = 'allowed_domains'
        elif origin_host and origin_host == request_host:
            allowed = True
            allowed_by = 'same_origin'
        elif settings.DEBUG and origin_host and _is_local_host(origin_host):
            allowed = True
            allowed_by = 'debug_local'
        elif settings.DEBUG and not origin:
            allowed = True
            allowed_by = 'debug_no_origin'

        # Block reasons
        block_reason = None
        block_msg = None
        if not allowed:
            block_reason = 'domain'
            block_msg = "This domain is not allowed for this bot."
        elif not bot.is_enabled:
            block_reason = 'disabled'
            block_msg = "This bot is disabled by the owner."
        elif not ws.approved:
            block_reason = 'not_approved'
            block_msg = "Workspace is not approved yet."
        elif not ws.is_operational:
            ap = ws.active_plan
            if ap and ap.term == 'LIMITED' and ap.end_at and timezone.now() > ap.end_at:
                block_reason = 'out_of_plan'
                block_msg = "You’re out of plan."
            else:
                block_reason = 'inactive'
                block_msg = "Workspace is not active."

        # Token
        token = None
        exp_ts = None
        if block_reason is None:
            now = datetime.now(dt_timezone.utc)
            exp = now + timedelta(minutes=30)  # 30 min TTL for dev
            payload = {
                'bot_id': bot.id,
                'public_key': public_key,
                'iat': int(now.timestamp()),             # issued at (UTC seconds)
                'nbf': int((now - timedelta(seconds=5)).timestamp()),  # not before (5s skew)
                'exp': int(exp.timestamp()),             # expires at
            }
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            exp_ts = payload['exp']

        # Debug for page and server
        ap = ws.active_plan
        debug = {
            'origin': origin,
            'origin_host': origin_host,
            'request_host': request_host,
            'allowed': allowed,
            'allowed_by': allowed_by,
            'blocked': bool(block_reason),
            'block_reason': block_reason,
            'bot_is_enabled': bot.is_enabled,
            'ws_approved': ws.approved,
            'ws_operational': ws.is_operational,
            'plan_bundle': ap.bundle if ap else None,
            'plan_term': ap.term if ap else None,
            'plan_active_now': ap.is_current_active if ap else None,
            'has_jwt': bool(token),
            'jwt_exp': exp_ts,
        }
        print(f"[embed.widget] pk={public_key} debug={debug}")

        cfg = {
            'jwt': token or '',
            'botId': bot.id,
            'botName': bot.name,
            'publicKey': public_key,
            'origin': origin,
        }

        # Render + no-cache headers (avoid stale JWTs)
        response = render(request, 'embed/widget.html', {
            'public_key': public_key,
            'bot': bot,
            'jwt': token,                 # used in template guard
            'blocked': bool(block_reason),
            'block_reason': block_reason,
            'block_msg': block_msg,
            'origin': origin,
            'cfg': cfg,
            'debug': debug,
            'debug_on': settings.DEBUG,
        })
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    except Bot.DoesNotExist:
        return HttpResponse("Bot not found", status=404)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)
    
   
