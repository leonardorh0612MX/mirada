"""Spark anchor proposals via the Responses API. No fallbacks inside.

Contract (D8): Responses API only. On any API error the caller gets None.
Absence is safe; a wrong anchor is not. The degradation ladder lives in the
caller, not here.
"""

import base64
import json
import os

PROMPT = (
    "You are an eye-tracking assistant. Given this screenshot and the recent "
    "interaction context, name the single UI element the user is most likely "
    "looking at right now. Reply with JSON only: "
    '{"concept": "<short noun phrase>", "confidence": <0-1>, '
    '"reason": "<short>", "x": <int>, "y": <int>}. '
    "x and y are the pixel coordinates of that element's center in this "
    "exact image (origin top-left). The concept must be a short noun phrase "
    "a segmentation model can match, e.g. \"blue Send button\"."
)


def _client():
    from openai import OpenAI

    key = os.environ.get("MODEL_API_KEY", "")
    if not key:
        raise RuntimeError("MODEL_API_KEY is not set")
    base = os.environ.get("META_MODEL_BASE_URL", "https://api.meta.ai/v1").rstrip("/")
    timeout_s = float(os.environ.get("MODEL_API_TIMEOUT_S", "90"))
    return OpenAI(base_url=base, api_key=key, timeout=timeout_s)


def propose(screenshot_png, context="", model="muse-spark-1.3", max_tokens=2000):
    """Screenshot bytes plus context to (concept, conf, reason, x, y).

    x, y are pixel coordinates in the screenshot's own space. Returns None
    on any failure. Never raises for API errors; raises only for missing
    configuration.
    """
    b64 = base64.b64encode(screenshot_png).decode()
    try:
        client = _client()
        r = client.responses.create(
            model=model,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": PROMPT + f"\nContext: {context}"},
                    {"type": "input_image", "image_url": f"data:image/png;base64,{b64}"},
                ],
            }],
        )
        text = (r.output_text or "").strip()
    except Exception:
        return None
    return parse_proposal(text)


def parse_proposal(text):
    """Raw model text to (concept, conf, reason, x, y) or None."""
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        data = json.loads(text[start:end])
        x, y = data.get("x"), data.get("y")
        if x is None or y is None:
            return None  # point required: a concept alone is not an anchor
        return (str(data["concept"]), float(data["confidence"]),
                str(data.get("reason", "")), float(x), float(y))
    except Exception:
        return None  # unparsed output is not safe enough for an anchor
