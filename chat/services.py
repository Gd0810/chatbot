# services.py
import json
import requests
from django.conf import settings
from bots.models import Bot

# Common timeout
REQUEST_TIMEOUT = 30

def _build_prompt(user_question: str, retrieved_data: str) -> str:
    """Construct the RAG prompt that forces the model to use ONLY retrieved_data."""
    return (
        "You are a helpful assistant. Use ONLY the following data to answer the question. "
        "Focus on content that directly relates to the question's keywords or intent. "
        "If no relevant data exists or the question is unrelated, respond exactly with: "
        "'I apologize, but I don't have specific information about that in my current knowledge base.' "
        "Do not invent information or provide general knowledge outside the data.\n\n"
        f"Data:\n{retrieved_data}\n\n"
        f"Question:\n{user_question}\n\n"
        "Important: If the Data includes any web links or labeled pages (for example: 'Service Page: https://...', "
        "or 'Contact Page: https://...'), include a short 'For more details:' section at the end of your answer listing those links that are relevant. "
        "If the user specifically asks for contact information, prioritize including contact details and the Contact Page link if present in the Data. "
        "Keep the answer concise and only use information present in the Data."
    )


def _extract_labeled_urls(retrieved_data: str) -> dict:
    """Extract labeled URLs from retrieved_data.

    Returns a dict like {'service': 'https://...', 'contact': 'https://...', 'others': [..]}.
    """
    import re
    urls = {'service': None, 'contact': None, 'others': []}
    if not retrieved_data:
        return urls

    # look for labeled forms first
    m = re.search(r"Service Page:\s*(https?://\S+)", retrieved_data, re.IGNORECASE)
    if m:
        urls['service'] = m.group(1).strip()
    m = re.search(r"Contact Page:\s*(https?://\S+)", retrieved_data, re.IGNORECASE)
    if m:
        urls['contact'] = m.group(1).strip()

    # find any other http(s) links
    found = re.findall(r"https?://[\w\-./?&=%#]+", retrieved_data)
    for u in found:
        if urls['service'] and u == urls['service']:
            continue
        if urls['contact'] and u == urls['contact']:
            continue
        if u not in urls['others']:
            urls['others'].append(u)

    return urls

def _call_google_generative(api_key: str, model: str, prompt: str):
    # Google Generative Language API (v1beta) — key typically passed as ?key=API_KEY
    full_model = model if model.startswith("models/") else f"models/{model}"
    url = f"https://generativelanguage.googleapis.com/v1beta/{full_model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.0,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 1024
        }
    }
    r = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    j = r.json()
    # navigate returned structure robustly
    candidates = j.get("candidates") or []
    if candidates:
        content = candidates[0].get("content", {})
        parts = content.get("parts") or []
        if parts:
            return parts[0].get("text") or parts[0]
    # fallback: try common fields
    return j.get("output", {}).get("text") or j.get("response", "") or json.dumps(j)

def _call_openai(api_key: str, model: str, prompt: str):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 1024
    }
    r = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    j = r.json()
    # Standard OpenAI response parsing
    choices = j.get("choices") or []
    if choices:
        msg = choices[0].get("message") or {}
        return msg.get("content") or choices[0].get("text") or json.dumps(j)
    return j.get("error", {}).get("message") or json.dumps(j)

def _call_openrouter(api_key: str, model: str, prompt: str):
    # OpenRouter implements OpenAI-like chat endpoint
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 1024
    }
    r = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    j = r.json()
    choices = j.get("choices") or []
    if choices:
        return choices[0].get("message", {}).get("content") or choices[0].get("text") or json.dumps(j)
    return json.dumps(j)

def _call_anthropic(api_key: str, model: str, prompt: str):
    # Anthropic supports /v1/messages with messages array (see current docs)
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.0
    }
    r = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    j = r.json()
    # try messages-like response parsing
    if "completion" in j:
        return j.get("completion")
    # Traditional Claude style: 'output' or top-level text
    if "message" in j:
        return j["message"].get("content") or json.dumps(j)
    # last fallback
    return j.get("content") or json.dumps(j)

