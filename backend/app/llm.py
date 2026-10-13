"""LLM integration for conversational diagnosis.

Providers: Anthropic Claude, Groq (free tier) or any OpenAI-compatible server (e.g. Ollama, local and free).
The LLM only phrases questions, weighs evidence and drafts resolutions. Safety interlocks, turn limits
and escalation triggers stay deterministic in the engine. Any failure returns None and the caller
falls back to the decision-tree engine, so the app works fully offline.
"""
import json
import logging
import os
from pathlib import Path

from . import config

log = logging.getLogger("sitebrain.llm")
_clients: dict = {}
_failed: dict[str, str] = {}  # provider -> reason it was switched off (bad key, no credits)

LABELS = {"anthropic": "Claude", "groq": "Groq", "openai_compat": "OpenAI-compatible"}


def _anthropic_credentials() -> bool:
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"):
        return True
    return (Path.home() / ".config" / "anthropic").exists()


def provider() -> str | None:
    """The configured provider, or None when no LLM should be used.

    In auto mode a provider that failed permanently (bad key, no credits) is skipped for the next one.
    """
    if config.LLM_ENABLED == "off":
        return None
    p = config.LLM_PROVIDER
    if p in ("anthropic", "groq", "openai_compat"):
        return p
    candidates = (["anthropic"] if _anthropic_credentials() else []) + (["groq"] if config.GROQ_API_KEY else [])
    for c in candidates:
        if c not in _failed:
            return c
    if candidates:
        return candidates[-1]
    return "anthropic" if config.LLM_ENABLED == "on" else None


def model() -> str | None:
    return {"anthropic": config.CLAUDE_MODEL, "groq": config.GROQ_MODEL,
            "openai_compat": config.OPENAI_COMPAT_MODEL}.get(provider())


def available() -> bool:
    if not provider() or provider() in _failed:
        return False
    if provider() == "groq":
        return bool(config.GROQ_API_KEY)
    return True


def status() -> dict:
    on = available()
    return {"enabled": on, "provider": provider() if on else None, "label": LABELS.get(provider()) if on else None,
            "model": model() if on else None,
            "engine": f"{LABELS[provider()]} + decision tree" if on else "decision tree",
            "reason": "; ".join(f"{LABELS[k]}: {v}" for k, v in _failed.items()) or None}


def _disable(p: str, reason: str) -> None:
    _failed[p] = reason
    nxt = provider()
    log.warning("%s switched off: %s.%s", LABELS[p], reason,
                f" Using {LABELS[nxt]} instead." if nxt and nxt not in _failed else " Using the decision tree.")


def complete_json(system: str, messages: list[dict], schema: dict, max_tokens: int = 4000) -> dict | None:
    """One LLM call constrained to `schema`. Returns the parsed dict, or None on any failure."""
    if not available() or not messages:
        return None
    p = provider()
    data = (_anthropic_call if p == "anthropic" else _openai_compat_call)(system, messages, schema, max_tokens)
    if data is None and p in _failed and available():
        return complete_json(system, messages, schema, max_tokens)  # auto mode moved on to the next provider
    if data is None:
        return None
    missing = [k for k in schema.get("required", []) if k not in data]
    if missing:
        log.warning("LLM response missing fields %s; using decision tree for this turn", missing)
        return None
    return data


def _parse(text: str | None) -> dict | None:
    if not text:
        return None
    t = text.strip()
    a, b = t.find("{"), t.rfind("}")  # tolerate code fences or stray prose around the JSON
    if a >= 0 and b > a:
        t = t[a:b + 1]
    try:
        out = json.loads(t)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        log.warning("LLM returned non-JSON text")
        return None


# ---------------------------------------------------------------------------
# Anthropic Claude
# ---------------------------------------------------------------------------

