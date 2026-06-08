"""Minimal Anthropic Messages client (text + vision) via stdlib urllib.

Cheapest current model is Haiku 4.5 (claude-haiku-4-5). Kept dependency-free so
the GitHub Actions runner needs no `pip install anthropic`.
"""
import base64
import json
import os
import urllib.request
import urllib.error

API = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")
VERSION = "2023-06-01"


def _post(body):
    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY not set")
    req = urllib.request.Request(API, data=json.dumps(body).encode(), method="POST")
    req.add_header("x-api-key", key)
    req.add_header("anthropic-version", VERSION)
    req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Anthropic HTTP {e.code}: {e.read().decode()[:400]}")


def _text(resp):
    return "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")


def _strip_fence(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        # ```json\n...\n```  ->  inner
        inner = raw.split("```", 2)
        raw = inner[1] if len(inner) > 1 else raw
        if raw.lstrip().lower().startswith("json"):
            raw = raw.lstrip()[4:]
    return raw.strip()


def complete_json(system, user, image_png=None, max_tokens=1500):
    """Send one message, parse the model's reply as JSON. Optional PNG bytes for vision."""
    content = []
    if image_png is not None:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": base64.standard_b64encode(image_png).decode("utf-8"),
            },
        })
    content.append({"type": "text", "text": user})
    resp = _post({
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": content}],
    })
    return json.loads(_strip_fence(_text(resp)))