def _call_cohere(api_key: str, model: str, prompt: str):
    # Cohere generate endpoint
    url = "https://api.cohere.ai/v1/generate"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "prompt": prompt,
        "max_tokens": 1024,
        "temperature": 0.0,
        "return_likelihoods": "NONE"
    }
    r = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    j = r.json()
    generations = j.get("generations") or []
    if generations:
        return generations[0].get("text") or json.dumps(j)
    return json.dumps(j)

def _call_huggingface(api_key: str, model: str, prompt: str):
    # Hugging Face Inference: model-specific endpoint
    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"inputs": prompt, "options": {"wait_for_model": True}}
    r = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    j = r.json()
    # HF sometimes returns a list of generated outputs or a dict with 'generated_text'
    if isinstance(j, list) and len(j) > 0:
        # e.g., [{"generated_text": "..."}]
        if isinstance(j[0], dict):
            return j[0].get("generated_text") or json.dumps(j)
        return str(j[0])
    if isinstance(j, dict):
        return j.get("generated_text") or j.get("text") or json.dumps(j)
    return json.dumps(j)

def _call_replicate(api_key: str, model: str, prompt: str):
    # Replicate uses a /v1/predictions endpoint and model-specific inputs
    url = "https://api.replicate.com/v1/predictions"
    headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
    # Simple generic payload — many Replicate models expect 'input' dict; you may need to adapt per model
    payload = {"version": model, "input": {"prompt": prompt}}
    r = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    j = r.json()
    # Replicate returns a prediction object that may have output or urls
    if "output" in j:
        output = j["output"]
        if isinstance(output, list):
            return output[0]
        return output
    # If prediction id provided, user may want to poll — but we keep simple
    return json.dumps(j)

# services.py (replace only the get_ai_response function)