def _anthropic_call(system, messages, schema, max_tokens):
    import anthropic

    client = _clients.get("anthropic")
    if client is None:
        client = _clients["anthropic"] = anthropic.Anthropic(timeout=60.0, max_retries=1)
    req = dict(
        model=config.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
        output_config={"effort": config.CLAUDE_EFFORT, "format": {"type": "json_schema", "schema": schema}},
    )
    try:
        try:
            # Server-side fallback: a policy decline is re-run on Anthropic's recommended fallback model.
            resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **req)
        except anthropic.BadRequestError as e:
            if "credit balance" in str(e).lower():
                raise
            log.info("fallbacks not accepted (%s); retrying without", e)
            resp = client.messages.create(**req)
    except anthropic.AuthenticationError:
        _disable("anthropic", "API key rejected")
        return None
    except anthropic.PermissionDeniedError:
        _disable("anthropic", "API key lacks permission")
        return None
    except anthropic.BadRequestError as e:
        if "credit balance" in str(e).lower():
            _disable("anthropic", "credit balance too low — add credits under Plans & Billing")
        else:
            log.warning("Claude API error 400: %s", e)
        return None
    except anthropic.NotFoundError as e:
        log.warning("Claude model not found: %s", e)
        return None
    except anthropic.RateLimitError:
        log.warning("Claude rate limited; using decision tree for this turn")
        return None
    except anthropic.APIStatusError as e:
        log.warning("Claude API error %s", e.status_code)
        return None
    except anthropic.APIConnectionError:
        log.warning("Claude unreachable; using decision tree for this turn")
        return None

    if resp.stop_reason == "refusal":
        log.warning("Claude declined the request")
        return None
    return _parse(next((b.text for b in resp.content if getattr(b, "type", "") == "text"), None))


# ---------------------------------------------------------------------------
# Groq and other OpenAI-compatible servers (Ollama, OpenRouter, LM Studio, vLLM …)
# ---------------------------------------------------------------------------

def _openai_compat_call(system, messages, schema, max_tokens):
    import openai

    p = provider()
    client = _clients.get(p)
    if client is None:
        if p == "groq":
            client = openai.OpenAI(api_key=config.GROQ_API_KEY, base_url=config.GROQ_BASE_URL, timeout=60.0, max_retries=1)
        else:
            client = openai.OpenAI(api_key=config.OPENAI_COMPAT_API_KEY or "none", base_url=config.OPENAI_COMPAT_BASE_URL,
                                   timeout=120.0, max_retries=1)
        _clients[p] = client
    name = model()
    chat = [{"role": "system", "content": system}] + messages
    base = dict(model=name, messages=chat, max_completion_tokens=max_tokens, temperature=0.2)
    if "gpt-oss" in name:
        base["reasoning_effort"] = "low"  # gpt-oss is a reasoning model; keep turns fast and within free-tier token limits
    strict = {"type": "json_schema", "json_schema": {"name": "sitebrain_reply", "strict": True, "schema": schema}}
    loose = {"type": "json_object"}
    hint = ("\n\nRespond with a single JSON object only, matching this JSON schema exactly "
            "(all keys required):\n" + json.dumps(schema))
    try:
        try:
            resp = client.chat.completions.create(response_format=strict, **base)
        except openai.BadRequestError as e:
            # Model without strict schema support: fall back to JSON mode with the schema in the prompt
            log.info("%s: strict JSON schema not accepted (%s); retrying in JSON mode", p, e.__class__.__name__)
            chat_loose = [{"role": "system", "content": system + hint}] + messages
            resp = client.chat.completions.create(response_format=loose, **{**base, "messages": chat_loose})
    except openai.AuthenticationError:
        _disable(p, "API key rejected — check the key in backend/.env")
        return None
    except openai.PermissionDeniedError:
        _disable(p, "API key lacks permission or the organization is restricted")
        return None
    except openai.NotFoundError:
        log.warning("%s model '%s' not found", LABELS[p], name)
        return None
    except openai.RateLimitError:
        log.warning("%s rate limited (free-tier limits); using decision tree for this turn", LABELS[p])
        return None
    except openai.APIStatusError as e:
        log.warning("%s API error %s", LABELS[p], e.status_code)
        return None
    except openai.APIConnectionError:
        log.warning("%s unreachable at %s; using decision tree for this turn", LABELS[p], client.base_url)
        return None
    if not resp.choices:
        return None
    return _parse(resp.choices[0].message.content)


