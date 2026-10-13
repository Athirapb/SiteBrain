"""Authoring vocabulary for the SiteBrain knowledge brain.

Troubleshooting follows two standard RCA methods:

1. Fishbone (Ishikawa, 6M). Every equipment type has a set of DIRECT CAUSES, each on one bone of the fishbone:
   Man (people), Machine, Method, Material, Measurement, Environment. Field checks (Q) narrow the fishbone down to
   one direct cause with a Bayesian update: every answer option carries a likelihood multiplier per cause.
2. 5-Why. Each direct cause carries a WHY tree (W → B → W … → R). Once the direct cause is confirmed, SiteBrain asks
   "why?" until it reaches a ROOT CAUSE (R) — usually a systemic Method / Man / Material gap — with preventive actions.

    C(id, label, category, keys, steps, why=W(...), case="KB-0298")      direct cause; steps = immediate corrective actions
    Q(id, text, [(label, {cause: lik}, [flags]), ...], keys, contradiction, how=..., purpose=...)
    W(text, [B(label, W(...) | R(...)), ...], how=...)                    one "why?" question
    R(label, category, prevent=[...], correct=[...], case=...)             root cause + preventive / extra corrective actions
    K(id, kinds, keys, title, cause, fix, why=[...], category=..., prevent=...)   a past RCA case for the case library

Likelihoods: 1.0 = the answer says nothing about that cause; >1 makes it more likely (3–4 = strong evidence);
<1 makes it less likely (0.2–0.4 = nearly rules it out).
"""

CATEGORIES = ["Man", "Machine", "Method", "Material", "Measurement", "Environment"]
CATEGORY_LABEL = {"Man": "People", "Machine": "Machine", "Method": "Method", "Material": "Material",
                  "Measurement": "Measurement", "Environment": "Environment"}


def C(id, label, category, keys, steps, why=None, case=None):
    return {"id": id, "label": label, "category": category, "keys": keys, "steps": steps, "why": why, "case": case}


def Q(id, text, options, keys=None, contradiction=None, how=None, purpose=None):
    return {"id": id, "text": text, "how": how, "purpose": purpose, "keys": keys or [], "contradiction": contradiction,
            "options": [{"label": o[0], "lik": o[1], "flags": list(o[2]) if len(o) > 2 else []} for o in options]}


def W(text, branches, how=None):
    return {"type": "why", "text": text, "how": how, "branches": branches}


def B(label, then):
    return {"label": label, "then": then}


def R(label, category, prevent, correct=None, case=None):
    return {"type": "root", "label": label, "category": category, "prevent": list(prevent), "correct": list(correct or []),
            "case": case}


def K(id, kinds, keys, title, cause, fix, why=(), category="Machine", prevent="", source="Maintenance records"):
    return {"id": id, "kinds": list(kinds), "keys": list(keys), "title": title, "cause": cause, "fix": fix,
            "why_chain": list(why), "category": category, "prevent": prevent, "source": source}


def roots(node) -> list[dict]:
    """Every root cause reachable in a why tree."""
    if not node:
        return []
    if node["type"] == "root":
        return [node]
    return [r for b in node["branches"] for r in roots(b["then"])]


def depth(node) -> int:
    if not node or node["type"] == "root":
        return 0
    return 1 + max(depth(b["then"]) for b in node["branches"])