def get_ai_response(user_question: str, retrieved_data: str, api_key: str = None, model: str = 'gpt-4o', bot_id: int = None):
    """
    Main entry: route to provider-specific callers based on the Bot.ai_provider.
    Appends a clickable 'For more details:' section with hyperlinks if labeled URLs are found
    in retrieved_data (Service Page / Contact Page / Others).
    """
    try:
        bot = Bot.objects.get(id=bot_id) if bot_id else None
    except Bot.DoesNotExist:
        return "⚠️ Bot not found."

    provider = bot.ai_provider if bot else 'google'
    # prefer bot's key if stored
    used_api_key = (bot.ai_api_key if bot and bot.ai_api_key else api_key)
    if not used_api_key:
        return "⚠️ No API key provided."

    prompt = _build_prompt(user_question, retrieved_data)
    answer_text = ""

    try:
        provider = provider.lower()
        if provider == 'google':
            # For Google, model examples: 'gemini-2.5-pro' or 'models/gemini-2.5-pro' accepted
            answer_text = _call_google_generative(used_api_key, model, prompt)

        elif provider == 'openai':
            answer_text = _call_openai(used_api_key, model, prompt)

        elif provider == 'openrouter':
            answer_text = _call_openrouter(used_api_key, model, prompt)

        elif provider == 'anthropic':
            answer_text = _call_anthropic(used_api_key, model, prompt)

        elif provider == 'cohere':
            answer_text = _call_cohere(used_api_key, model, prompt)

        elif provider == 'huggingface':
            # model should be huggingface repo id like "bigscience/bloom" or "meta-llama/Llama-2-13b-chat"
            answer_text = _call_huggingface(used_api_key, model, prompt)

        elif provider == 'replicate':
            # model should be replicate version id (not repo); check Replicate docs for correct value
            answer_text = _call_replicate(used_api_key, model, prompt)

        else:
            return f"⚠️ Unsupported or not-yet-implemented AI provider: {provider}"

    except requests.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        try:
            body = e.response.text
        except Exception:
            body = "<unavailable>"
        print(f"HTTPError calling provider {provider}: status={status} body={body}")
        
        # Build user-friendly error message based on plan
        error_msg = f"⚠️ AI service error (HTTP {status})."
        try:
            if bot and bot.workspace:
                ws = bot.workspace
                plan = ws.active_plan
                
                # Add plan-specific suggestions
                if plan and plan.bundle == 'FULL':
                    error_msg += " However, you may get better assistance by switching to our Live Chat or Q&A bot using the menu above."
                
                # Add WhatsApp link if enabled (for ALL plans)
                if ws.enable_whatsapp_number_in_chat and ws.whatsapp_number:
                    clean_number = ws.whatsapp_number.replace(' ', '').replace('-', '')
                    wa_link = f'<a href="https://wa.me/{clean_number}" style="color:#5A4FCF;text-decoration:underline;font-weight:600" target="_blank"><iconify-icon icon="logos:whatsapp-icon" style="vertical-align: middle; margin-right: 2px; font-size: 1.6em;"></iconify-icon>{ws.whatsapp_number}</a>'
                    error_msg += f" For further details, WhatsApp this number: {wa_link}"
        except Exception:
            pass
        
        return error_msg

    except requests.RequestException as e:
        print(f"RequestException calling provider {provider}: {e}")
        
        # Build user-friendly error message based on plan
        error_msg = f"⚠️ AI service connection error."
        try:
            if bot and bot.workspace:
                ws = bot.workspace
                plan = ws.active_plan
                
                # Add plan-specific suggestions
                if plan and plan.bundle == 'FULL':
                    error_msg += " However, you may get better assistance by switching to our Live Chat or Q&A bot using the menu above."
                
                # Add WhatsApp link if enabled (for ALL plans)
                if ws.enable_whatsapp_number_in_chat and ws.whatsapp_number:
                    clean_number = ws.whatsapp_number.replace(' ', '').replace('-', '')
                    wa_link = f'<a href="https://wa.me/{clean_number}" style="color:#5A4FCF;text-decoration:underline;font-weight:600" target="_blank"><iconify-icon icon="logos:whatsapp-icon" style="vertical-align: middle; margin-right: 2px; font-size: 1.6em;"></iconify-icon>{ws.whatsapp_number}</a>'
                    error_msg += f" For further details, WhatsApp this number: {wa_link}"
        except Exception:
            pass
        
        return error_msg

    except ValueError as e:
        print(f"ValueError parsing response from {provider}: {e}")
        
        # Build user-friendly error message based on plan
        error_msg = "⚠️ Received invalid response from AI service."
        try:
            if bot and bot.workspace:
                ws = bot.workspace
                plan = ws.active_plan
                
                # Add plan-specific suggestions
                if plan and plan.bundle == 'FULL':
                    error_msg += " However, you may get better assistance by switching to our Live Chat or Q&A bot using the menu above."
                
                # Add WhatsApp link if enabled (for ALL plans)
                if ws.enable_whatsapp_number_in_chat and ws.whatsapp_number:
                    clean_number = ws.whatsapp_number.replace(' ', '').replace('-', '')
                    wa_link = f'<a href="https://wa.me/{clean_number}" style="color:#5A4FCF;text-decoration:underline;font-weight:600" target="_blank"><iconify-icon icon="logos:whatsapp-icon" style="vertical-align: middle; margin-right: 2px; font-size: 1.6em;"></iconify-icon>{ws.whatsapp_number}</a>'
                    error_msg += f" For further details, WhatsApp this number: {wa_link}"
        except Exception:
            pass
        
        return error_msg

    except Exception as e:
        print(f"Unexpected error in get_ai_response: {e}")
        
        # Build user-friendly error message based on plan
        error_msg = "⚠️ Unexpected error occurred."
        try:
            if bot and bot.workspace:
                ws = bot.workspace
                plan = ws.active_plan
                
                # Add plan-specific suggestions
                if plan and plan.bundle == 'FULL':
                    error_msg += " However, you may get better assistance by switching to our Live Chat or Q&A bot using the menu above."
                
                # Add WhatsApp link if enabled (for ALL plans)
                if ws.enable_whatsapp_number_in_chat and ws.whatsapp_number:
                    clean_number = ws.whatsapp_number.replace(' ', '').replace('-', '')
                    wa_link = f'<a href="https://wa.me/{clean_number}" style="color:#5A4FCF;text-decoration:underline;font-weight:600" target="_blank"><iconify-icon icon="logos:whatsapp-icon" style="vertical-align: middle; margin-right: 2px; font-size: 1.6em;"></iconify-icon>{ws.whatsapp_number}</a>'
                    error_msg += f" For further details, WhatsApp this number: {wa_link}"
        except Exception:
            pass
        
        return error_msg

    # Post-process: convert plain URLs to clickable links and avoid duplicates
    try:
        import re
        # Normalize to string
        answer_text = "" if answer_text is None else str(answer_text)
        link_style = 'style="color:#5A4FCF;text-decoration:underline;font-weight:600" rel="noopener noreferrer" target="_blank"'

        # If the model responded with the 'no relevant information' phrase, try a deterministic
        # fallback: extract contact/service links, emails, phones, and address from retrieved_data
        no_info_variants = [
            "I apologize, but I don't have specific information about that in my current knowledge base.",
            "I don't have specific information about that",
            "Sorry, I don't have relevant information for that.",
        ]

        workspace_name = None
        try:
            if bot and getattr(bot, 'workspace', None):
                workspace_name = getattr(bot.workspace, 'name', None)
        except Exception:
            workspace_name = None

        if any(v in answer_text for v in no_info_variants):
            # Check if user is specifically asking for contact information
            contact_keywords = ['contact', 'phone', 'email', 'address', 'reach', 'call', 'location']
            is_contact_query = any(keyword in user_question.lower() for keyword in contact_keywords)
            
            if is_contact_query:
                # User is asking for contact info - try to extract it
                urls = _extract_labeled_urls(retrieved_data)
                phones = re.findall(r"\+?\d[\d\-\s\(\)]{6,}\d", retrieved_data or "")
                emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", retrieved_data or "")
                addr_match = re.search(r"Address[:\-]?\s*(.+)", retrieved_data or "", re.IGNORECASE)

                # If we found any contact-like info, build a concise contact answer
                if urls.get('contact') or phones or emails or addr_match or urls.get('service') or urls.get('others'):
                    parts = []
                    if phones:
                        uniq_phones = list(dict.fromkeys(phones))
                        parts.append("Phones: " + ", ".join(uniq_phones))
                    if emails:
                        uniq_emails = list(dict.fromkeys(emails))
                        parts.append("Emails: " + ", ".join(uniq_emails))
                    if addr_match:
                        parts.append("Address: " + addr_match.group(1).strip())

                    # Links (prefer labeled contact/service)
                    links_html = []
                    if urls.get('contact'):
                        links_html.append(f'Contact Page: <a href="{urls["contact"]}" {link_style}>Check this link</a>')
                    if urls.get('service'):
                        links_html.append(f'Service Page: <a href="{urls["service"]}" {link_style}>Check this link</a>')
                    for o in urls.get('others', []):
                        links_html.append(f'<a href="{o}" {link_style}>Check this link</a>')

                    if links_html:
                        parts.append('For more details: ' + ' '.join(links_html))

                    # Prepend a short header
                    header = ""
                    if workspace_name:
                        header = f"Here are the contact details I found for {workspace_name}:\n"
                    else:
                        header = "Here are the contact details I found:\n"
                    
                    answer_text = header + "\n".join(parts)
                else:
                    # No contact info found even though they asked - suggest bot switching
                    try:
                        if bot and bot.workspace:
                            plan = bot.workspace.active_plan
                            if plan and plan.bundle == 'FULL':
                                answer_text = (
                                    "I apologize, but I don't have specific contact information in my current knowledge base. "
                                    "However, you may get better assistance by switching to our Live Chat or Q&A bot using the menu above. "
                                    "<span class='trigger-bot-switcher' style='display:none;'>TRIGGER_SWITCHER</span>"
                                )
                            else:
                                answer_text = "I apologize, but I don't have specific information about that in my current knowledge base."
                        else:
                            answer_text = "I apologize, but I don't have specific information about that in my current knowledge base."
                    except Exception:
                        answer_text = "I apologize, but I don't have specific information about that in my current knowledge base."
            else:
                # NOT a contact query - suggest switching bots for FULL plan
                try:
                    if bot and bot.workspace:
                        ws = bot.workspace
                        plan = ws.active_plan
                        
                        # Build base message based on plan
                        if plan and plan.bundle == 'FULL':
                            answer_text = (
                                "I apologize, but I don't have specific information about that in my current knowledge base. "
                                "However, you may get better assistance by switching to our Live Chat or Q&A bot using the menu above."
                            )
                            # Add bot switcher trigger for FULL plan
                            answer_text += " <span class='trigger-bot-switcher' style='display:none;'>TRIGGER_SWITCHER</span>"
                        else:
                            # For all other plans (AI_ONLY, LIVE_QA, etc.)
                            answer_text = "I apologize, but I don't have specific information about that in my current knowledge base."
                        
                        # Add WhatsApp link if enabled (for ALL plans)
                        if ws.enable_whatsapp_number_in_chat and ws.whatsapp_number:
                            # Clean the number (remove spaces, dashes)
                            clean_number = ws.whatsapp_number.replace(' ', '').replace('-', '')
                            wa_link = f'<a href="https://wa.me/{clean_number}" style="color:#5A4FCF;text-decoration:underline;font-weight:600" target="_blank"><iconify-icon icon="logos:whatsapp-icon" style="vertical-align: middle; margin-right: 2px; font-size: 1.6em;"></iconify-icon>{ws.whatsapp_number}</a>'
                            answer_text += f" For further details, WhatsApp this number: {wa_link}"
                    else:
                        answer_text = "I apologize, but I don't have specific information about that in my current knowledge base."
                except Exception:
                    answer_text = "I apologize, but I don't have specific information about that in my current knowledge base."


        # Normalize phrasing: prefer 'Our company' when the model used 'your company'
        if workspace_name:
            answer_text = re.sub(r"\b[Yy]our company\b", "Our company", answer_text)
            answer_text = re.sub(r"\bthis company\b", "our company", answer_text, flags=re.IGNORECASE)

        # 1. Convert plain URLs in answer to clickable links (if not already <a> tags)
        # First, remove any line breaks within URLs (AI sometimes splits long URLs)
        # Match URLs that might be split across lines
        answer_text = re.sub(r'(https?://[^\s<>"\']+)\s*/\s*([^\s<>"\']+)', r'\1/\2', answer_text)
        
        # Find all plain URLs (https://...) that are not already in <a> tags
        # Use negative lookbehind to avoid matching URLs inside href="..."
        # Match full URLs including paths, query params, and fragments
        plain_urls = re.findall(r'(?<!href=")(?<!href=\')https?://[^\s<>"\']+', answer_text)
        for url in plain_urls:
            # Clean up trailing punctuation that might not be part of the URL
            # Remove trailing periods, commas, etc. unless they're part of a file extension
            cleaned_url = re.sub(r'[.,;:!?]+$', '', url)
            # Only replace if not already inside an anchor tag
            # Check if URL appears in a context like href="URL" or href='URL'
            if f'href="{cleaned_url}"' not in answer_text and f"href='{cleaned_url}'" not in answer_text:
                answer_text = answer_text.replace(url, f'<a href="{cleaned_url}" {link_style}>{cleaned_url}</a>')

        # 2. Remove duplicate "For more details:" sections (keep only first)
        # Split by "For more details:" and rejoin with only one
        parts = answer_text.split('For more details:')
        if len(parts) > 1:
            # Keep first part and only first "For more details:" section
            answer_text = parts[0] + 'For more details:' + parts[1]

        return answer_text

    except Exception as e:
        print(f"Post-process error: {e}")
        # If post-process fails, still return the model's raw answer
        return answer_text or ""