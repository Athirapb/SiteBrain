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

import re

from .. import config

# Vibration limits for rotary machines (pumps, agitators, blowers, fans, shredders, screws): site-configurable
VIB_ALERT, VIB_STOP = config.VIB_ALERT_MM_S, config.VIB_STOP_MM_S
VIB_LIMIT = (f"< {VIB_ALERT:g} mm/s acceptable; {VIB_ALERT:g}–{VIB_STOP:g} mm/s alert; stop above {VIB_STOP:g} mm/s "
             "(ISO 10816 class II); also alert on a 25 % rise over the machine's own baseline")
VIB_ALARM_PREVENT = (f"Set vibration alarms at {VIB_ALERT:g} mm/s (alert) and {VIB_STOP:g} mm/s (stop), plus a 25 % rise "
                     "over the baseline, each with a defined response")

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


# Answers that describe a healthy reading (most field checks read like this, whatever the fault)
_NORMAL_START = re.compile(
    r"^(normal|ok\b|fine(?! black| but)|good|clean|intact|smooth|stable|nothing|none\b|clear|tight|correct|"
    r"steady(?! climb| stream)|within (design|life|schedule|the normal)|no (change|dust|lockouts|unusual|work)|"
    r"dry(,|$)|tube matches|both agree|all (open|normal)|as usual|level ok|flow good|flowing normally|belts? |"
    r"coupling fine|sharp|fresh|moves smoothly|yes, reaches|recently|0% lel|centred|quiet|even|same\b|at setpoint|"
    r"uniform|a little, as usual|slight weep|moving evenly|below 70|both below|< ?10 ppm|2–5°c|above 95|agrees within|"
    r"level 60|reads correctly|they agree|starts and runs normally|cycles normally|it does not trip|in service|"
    r"just the usual|usual -|firm dry cake|full, even spray|brush intact|oil level ok|one running, normal|"
    r"louvres open|inlet below 40|supply cold|o2 3–6|δt normal|yes — pot empty|yes, flows freely|yes, flushed|"
    r"no, same|100% perimeter|well above the minimum|closed and locked|no trip|warm, below|ir above|"
    r"within the design|yes, done to|the usual few|matches the nameplate)", re.I)


def is_normal_answer(label: str) -> bool:
    """An answer that describes a healthy reading (most field checks read like this, whatever the fault)."""
    return bool(_NORMAL_START.match(label.strip()))
