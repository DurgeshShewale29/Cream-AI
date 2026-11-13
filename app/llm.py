import logging
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT = 30
RETRIES = 3

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

DEFAULT_MODELS = {"groq": "llama-3.3-70b-versatile", "gemini": "gemini-2.5-flash"}
KEY_NAMES = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY"}


class LLMError(Exception):
    """Anything that goes wrong when asking the model, with a message the user can act on."""


def get_provider():
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    if provider not in DEFAULT_MODELS:
        raise LLMError(f"LLM_PROVIDER must be 'groq' or 'gemini', not '{provider}'")
    return provider


def get_model(provider):
    return os.getenv(f"{provider.upper()}_MODEL", "").strip() or DEFAULT_MODELS[provider]


def get_key(provider):
    name = KEY_NAMES[provider]
    key = os.getenv(name, "").strip()
    if not key or key.startswith("your_"):
        raise LLMError(f"{name} is missing. Copy .env.example to .env and add your key.")
    return key


def api_message(response):
    """The error text the provider sent back."""
    try:
        return response.json()["error"]["message"]
    except Exception:
        return response.text[:200]


def post_json(url, headers, payload):
    """POST with a timeout. Retries on timeouts, rate limits (429) and server errors."""
    last_error = "unknown error"
    for attempt in range(1, RETRIES + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        except requests.exceptions.Timeout:
            last_error = "the model did not answer in time"
        except requests.exceptions.ConnectionError:
            last_error = "could not reach the model (check your internet)"
        else:
            status = response.status_code
            if status == 200:
                try:
                    return response.json()
                except ValueError:
                    raise LLMError("The model sent a reply that is not valid JSON.")
            if status in (401, 403):
                raise LLMError("The API key was rejected. Check the key in your .env file.")
            if status in (400, 404):
                raise LLMError(f"The request was refused: {api_message(response)} "
                               "(if the model was not found, change the model name in .env)")
            if status == 429 or status >= 500:
                last_error = f"rate limit or server problem ({status}): {api_message(response)}"
            else:
                raise LLMError(f"Unexpected error {status}: {api_message(response)}")
        logging.warning("LLM call failed (try %s of %s): %s", attempt, RETRIES, last_error)
        if attempt < RETRIES:
            time.sleep(2 * attempt)  # wait longer after each failure
    raise LLMError(f"Gave up after {RETRIES} tries: {last_error}")


def ask_groq(system_prompt, user_message, temperature, max_tokens, json_mode):
    payload = {
        "model": get_model("groq"),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {get_key('groq')}", "Content-Type": "application/json"}
    data = post_json(GROQ_URL, headers, payload)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise LLMError("The model reply was not in the expected format.")


def ask_gemini(system_prompt, user_message, temperature, max_tokens, json_mode):
    config = {"temperature": temperature, "maxOutputTokens": max_tokens}
    if json_mode:
        config["responseMimeType"] = "application/json"
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        "generationConfig": config,
    }
    headers = {"x-goog-api-key": get_key("gemini"), "Content-Type": "application/json"}
    data = post_json(GEMINI_URL.format(model=get_model("gemini")), headers, payload)
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise LLMError("The model returned no text (the answer may have been blocked).")


def ask_llm(system_prompt, user_message, temperature=0.2, max_tokens=800, json_mode=False):
    """Send a system prompt and a user message to the chosen provider; return the text reply."""
    provider = get_provider()
    ask = ask_groq if provider == "groq" else ask_gemini
    return ask(system_prompt, user_message, temperature, max_tokens, json_mode)