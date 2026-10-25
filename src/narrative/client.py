"""Minimal Azure OpenAI HTTP client for the optional narrative provider.

Kept isolated so the default template provider has zero cloud dependencies and
imports nothing from the `requests`/`openai` ecosystem.
"""

from __future__ import annotations

import json
import urllib.request


def _post(provider, messages: list[dict]) -> dict:
    url = (
        f"{provider.endpoint.rstrip('/')}/openai/deployments/"
        f"{provider.deployment}/chat/completions?api-version={provider.api_version}"
    )
    payload = json.dumps(
        {
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "api-key": provider.api_key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        body = json.loads(response.read().decode("utf-8"))
    return json.loads(body["choices"][0]["message"]["content"])


def request_json(provider, context: dict) -> dict:
    from src.narrative.prompts import SYSTEM_PROMPT

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Return JSON with exactly the keys 'claim' and 'significance'. "
                f"Facts: {json.dumps(context, sort_keys=True)}"
            ),
        },
    ]
    return _post(provider, messages)


def request_narrative(provider, claim, audience: str) -> dict:
    from src.narrative.prompts import SYSTEM_PROMPT

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Rewrite the verified claim for the "
                f"'{audience}' audience without adding facts. Return JSON with keys "
                f"'headline' and 'body'. Claim: {claim.claim}. "
                f"Significance: {claim.significance}. Confidence: {claim.confidence}."
            ),
        },
    ]
    return _post(provider, messages)
