# embed/views.py (update: include jwt_exp in cfg and pre-render welcome_text)
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
            allowed = True; allowed_by = 'allowed_domains'
        elif origin_host and origin_host == request_host:
            allowed = True; allowed_by = 'same_origin'
        elif settings.DEBUG and origin_host and _is_local_host(origin_host):
            allowed = True; allowed_by = 'debug_local'
        elif settings.DEBUG and not origin:
            allowed = True; allowed_by = 'debug_no_origin'

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
            exp = now + timedelta(minutes=30)  # 30 min TTL
            payload = {
                'bot_id': bot.id,
                'public_key': public_key,
                'iat': int(now.timestamp()),
                'nbf': int((now - timedelta(seconds=5)).timestamp()),
                'exp': int(exp.timestamp()),
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
            'workspace_enable_reset_button': getattr(ws, 'enable_reset_button', False),
        }
        print(f"[embed.widget] pk={public_key} debug={debug}")

        # Welcome text (no template filter use)
        default_welcome = "Hi! I'm {name}. How can I help you?"
        welcome_raw = bot.ui_welcome_message or default_welcome
        welcome_text = welcome_raw.replace("{name}", bot.name)

        cfg = {
            'jwt': token or '',
            'botId': bot.id,
            'botName': bot.name,
            'publicKey': public_key,
            'origin': origin,
            'jwt_exp': exp_ts,                # pass exp for auto-refresh
            'sound': bot.ui_sound_enabled,    # for sound toggle
            # expose workspace-level UI toggles for client debug/fallback
            'workspace_enable_reset_button': getattr(ws, 'enable_reset_button', False),
        }

        # Bot footer: use workspace setting and first footer for workspace if available
        footer = None
        try:
            if getattr(ws, 'bot_footer', False):
                footer = getattr(ws, 'bot_footers', None)
                if footer is not None:
                    footer = footer.first()
        except Exception:
            footer = None

        # Enquiry form: check if workspace has enabled it
        enquiry_form_enabled = getattr(ws, 'enable_enquiry_form', False)

        # Render + no-cache headers
        response = render(request, 'embed/widget.html', {
            'public_key': public_key,
            'bot': bot,
            'workspace': ws,
            'bot_footer': footer,
            'enquiry_form_enabled': enquiry_form_enabled,
            'jwt': token,
            'blocked': bool(block_reason),
            'block_reason': block_reason,
            'block_msg': block_msg,
            'origin': origin,
            'welcome_text': welcome_text,
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


@xframe_options_exempt
def bot_config_api(request, public_key):
    """
    JSON API endpoint that returns bot configuration for embedding.
    Client-side embed script calls this to get all bot settings dynamically.
    URL: /embed/config/<public_key>/ returns JSON with all UI settings
    """
    try:
        bot = Bot.objects.get(public_key=public_key)
        return HttpResponse(
            __import__('json').dumps({
                'public_key': bot.public_key,
                'primary_color': bot.ui_primary_color or '',
                'bg_color': bot.ui_bg_color or '',
                'font_family': bot.ui_font_family or '',
                'font_size': bot.ui_font_size or 14,
                'welcome_message': bot.ui_welcome_message or '',
                'sound_enabled': bool(bot.ui_sound_enabled),
                'animation_speed': bot.ui_animation_speed or 'normal',
                'widget_position': bot.ui_widget_position or 'bottom-right',
            }, default=str),
            content_type='application/json'
        )
    except Bot.DoesNotExist:
        return HttpResponse('{"error": "Bot not found"}', status=404, content_type='application/json')
    except Exception as e:
        return HttpResponse(f'{{"error": "{str(e)}"}}', status=500, content_type='application/json')


def test_embed_page(request, public_key=None):
    """
    Serve a minimal test page for the embed.
    User's actual page only needs a placeholder div + 2 lines of script.
    URL: /embed/test/ or /embed/test/<public_key>/
    """
    bot = None
    if public_key:
        try:
            bot = Bot.objects.get(public_key=public_key)
        except Bot.DoesNotExist:
            pass
    if not bot:
        try:
            bot = Bot.objects.first()
        except Exception:
            pass
    
    return render(request, 'embed/test.html', {'bot': bot})


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def save_enquiry(request):
    """
    API endpoint to save user enquiry (name/phone/email) from widget.
    Expects POST with: public_key, name, phone, email
    Returns JSON response.
    CSRF is exempted because this is called from an iframe (cross-origin context).
    Security is maintained by validating the bot's public_key exists.
    """
    if request.method != 'POST':
        return HttpResponse('{"error": "Method not allowed"}', status=405, content_type='application/json')
    
    try:
        import json
        data = json.loads(request.body)
        public_key = data.get('public_key', '')
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()
        
        # Find bot by public key
        bot = Bot.objects.get(public_key=public_key)
        ws = bot.workspace
        
        # Check if enquiry form is enabled for this workspace
        if not getattr(ws, 'enable_enquiry_form', False):
            return HttpResponse('{"error": "Enquiry form is not enabled"}', status=400, content_type='application/json')
        
        # Save enquiry (at least one field must be filled)
        if name or phone or email:
            from bots.models import BotEnquiry
            enquiry = BotEnquiry.objects.create(
                workspace=ws,
                name=name or None,
                phone=phone or None,
                email=email or None
            )
            return HttpResponse(
                __import__('json').dumps({'success': True, 'enquiry_id': enquiry.id}),
                content_type='application/json'
            )
        else:
            return HttpResponse('{"error": "At least one field is required"}', status=400, content_type='application/json')
    
    except Bot.DoesNotExist:
        return HttpResponse('{"error": "Bot not found"}', status=404, content_type='application/json')
    except Exception as e:
        return HttpResponse(f'{{"error": "{str(e)}"}}', status=500, content_type='application/json')