CATEGORY_ENUM = ["Man", "Machine", "Method", "Material", "Measurement", "Environment"]

CAUSE_SCHEMA = {
    "type": "object",
    "properties": {"label": {"type": "string"}, "likelihood": {"type": "number"},
                   "category": {"type": "string", "enum": CATEGORY_ENUM}},
    "required": ["label", "likelihood", "category"], "additionalProperties": False,
}

WHY_SCHEMA = {
    "type": "object",
    "properties": {"why": {"type": "string"}, "because": {"type": "string"}},
    "required": ["why", "because"], "additionalProperties": False,
}

BOT_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        # stage 'fishbone': the one field check the operator is told to do now, why, and how to do it safely
        "instruction": {"type": ["string", "null"]},
        "purpose": {"type": ["string", "null"]},
        "how": {"type": ["string", "null"]},
        # the possible results of that check (what the operator observes), never actions to take
        "quick_replies": {"type": "array", "items": {"type": "string"}},
        "stage": {"type": "string", "enum": ["fishbone", "why", "done"]},
        "causes": {"type": "array", "items": CAUSE_SCHEMA},
        "cited_cases": {"type": "array", "items": {"type": "string"}},
        "direct_cause": {"type": ["string", "null"]},
        "fishbone_category": {"type": ["string", "null"], "enum": CATEGORY_ENUM + [None]},
        "immediate_actions": {"type": ["array", "null"], "items": {"type": "string"}},
        "why_chain": {"type": "array", "items": WHY_SCHEMA},
        "identified": {"type": "boolean"},
        "root_cause": {"type": ["string", "null"]},
        "steps": {"type": ["array", "null"], "items": {"type": "string"}},
        "preventive_actions": {"type": ["array", "null"], "items": {"type": "string"}},
        "unidentified": {"type": "boolean"},
        "hazard_flags": {"type": "array", "items": {"type": "string",
                                                    "enum": ["particles", "channeling", "gas_leak", "rotating_critical",
                                                             "rotating_abnormal", "water_carryover", "h2s_breakthrough",
                                                             "bypass_open", "guard_inactive", "offspec_gas", "low_oil",
                                                             "seal_leak", "belt_wear"]}},
    },
    "required": ["reply", "instruction", "purpose", "how", "quick_replies", "stage", "causes", "cited_cases", "direct_cause", "fishbone_category",
                 "immediate_actions", "why_chain", "identified", "root_cause", "steps", "preventive_actions",
                 "unidentified", "hazard_flags"],
    "additionalProperties": False,
}

SIDE_SCHEMA = {
    "type": "object",
    "properties": {"reply": {"type": "string"},
                   "sources": {"type": "array", "items": {"type": "integer"}}},  # numbers of the passages used
    "required": ["reply", "sources"],
    "additionalProperties": False,
}

EQUIPMENT_KINDS = ["Agitator", "Pump", "Blower", "Compressor", "Decanter", "WAM", "Shredder", "HWG", "Chiller",
                   "Scrubber", "Filter", "Membrane"]

# What an uploaded document is about (knowledge.profile_document)
DOC_PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "equipment_kinds": {"type": "array", "items": {"type": "string", "enum": EQUIPMENT_KINDS}},
        "summary": {"type": "string"},
    },
    "required": ["equipment_kinds", "summary"],
    "additionalProperties": False,
}

# Answer to a knowledge-base question from retrieved passages (knowledge.ask)
DOC_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "found": {"type": "boolean"},
        "sources": {"type": "array", "items": {"type": "integer"}},  # relevant passages, most relevant first
    },
    "required": ["answer", "found", "sources"],
    "additionalProperties": False,
}
