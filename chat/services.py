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
        "'Sorry, I don’t have relevant information for that.' "
        "Do not invent information or provide general knowledge outside the data.\n\n"
        f"Data:\n{retrieved_data}\n\n"
        f"Question:\n{user_question}"
    )

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

def get_ai_response(user_question: str, retrieved_data: str, api_key: str = None, model: str = 'gpt-4o', bot_id: int = None):
    """
    Main entry: route to provider-specific callers based on the Bot.ai_provider.
    - user_question: user question string
    - retrieved_data: the RAG context string (what the assistant must use)
    - api_key: optional global API key (used if bot doesn't have its own)
    - model: provider model string (e.g., 'gpt-4o' or 'gemini-2.5-pro')
    - bot_id: optional Bot id to use stored provider/model/key
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

    try:
        provider = provider.lower()
        if provider == 'google':
            # For Google, model examples: 'gemini-2.5-pro' or 'models/gemini-2.5-pro' accepted
            return _call_google_generative(used_api_key, model, prompt)

        elif provider == 'openai':
            return _call_openai(used_api_key, model, prompt)

        elif provider == 'openrouter':
            return _call_openrouter(used_api_key, model, prompt)

        elif provider == 'anthropic':
            return _call_anthropic(used_api_key, model, prompt)

        elif provider == 'cohere':
            return _call_cohere(used_api_key, model, prompt)

        elif provider == 'huggingface':
            # model should be huggingface repo id like "bigscience/bloom" or "meta-llama/Llama-2-13b-chat"
            return _call_huggingface(used_api_key, model, prompt)

        elif provider == 'replicate':
            # model should be replicate version id (not repo); check Replicate docs for correct value
            return _call_replicate(used_api_key, model, prompt)

        else:
            return f"⚠️ Unsupported or not-yet-implemented AI provider: {provider}"

    except requests.HTTPError as e:
        # Return a friendly explanation and log actual response if needed
        status = getattr(e.response, "status_code", None)
        try:
            body = e.response.text
        except Exception:
            body = "<unavailable>"
        # Log for server-side debugging
        print(f"HTTPError calling provider {provider}: status={status} body={body}")
        return f"⚠️ AI service error (HTTP {status})."

    except requests.RequestException as e:
        print(f"RequestException calling provider {provider}: {e}")
        return f"⚠️ AI service connection error: {str(e)}"

    except ValueError as e:
        print(f"ValueError parsing response from {provider}: {e}")
        return "⚠️ Received invalid response from AI service."

    except Exception as e:
        # catch-all
        print(f"Unexpected error in get_ai_response: {e}")
        return f"⚠️ Unexpected error: {str(e)}"
