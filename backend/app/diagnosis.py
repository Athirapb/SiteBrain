"""Diagnostic session engine (SRS §3 state machine): fishbone + 5-Why root cause analysis.

Issue report → [localize: which equipment in the area?]
  → FISHBONE: field checks narrow the 6M direct causes (Man, Machine, Method, Material, Measurement, Environment)
    with a Bayesian update over the knowledge brain's decision tree, or the LLM following the same method
  → FINDING: the confirmed direct cause with immediate corrective actions
  → 5-WHY: "why?" one level at a time until a systemic root cause
  → RCA SUMMARY: root cause, why chain, fishbone category, corrective and preventive actions → resolution
Safety interlocks are recorded for the control room; they never hold up the troubleshooting. Escalation to L2/L3 experts (SRS §4.2) is always the field
operator's call (the Escalate button, or asking for an expert in the chat); on >5 turns without >85% confidence,
telemetry contradiction, critical safety hazard, no known cause, or an issue that cannot be localized SiteBrain
recommends it.

The field operator is talked to like a colleague: every check says why it is asked and how to do it safely, can be
skipped ("I can't check this"), and every answer is acknowledged with what it tells us.
"""
import itertools
import json
import math
import re
import zlib

from . import config, db, escalation, knowledge, llm, media, safety, telemetry, topology
from .brain import CATEGORY_LABEL, MAINTENANCE, conditions_for, find_cause, roots, tree_for
from .catalog import SEVERITIES, SYMPTOM_BY_ID, report_hint, report_summary, symptom_labels, symptoms_for

NOT_SURE = "Not sure"
HOW = "How do I check this?"
CANT = "I can't check this"
SKIP_WHY = "Skip to the fix"
DONE = "Done"
STEP_HOW = "How do I do this?"
STEP_CANT = "I can't do this step"
ALL_STEPS = "Show all steps"
WORKING = "Yes, it's working normally"
NOT_WORKING = "No, still a problem"
CLOSE_REPLY = "No issue found, close session"
PERSISTS = "I applied the recommended steps but the issue persists."
_NOT_SURE_TEXT = re.compile(r"\b(not sure|unsure|don'?t know|no idea|can'?t tell|whole area)\b", re.I)
_QUESTION = re.compile(r"^(what|why|how|when|where|which|who|whose|is|are|was|were|can|could|should|shall|do|does|did|"
                       r"will|would|may|might|any|tell me|explain)\b", re.I)
_DONE_TEXT = re.compile(r"^(done|ok|okay|finished|completed|complete|did it|yes|yep|next)\b", re.I)
_CANT_TEXT = re.compile(r"\b(can'?t|cannot|unable to|no way to|not able to) (check|see|reach|access|measure|get)\b", re.I)


class SessionError(Exception):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

EQ_SELECT = "SELECT e.*, a.code AS unit, a.name AS unit_name FROM equipment e JOIN areas a ON a.id=e.area_id"


def load_area(area_id: int) -> dict:
    a = db.q1("SELECT * FROM areas WHERE id=?", (area_id,))
    if not a:
        raise SessionError("Unknown area", 404)
    return a


def load_eq(eq_id: str) -> dict:
    eq = db.q1(f"{EQ_SELECT} WHERE e.id=?", (eq_id,))
    if not eq:
        raise SessionError("Unknown equipment", 404)
    return eq


def area_equipment(area_id: int) -> list[dict]:
    return db.q(f"{EQ_SELECT} WHERE e.area_id=? AND e.active ORDER BY e.name", (area_id,))


def session_eq(s: dict) -> dict | None:
    return load_eq(s["equipment_id"]) if s.get("equipment_id") else None


def load_session(sid: str) -> dict:
    s = db.q1("SELECT * FROM sessions WHERE id=?", (sid,))
    if not s:
        raise SessionError("Unknown session", 404)
    for k, d in (("causes", []), ("cited", []), ("state", {}), ("steps", None), ("report", {})):
        s[k] = db.loads(s[k], d)
    return s


def save_session(s: dict, **fields) -> None:
    s.update(fields)
    db.update("sessions", "id", s["id"], {k: s[k] for k in (
        "equipment_id", "status", "mode", "engine", "turns", "confidence", "causes", "cited", "state", "identified",
        "symptom", "root_cause", "steps", "resolved_by", "severity", "pending_signoff", "identified_at", "resolved_at")})


def messages(sid: str) -> list[dict]:
    rows = db.q("SELECT * FROM messages WHERE session_id=? ORDER BY id", (sid,))
    return [{"id": r["id"], "type": r["type"], "created_at": r["created_at"], **db.loads(r["payload"], {})} for r in rows]


# SiteBrain writes like a colleague on WhatsApp: at most three short sentences per message
MAX_SENTENCES = 3
_ABBREV = re.compile(r"\b(e\.g|i\.e|etc|approx|vs|no|nos|min|max|fig|ref|dr|mr|ms|st)\.$", re.I)
_CRISP_TYPES = {"agent", "analysis", "offer", "survey"}


def sentences(text: str) -> list[str]:
    """Split into sentences, keeping decimals (2.5 bar), abbreviations (e.g.) and list numbers together."""
    out: list[str] = []
    for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"“‘(])", (text or "").strip()):
        if out and (_ABBREV.search(out[-1]) or re.search(r"(^|\s)\d+\.$", out[-1])):
            out[-1] = f"{out[-1]} {part}"
        elif part:
            out.append(part)
    return out


def crisp(text: str, keep: str | None = None, n: int = MAX_SENTENCES) -> str:
    """Trim a message to n sentences. `keep` (the question or step being asked, at the end) is never cut: only the
    lead-in before it is shortened. Without it, a closing question survives the cut too."""
    text = (text or "").strip()
    if not text:
        return text
    if keep and text.endswith(keep.strip()) and keep.strip() != text:
        tail = keep.strip()
        head = sentences(text[: -len(tail)])
        room = max(1, n - len(sentences(tail)))
        return " ".join(head[:room] + [tail]) if head else tail
    parts = sentences(text)
    if len(parts) <= n:
        return text
    if parts[-1].endswith("?") and not any(p.endswith("?") for p in parts[: n - 1]):
        return " ".join(parts[: n - 1] + [parts[-1]])
    return " ".join(parts[:n])


def add_msg(sid: str, type_: str, **payload) -> None:
    if type_ in _CRISP_TYPES and payload.get("text") and not (payload.get("expert") and type_ == "agent"):
        payload["text"] = crisp(payload["text"], payload.get("prompt"))  # a person's own words are never trimmed
    db.insert("messages", {"session_id": sid, "type": type_, "payload": payload, "created_at": db.now_iso()})


def event(sid: str, text: str, icon: str = "information-outline", tone: str = "info") -> None:
    add_msg(sid, "event", text=text, icon=icon, tone=tone)


def condition(s: dict) -> dict:
    """Signals the simulated historian derives from this session's report and hazards."""
    return telemetry.condition(s["report"], s["state"].get("flags", []))


def latest_escalation(sid: str) -> dict | None:
    return db.q1("SELECT * FROM escalations WHERE session_id=? ORDER BY created_at DESC", (sid,))


# ---------------------------------------------------------------------------
# Bayesian decision-tree engine
# ---------------------------------------------------------------------------

def _norm(post: dict) -> dict:
    t = sum(post.values()) or 1.0
    return {k: v / t for k, v in post.items()}


def _entropy(p: dict) -> float:
    return -sum(v * math.log(v) for v in p.values() if v > 0)


def initial_posterior(tree: dict, hint: str, matched: list[dict]) -> dict:
    strong = {m["id"] for m in matched if m["sim"] >= 60}
    post = {}
    for c in tree["causes"]:
        w = c.get("prior", 1.0)  # how common this cause is, learned from resolved sessions (1.0 = no data)
        if any(k in hint for k in c["keys"]):
            w *= 2.5
        if c.get("case") in strong:
            w *= 1.3
        post[c["id"]] = w
    return _norm(post)


def _answer_dist(q: dict, post: dict) -> list[float]:
    probs = [0.0] * len(q["options"])
    for c, pc in post.items():
        liks = [o["lik"].get(c, 1.0) for o in q["options"]]
        t = sum(liks)
        for i, l in enumerate(liks):
            probs[i] += pc * l / t
    return probs


def pick_question(tree: dict, post: dict, asked: list[str], hint: str) -> dict | None:
    best, best_score = None, -1e9
    h0 = _entropy(post)
    for q in tree["questions"]:
        if q["id"] in asked:
            continue
        exp_h = 0.0
        for i, pa in enumerate(_answer_dist(q, post)):
            after = _norm({c: post[c] * q["options"][i]["lik"].get(c, 1.0) for c in post})
            exp_h += pa * _entropy(after)
        gain = h0 - exp_h
        if q["keys"] and any(k in hint for k in q["keys"]):
            gain += 0.05
        if gain > best_score:
            best, best_score = q, gain
    return best


def _answer_lik(q: dict, i: int, c: str) -> float:
    """P(the operator sees option i | cause c), the observation model pick_question() uses."""
    liks = [o["lik"].get(c, 1.0) for o in q["options"]]
    return liks[i] / (sum(liks) or 1.0)


def _set_entropy(qs: list[dict], post: dict) -> float:
    """Expected entropy of the causes after the answers to all of qs (every combination of answers)."""
    exp_h = 0.0
    for combo in itertools.product(*[range(len(q["options"])) for q in qs]):
        w = {c: p * math.prod(_answer_lik(q, i, c) for q, i in zip(qs, combo)) for c, p in post.items()}
        pa = sum(w.values())
        if pa > 0:
            exp_h += pa * _entropy({c: v / pa for c, v in w.items()})
    return exp_h


def pick_survey(tree: dict, post: dict, asked: list[str], hint: str, k: int) -> list[dict]:
    """The k checks that, answered together, best separate the causes: chosen greedily by joint information gain,
    so the set covers different bones of the fishbone instead of k checks that all test the same cause."""
    chosen: list[dict] = []
    h = _entropy(post)
    left = [q for q in tree["questions"] if q["id"] not in asked]
    while left and len(chosen) < k:
        best, best_h = None, None
        for q in left:
            eh = _set_entropy(chosen + [q], post) - (0.05 if q["keys"] and any(x in hint for x in q["keys"]) else 0)
            if best_h is None or eh < best_h:
                best, best_h = q, eh
        if h - best_h < 0.01:  # adds nothing the others don't already tell us
            break
        chosen.append(best)
        left.remove(best)
        h = best_h
    return chosen


def by_likely_cause(qs: list[dict], post: dict) -> list[dict]:
    """Order checks so the one that tests the most likely cause comes first: a check tests a cause when the cause
    changes which answer the operator would see."""
    def score(q: dict) -> float:
        best = 0.0
        for c, p in post.items():
            liks = [_answer_lik(q, i, c) for i in range(len(q["options"]))]
            best = max(best, p * (max(liks) - min(liks)))
        return best
    return sorted(qs, key=score, reverse=True)


def _num(text: str) -> float | None:
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group()) if m else None


_OK_WORDS = re.compile(r"\b(normal|ok|okay|fine|good|clean|intact|no issue|nothing|none|dry|smooth|steady|stable|clear)\b")


def match_option(q: dict, text: str) -> int | None:
    t = text.strip().lower()
    for i, o in enumerate(q["options"]):
        if t == o["label"].lower():
            return i
    n = _num(t)
    if n is not None:
        for i, o in enumerate(q["options"]):
            lab = o["label"].lower().replace("–", "-")
            lo_hi = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", lab)
            m_below = re.search(r"(below|under|<|less than)\s*(\d+(?:\.\d+)?)", lab)
            m_above = re.search(r"(above|over|>|more than)\s*(\d+(?:\.\d+)?)", lab)
            if m_below and n < float(m_below.group(2)):
                return i
            if m_above and n > float(m_above.group(2)):
                return i
            if lo_hi and not m_below and not m_above and float(lo_hi.group(1)) <= n <= float(lo_hi.group(2)):
                return i
    tt = set(knowledge.tokenize(t))
    best, best_s = None, 0.0
    for i, o in enumerate(q["options"]):
        lt = set(knowledge.tokenize(o["label"]))
        if not lt:
            continue
        s = len(lt & tt) / len(lt)
        if s > best_s:
            best, best_s = i, s
    if best is not None and best_s >= 0.34:
        return best
    if _OK_WORDS.search(t) and not re.search(r"\b(not|no flow|abnormal|high|low|leak)\b", t):
        return 0
    return None


# Helper replies by what people say for them
_SPOKEN_HELPERS = [
    (re.compile(r"\b(can'?t|cannot|can not|unable|not able|no way to)\b.*\b(check|do|see|reach|get)\b|\bskip\b", re.I),
     [CANT, STEP_CANT, SKIP_WHY]),
    (re.compile(r"\bhow (do|can|should) i\b|\bhow to\b|\bshow me how\b", re.I), [HOW, STEP_HOW]),
    (re.compile(r"\b(not sure|don'?t know|no idea|unsure|maybe)\b", re.I), [NOT_SURE, CANT]),
    (re.compile(r"\b(all (the )?steps|every step)\b", re.I), [ALL_STEPS]),
    (re.compile(r"\b(done|finished|completed|did it|that'?s done)\b", re.I), [DONE]),
    (re.compile(r"\b(still|not working|didn'?t work|same problem|no change)\b", re.I), [NOT_WORKING]),
    (re.compile(r"\b(working (fine|normally|now)|it works|fixed|yes,? it'?s working|running fine)\b", re.I), [WORKING]),
]
_ORDINALS = {"first": 0, "one": 0, "1": 0, "second": 1, "two": 1, "2": 1, "third": 2, "three": 2, "3": 2,
             "fourth": 3, "four": 3, "4": 3, "fifth": 4, "five": 4, "5": 4, "last": -1}


def match_spoken(options: list[str], text: str, multi: bool = False) -> list[str]:
    """Which of the options on screen a spoken answer picks ('first one', '75 degrees', 'dark with fines', 'I can't
    check this'). Several when the check takes more than one answer. Falls back to the LLM, else nothing."""
    text = (text or "").strip()
    if not text or not options:
        return []
    helpers = [o for o in options if o in _NOT_OBSERVATIONS]
    answers = [o for o in options if o not in _NOT_OBSERVATIONS]
    m = re.search(r"\b(?:option|number|answer|the)\s+(first|second|third|fourth|fifth|last|one|two|three|four|five|[1-5])\b",
                  text, re.I) or re.fullmatch(r"\W*(first|second|third|fourth|fifth|last|one|two|three|four|five|[1-5])\W*(one)?\W*",
                                              text, re.I)
    if m and answers:
        i = _ORDINALS[m.group(1).lower()]
        if -len(answers) <= i < len(answers):
            return [answers[i]]
    for pattern, wanted in _SPOKEN_HELPERS:
        hit = next((o for o in wanted if o in options), None)
        if hit and pattern.search(text):
            return [hit]
    if _num(text) is not None and any(re.search(r"\d", o) for o in answers):
        # a reading ("above 85", "about 90 degrees") picks the one range it falls in, not every label with an 85;
        # "above 85" is past the 70–85 range's edge, "below 70" short of it
        n = _num(text)
        if re.search(r"\b(above|over|more than|higher than|greater than|beyond)\b|>", text, re.I):
            n += 0.01
        elif re.search(r"\b(below|under|less than|lower than)\b|<", text, re.I):
            n -= 0.01
        i = match_option({"options": [{"label": o} for o in answers]}, f"{n:g}")
        if i is not None:
            return [answers[i]]
    said = set(knowledge.tokenize(text))
    scored = []
    for o in answers:
        lt = set(knowledge.tokenize(o))
        if lt:
            scored.append((len(lt & said) / len(lt), o))
    strong = [o for sc, o in sorted(scored, reverse=True) if sc >= 0.5]
    if strong:
        return strong if multi else strong[:1]
    if answers:
        i = match_option({"options": [{"label": o} for o in answers]}, text)
        if i is not None:
            return [answers[i]]
    if llm.available():
        res = llm.complete_json(
            "A field operator answered a question by voice. Pick the option(s) they meant, exactly as written; "
            "none if what they said matches no option. JSON {\"picked\": [str]}.",
            [{"role": "user", "content": f"Options: {json.dumps(options)}\n{'Several may apply.' if multi else 'Pick one.'}"
                                         f"\nThey said: {text}"}],
            {"type": "object", "additionalProperties": False, "required": ["picked"],
             "properties": {"picked": {"type": "array", "items": {"type": "string"}}}}, max_tokens=200)
        picked = [o for o in options if o in ((res or {}).get("picked") or [])]
        return picked if multi else picked[:1]
    return []


def causes_view(tree: dict, post: dict, excluded: list[str]) -> list[dict]:
    meta = {c["id"]: c for c in tree["causes"]}
    items = [(c, p) for c, p in post.items() if c not in excluded and c in meta]
    items.sort(key=lambda x: -x[1])
    return [{"id": c, "label": meta[c]["label"], "category": meta[c].get("category", "Machine"), "likelihood": round(p, 3)}
            for c, p in items[:4]]


def fishbone(tree: dict, post: dict, excluded: list[str]) -> list[dict]:
    """Every direct cause on its 6M bone with its current likelihood (the Ishikawa diagram)."""
    bones: dict[str, list] = {}
    for c in tree["causes"]:
        p = post.get(c["id"], 0.0)
        bones.setdefault(c.get("category", "Machine"), []).append(
            {"id": c["id"], "label": c["label"], "likelihood": round(p, 3), "ruled_out": c["id"] in excluded or p < 0.03})
    return [{"category": k, "label": CATEGORY_LABEL.get(k, k), "causes": sorted(v, key=lambda x: -x["likelihood"])}
            for k, v in bones.items()]


# ---------------------------------------------------------------------------
# Talking like a colleague
# ---------------------------------------------------------------------------

def _vary(s: dict, options: list[str], salt: str = "") -> str:
    """Deterministic variety, so acknowledgements don't read like a form letter."""
    key = f"{s['id']}:{s['turns']}:{len(s['state'].get('answers', []))}:{len(s['state'].get('rca', {}) or {})}:{salt}"
    return options[zlib.crc32(key.encode()) % len(options)]


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _reasoning(s: dict, tree: dict, before: dict, after: dict) -> str:
    """Say what the last answer told us: what it ruled out and where it points."""
    lab = {c["id"]: c["label"].lower() for c in tree["causes"]}
    top = max(after, key=after.get)
    down = [c for c in after if before.get(c, 0) > 0.08 and after[c] / before[c] < 0.45 and c != top]
    parts = [_vary(s, ["Thanks.", "Got it.", "Okay, that helps.", "Good, noted.", "Right."], "ack")]
    if down:
        parts.append(f"That makes {_join([lab[c] for c in down[:2]])} less likely.")
    if after[top] > before.get(top, 0) * 1.3:
        parts.append(f"It points towards {lab[top]} — about {round(after[top] * 100)}% now.")
    elif after[top] >= 0.4:
        parts.append(f"My best guess is still {lab[top]} ({round(after[top] * 100)}%), but I want to be sure.")
    return " ".join(parts)


def _ask(s: dict, q: dict, who: str = "SiteBrain", expert: bool = False, lead: str = "") -> None:
    """Ask one field check, with why it matters and an offer to explain how to do it. The operator may pick
    several of its options when more than one applies (multi)."""
    s["state"]["pending"] = q["id"]
    add_msg(s["id"], "agent", who=who, expert=expert, text=f"{lead} {q['text']}".strip(), prompt=q["text"],
            purpose=q.get("purpose"), multi=True,
            how=q.get("how"), replies=[o["label"] for o in q["options"]] + ([HOW] if q.get("how") else []) + [CANT])


def _skip_or_explain(s: dict, tree: dict, pending: dict, text: str, who: str, expert: bool) -> bool:
    """Handle "How do I check this?" and "I can't check this" for the pending check. True if handled."""
    t = text.strip()
    if t == HOW:
        add_msg(s["id"], "agent", who=who, expert=expert,
                text=f"Here's how: {pending.get('how') or 'use the local gauge or ask the shift engineer.'} "
                     "Tell me what you find.", multi=True,
                replies=[o["label"] for o in pending["options"]] + [CANT])
        return True
    if t == CANT or _CANT_TEXT.search(t) or (t.lower() == NOT_SURE.lower() or _NOT_SURE_TEXT.search(t)):
        st = s["state"]
        st["asked"].append(pending["id"])
        st.setdefault("skipped", []).append(pending["id"])
        nxt = pick_question(tree, st["posterior"], st["asked"], report_hint(s["report"]))
        if nxt:
            _ask(s, nxt, who, expert, lead=_vary(s, ["No problem — let's look at it another way.",
                                                     "That's fine, we'll work around it.",
                                                     "Okay, skip that one."], "skip"))
        else:
            st["pending"] = None
            st["unidentified"] = True
        return True
    return False





def _answer_pending(tree: dict, st: dict, text: str, choices: list[str] | None = None) -> tuple[dict | None, list[int]]:
    """Map the field operator's answer to options of the pending check, or of another unasked check they answered
    instead. Several options picked together (multi-select) all apply to the pending check."""
    pending = next((q for q in tree["questions"] if q["id"] == st.get("pending")), None)
    if not pending:
        return None, []
    if choices and len(choices) > 1:
        labels = {o["label"].lower(): i for i, o in enumerate(pending["options"])}
        picked = sorted({labels[c.lower()] for c in choices if c.lower() in labels})
        if picked:
            return pending, picked
    t = text.strip().lower()
    # exact option labels win over fuzzy matching, so a volunteered answer is never forced onto the pending check
    for q in [pending] + [q for q in tree["questions"] if q["id"] not in st["asked"] and q is not pending]:
        j = next((i for i, o in enumerate(q["options"]) if o["label"].lower() == t), None)
        if j is not None:
            return q, [j]
    j = match_option(pending, text)
    return pending, [] if j is None else [j]


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

def session_severity(current: str, rules: list[dict]) -> str:
    """The reported severity, raised (never lowered) by the interlocks the report or diagnosis triggered."""
    rank = {s: i for i, s in enumerate(SEVERITIES)}
    sev = current if current in rank else "Medium"
    if any(r["severity"] == "CRITICAL" and r["category"] == "interlock" for r in rules):
        sev = "Critical"
    elif any(r["category"] == "interlock" for r in rules) and rank[sev] < rank["High"]:
        sev = "High"
    return sev


def _rules_for(s: dict, area: dict, eq: dict | None) -> list[dict]:
    return safety.evaluate(eq["kind"] if eq else None, eq["name"] if eq else area["name"], s["state"].get("flags", []))


def _apply_safety(s: dict, area: dict, eq: dict | None) -> list[dict]:
    rules = _rules_for(s, area, eq)
    safety.engage(s["site_code"], area["id"], eq, rules, s["id"])
    s["severity"] = session_severity(s["severity"], rules)
    return rules


def start_session(user: dict, project_id: int | None, area_id: int | None, equipment_id: str | None, symptoms: list[str],
                  severity: str, description: str) -> dict:
    eq = load_eq(equipment_id) if equipment_id else None
    if eq and not eq["active"]:
        raise SessionError(f"{eq['name']} is marked inactive in Plant Setup")
    if not eq and not area_id:
        raise SessionError("Pick the area (and the equipment, if you know it) where the issue is")
    if eq and area_id and eq["area_id"] != area_id:
        raise SessionError(f"{eq['name']} is not in that area")
    project = db.q1("SELECT id, name, code FROM projects WHERE id=?", (project_id,)) if project_id else None
    if not project:
        raise SessionError("Pick the project the issue belongs to")
    area = load_area(eq["area_id"] if eq else area_id)
    symptoms = list(dict.fromkeys(x for x in symptoms if x in SYMPTOM_BY_ID))
    fits = symptoms_for([eq["kind"]] if eq else [e["kind"] for e in area_equipment(area["id"])])
    if set(symptoms) - fits:
        wrong = symptom_labels([x for x in symptoms if x not in fits])
        raise SessionError(f"Not a symptom of {eq['name'] if eq else area['name']}: {', '.join(wrong)}")
    description = (description or "").strip()
    if not symptoms and not description:
        raise SessionError("Pick at least one symptom or describe the issue")
    if severity not in SEVERITIES:
        raise SessionError(f"Severity must be one of {', '.join(SEVERITIES)}")

    named = None if eq else _mentioned_equipment(area, description)
    report = {"project": project["name"], "project_code": project["code"], "project_id": project["id"], "symptoms": symptoms, "symptom_labels": symptom_labels(symptoms), "severity": severity,
              "description": description, "reported_by": user["name"], "reported_at": db.now_iso()}
    sid = f"S-{db.next_counter('session', 2425)}"
    s = {
        "id": sid, "site_code": area["site_code"], "area_id": area["id"], "equipment_id": eq["id"] if eq else None,
        "user_id": user["id"], "report": report, "status": "active", "mode": "bot",
        "engine": "llm" if llm.available() else "rules", "turns": 0, "confidence": 0.0, "causes": [], "cited": [],
        "state": {"posterior": {}, "asked": [], "pending": None, "answers": [], "excluded": [], "expert_turns": 0,
                  "flags": sorted(safety.report_flags(report, eq["kind"] if eq else None)),
                  "phase": "diagnose" if eq else "localize", "loc": None},
        "identified": 0, "symptom": report_summary(report), "root_cause": None, "steps": None, "resolved_by": None,
        "severity": severity, "pending_signoff": 0, "created_at": db.now_iso(), "identified_at": None,
        "resolved_at": None,
    }
    db.insert("sessions", s)
    add_msg(sid, "report", text=report_summary(report), symptoms=report["symptom_labels"], severity=severity,
            description=description, author=user["name"], area=area["name"], equipment=eq["name"] if eq else None,
            project=project["name"])
    if eq:
        _begin_diagnosis(s, area, eq)
    else:
        add_msg(sid, "analysis", text=f"Issue reported in {area['name']} without a specific equipment. "
                                      f"First, let's find which equipment it is.",
                safety_rules=[r["action"] for r in _rules_for(s, area, None) if r["category"] == "advisory"],
                footnote="Answer with the equipment name, or Not sure and I'll narrow it down by equipment type.")
        _apply_safety(s, area, None)
        if named:
            _set_equipment(s, area, named, f"Matched “{named['name']}” from the description")
        else:
            reason = _ask_localize(s, area)
            if reason:
                suggest_escalation(s, reason)
    save_session(s)
    db.audit(user["name"], user["role"], "issue.reported", sid,
             {"project": project["code"], "area": area["code"], "equipment": s["equipment_id"], "symptoms": symptoms, "severity": severity,
              "engine": s["engine"]}, area["site_code"])
    return load_session(sid)


def _begin_diagnosis(s: dict, area: dict, eq: dict) -> None:
    """Equipment known: set the prior from the report and past cases, apply safety, ask the first check."""
    tree = tree_for(eq["kind"])
    hint = report_hint(s["report"])
    matched = knowledge.match_cases(eq["kind"], hint, s["site_code"])
    st = s["state"]
    st.update(phase="diagnose", loc=None, posterior=initial_posterior(tree, hint, matched))
    st["flags"] = sorted(set(st.get("flags", [])) | safety.report_flags(s["report"], eq["kind"]))
    s["causes"] = causes_view(tree, st["posterior"], [])
    s["confidence"] = s["causes"][0]["likelihood"] if s["causes"] else 0.0
    top = matched[0] if matched else None
    add_msg(s["id"], "analysis",
            text="Thanks for reporting. Let's solve it together. Below are the possible causes — a few quick checks "
                 "will narrow them down.",
            safety_rules=[r["action"] for r in _rules_for(s, area, eq) if r["category"] == "advisory"],
            similar=({"id": top["id"], "title": top["title"], "sim": top["sim"]} if top and top["sim"] > 40 else None))
    add_msg(s["id"], "fishbone", problem=_problem(s, eq), bones=fishbone(tree, st["posterior"], []))
    _apply_safety(s, area, eq)
    if s["mode"] == "bot" and not _ask_survey(s, area, eq):
        _first_question(s, area, eq)


def _problem(s: dict, eq: dict) -> str:
    what = ", ".join(s["report"].get("symptom_labels") or []).lower() or "the problem you described"
    return f"{what.capitalize()} on {eq['name']}"


def _first_question(s: dict, area: dict, eq: dict) -> None:
    if s["engine"] == "llm":
        if _llm_bot_turn(s, area, eq, None):
            return
        _note_llm_fallback(s)
    tree = tree_for(eq["kind"])
    st = s["state"]
    q = pick_question(tree, st["posterior"], st["asked"], report_hint(s["report"]))
    st["pending"] = None
    if q:
        _ask(s, q, lead="First check:")


def _ask_survey(s: dict, area: dict, eq: dict) -> bool:
    """Start with the present condition: several field checks in one form, answered together. False when the
    survey is off or the knowledge brain has too few checks for this equipment type."""
    if config.SURVEY_SIZE < 2:
        return False
    st = s["state"]
    qs = pick_survey(tree_for(eq["kind"]), st["posterior"], st["asked"], report_hint(s["report"]), config.SURVEY_SIZE)
    qs = by_likely_cause(qs, st["posterior"])  # asked one at a time, most likely cause first
    if len(qs) < 2:
        return False
    st["survey"], st["pending"] = [q["id"] for q in qs], None
    add_msg(s["id"], "survey", who="SiteBrain",
            text=f"These {len(qs)} checks together tell the detailed causes. Do the ones you can — one at a time.",
            questions=[{"id": q["id"], "text": q["text"], "purpose": q.get("purpose"), "how": q.get("how"),
                        "options": [o["label"] for o in q["options"]]} for q in qs])
    return True


def bones_from_causes(causes: list[dict]) -> list[dict]:
    """A fishbone from a ranked cause list (LLM-ranked causes, which are not on the knowledge brain's tree)."""
    bones: dict[str, list] = {}
    for c in causes:
        bones.setdefault(c.get("category") or "Machine", []).append({**c, "ruled_out": c["likelihood"] < 0.03})
    return [{"category": k, "label": CATEGORY_LABEL.get(k, k), "causes": v} for k, v in bones.items()]


def answer_survey(sid: str, user: dict, answers: dict[str, list[str]], skipped: list[str]) -> dict:
    """The field operator's answers to the present-condition checks, all applied to the fishbone at once. Checks
    they left blank stay available as follow-ups; no answers at all means "ask me one at a time"."""
    s = load_session(sid)
    st = s["state"]
    if s["status"] in ("resolved", "closed"):
        raise SessionError("Session is closed. Report a new issue.", 409)
    if s["mode"] != "bot" or not st.get("survey"):
        raise SessionError("No condition check is waiting for answers", 409)
    area, eq = load_area(s["area_id"]), session_eq(s)
    tree = tree_for(eq["kind"])
    qs = [q for qid in st["survey"] for q in tree["questions"] if q["id"] == qid]
    answers = {k: [a.strip().lower() for a in v or [] if a and a.strip()] for k, v in (answers or {}).items()}
    skipped = set(skipped or [])
    post, flags, lines = dict(st["posterior"]), set(st.get("flags", [])), []
    before = dict(post)
    for q in qs:
        labels = {o["label"].lower(): i for i, o in enumerate(q["options"])}
        picked = sorted({labels[a] for a in answers.get(q["id"], []) if a in labels})
        if picked:
            opts = [q["options"][i] for i in picked]
            post = _norm({c: post[c] * sum(o["lik"].get(c, 1.0) for o in opts) / len(opts) for c in post})
            opt_flags = sorted({f for o in opts for f in o["flags"]})
            flags.update(opt_flags)
            st["answers"].append({"qid": q["id"], "question": q["text"], "answer": "; ".join(o["label"] for o in opts),
                                  "flags": opt_flags})
            st["asked"].append(q["id"])
            lines.append({"q": q["text"], "a": "; ".join(o["label"] for o in opts)})
        elif q["id"] in skipped:
            st["asked"].append(q["id"])
            st.setdefault("skipped", []).append(q["id"])
            lines.append({"q": q["text"], "a": CANT})
    st["survey"] = None
    if not lines:
        add_msg(sid, "user", text="Ask me one check at a time", author=user["name"])
        _first_question(s, area, eq)
        save_session(s)
        return load_session(sid)

    summary = "Present condition:\n" + "\n".join(f"• {x['q']} — {x['a']}" for x in lines)
    add_msg(sid, "user", text=summary, author=user["name"], survey=lines)
    s["turns"] += 1
    for c in st.get("excluded", []):
        post[c] = post.get(c, 0) * 0.05
    post = _norm(post)
    new_flags = flags - set(st.get("flags", []))
    st["posterior"], st["flags"] = post, sorted(flags)
    s["causes"] = causes_view(tree, post, st.get("excluded", []))
    s["confidence"] = s["causes"][0]["likelihood"] if s["causes"] else 0
    if new_flags:
        _apply_safety(s, area, eq)
    n = len([x for x in lines if x["a"] != CANT])
    add_msg(sid, "fishbone", problem=_problem(s, eq), bones=fishbone(tree, post, st.get("excluded", [])),
            updated=f"after {n} check{'s' if n != 1 else ''}")
    if s["engine"] == "llm":
        if _llm_bot_turn(s, area, eq, summary):
            _post_turn_checks(s)
            return load_session(sid)
        _note_llm_fallback(s)
    lead = _reasoning(s, tree, before, post) or "Thanks, that's a good picture."
    if s["confidence"] >= config.CONFIDENCE_THRESHOLD:
        _confirm_cause(s, area, eq, tree, "SiteBrain", lead=lead)
    else:
        nxt = pick_question(tree, post, st["asked"], report_hint(s["report"]))
        if nxt:
            _ask(s, nxt, lead=f"{lead} To narrow it down further:")
        else:
            st["unidentified"] = True
    save_session(s)
    _post_turn_checks(s)
    return load_session(sid)


def _note_llm_fallback(s: dict) -> None:
    if not s["state"].get("llm_fallback_noted"):
        s["state"]["llm_fallback_noted"] = True
        event(s["id"], "Language model unavailable (rate limit or network) · the decision-tree engine is answering "
                       "until it is back", "cloud-off-outline", "warn")


# ---------------------------------------------------------------------------
# Localization: which equipment in the reported area?
# ---------------------------------------------------------------------------

def _fit(eq: dict, report: dict) -> int:
    """How well an equipment fits the report: its type vs the symptoms, its type or name in the description."""
    text = (report.get("description") or "").lower()
    score = sum(1 for i in report.get("symptoms") or [] if eq["kind"] in SYMPTOM_BY_ID[i]["kinds"])
    if re.search(r"\b" + re.escape(eq["kind"].lower()), text):
        score += 3
    if _names_in(eq["name"], text):
        score += 10
    return score


def _names_in(name: str, text: str) -> bool:
    return bool(re.search(r"(?<![\w])" + re.escape(name.lower()) + r"(?![\w])", text.lower()))


def _mentioned_equipment(area: dict, text: str) -> dict | None:
    hits = [e for e in area_equipment(area["id"]) if text and _names_in(e["name"], text)]
    return max(hits, key=lambda e: len(e["name"])) if hits else None


def _ranked(area: dict, report: dict, kind: str | None = None) -> list[dict]:
    eqs = [e for e in area_equipment(area["id"]) if not kind or e["kind"] == kind]
    return sorted(eqs, key=lambda e: (-_fit(e, report), e["name"]))


def _who(s: dict) -> tuple[str, bool]:
    if s["mode"] == "expert":
        return _expert_who(latest_escalation(s["id"])), True
    return "SiteBrain", False


def _ask_localize(s: dict, area: dict, kind: str | None = None) -> str | None:
    """Ask which equipment shows the problem. Returns an escalation reason if it cannot be asked."""
    eqs = _ranked(area, s["report"], kind)
    if not eqs:
        return f"No active equipment is configured in {area['name']} to localize the issue"
    if len(eqs) == 1:
        how = f"{eqs[0]['name']} is the only {kind.lower() if kind else 'equipment'} in {area['name']}"
        _set_equipment(s, area, eqs[0], how)
        return None
    who, expert = _who(s)
    s["state"].update(phase="localize", loc={"step": "equipment", "kind": kind})
    likely = [e["name"] for e in eqs[:3] if _fit(e, s["report"]) > 0] if not kind else []
    text = f"Which {kind.lower() if kind else 'equipment'} in {area['name']} shows the problem?"
    if likely and len(likely) < len(eqs):
        text += f" From the symptoms, the most likely are {', '.join(likely)}."
    add_msg(s["id"], "agent", who=who, expert=expert, text=text, replies=[e["name"] for e in eqs[:8]] + [NOT_SURE])
    return None


def _ask_kind(s: dict, area: dict) -> str | None:
    eqs = _ranked(area, s["report"])
    kinds = list(dict.fromkeys(e["kind"] for e in eqs))  # ordered by best symptom fit
    if len(kinds) <= 1:
        return f"Issue could not be localized to an equipment in {area['name']}"
    who, expert = _who(s)
    s["state"].update(phase="localize", loc={"step": "kind", "kind": None})
    add_msg(s["id"], "agent", who=who, expert=expert,
            text="No problem. What type of equipment is involved? Follow the sound, leak or smell to its source.",
            replies=kinds[:8] + [NOT_SURE])
    return None


def _set_equipment(s: dict, area: dict, eq: dict, how: str) -> None:
    s["equipment_id"] = eq["id"]
    # area-level interlocks raised by the report now belong to the equipment
    db.ex("UPDATE interlocks SET equipment_id=? WHERE session_id=? AND equipment_id IS NULL", (eq["id"], s["id"]))
    event(s["id"], f"Issue localized to {eq['name']} ({eq['kind']}) · {how}", "map-marker-check-outline", "info")
    _begin_diagnosis(s, area, eq)


def _localize_turn(s: dict, text: str) -> str | None:
    """Handle an answer during localization. Returns an escalation reason when the issue cannot be localized."""
    area = load_area(s["area_id"])
    loc = s["state"].get("loc") or {"step": "equipment", "kind": None}
    t = text.strip().lower()
    eqs = area_equipment(area["id"])
    eq = next((e for e in eqs if e["name"].lower() == t), None) or _mentioned_equipment(area, text)
    if eq:
        _set_equipment(s, area, eq, f"identified by {s['report'].get('reported_by') or 'the field operator'}")
        return None
    unsure = t == NOT_SURE.lower() or bool(_NOT_SURE_TEXT.search(t))
    who, expert = _who(s)
    if loc["step"] == "kind":
        kind = next((k for k in dict.fromkeys(e["kind"] for e in eqs) if k.lower() == t or k.lower() in t), None)
        if kind:
            return _ask_localize(s, area, kind)
        if unsure:
            return f"Issue could not be localized to an equipment in {area['name']}"
        add_msg(s["id"], "agent", who=who, expert=expert, text="I could not match that to an equipment type in this area. "
                "Pick one below, or Not sure.", replies=list(dict.fromkeys(e["kind"] for e in _ranked(area, s["report"])))[:8] + [NOT_SURE])
        return None
    if unsure:
        if loc.get("kind"):
            return f"Issue could not be localized to a specific {loc['kind'].lower()} in {area['name']}"
        return _ask_kind(s, area)
    names = [e["name"] for e in _ranked(area, s["report"], loc.get("kind"))[:8]]
    add_msg(s["id"], "agent", who=who, expert=expert,
            text=f"I could not match that to equipment in {area['name']}. Pick one below, or Not sure.",
            replies=names + [NOT_SURE])
    return None


# ---------------------------------------------------------------------------
# Conversation turns
# ---------------------------------------------------------------------------

def send(sid: str, text: str, user: dict, choices: list[str] | None = None, files: list[dict] | None = None,
         display: str | None = None) -> dict:
    """One field operator message. They can write at any time: answers move the troubleshooting on, anything else
    (a question, extra information) gets a direct reply and the pending question or step is repeated.
    `choices` carries the options picked together on a multi-select check; `text` is their readable form.
    `files` are attachments already saved with save_files(), shown on the message. `display` is what the chat
    shows when it differs from what the engine reads (a voice note: nothing typed, the engine reads its words)."""
    text = (text or "").strip()
    choices = [c.strip() for c in choices or [] if c and c.strip()]
    s = load_session(sid)
    if not text:
        raise SessionError("Empty message")
    if s["status"] in ("resolved", "closed"):
        raise SessionError("Session is closed. Report a new issue.", 409)
    if text == CLOSE_REPLY:
        _check_can_close(user)
        add_msg(sid, "user", text=text, author=user["name"])
        mark_resolved(sid, user)
        return load_session(sid)

    add_msg(sid, "user", text=text if display is None else display, author=user["name"],
            **({"choices": choices} if len(choices) > 1 else {}), **({"attachments": files} if files else {}),
            **({"heard": text} if display is not None and display != text else {}))
    st = s["state"]
    phase = st.get("phase")

    if s["mode"] == "expert":  # escalated: the field operator and the expert talk directly, SiteBrain stays out
        if phase == "localize":
            eq = _mentioned_equipment(load_area(s["area_id"]), text)
            if eq:  # only record the equipment the field operator named
                s["equipment_id"] = eq["id"]
                db.ex("UPDATE interlocks SET equipment_id=? WHERE session_id=? AND equipment_id IS NULL", (eq["id"], sid))
                st.update(phase="diagnose", loc=None)
                event(sid, f"Issue localized to {eq['name']} ({eq['kind']})", "map-marker-check-outline", "info")
                save_session(s)
        return load_session(sid)

    if phase == "localize":
        if _is_question(text):
            _side_turn(s, text)
            save_session(s)
            return load_session(sid)
        reason = _localize_turn(s, text)
        if reason:
            suggest_escalation(s, reason)
        save_session(s)
        return load_session(sid)

    if phase == "why":
        if _is_question(text):
            _side_turn(s, text)
        else:
            _why_turn(s, text)
        save_session(s)
        return load_session(sid)

    if phase in ("fix", "verify"):
        return _fix_turn(s, text, user)

    if st.get("survey") and phase in (None, "diagnose"):
        # the present-condition checks are open: answer the message, the checks wait for the form
        _side_turn(s, text, after="When you're ready, fill in the condition checks above and submit them.")
        save_session(s)
        return load_session(sid)

    if s["identified"] and text != PERSISTS:  # solution given without guided steps (e.g. by a human expert earlier)
        _side_turn(s, text)
        save_session(s)
        return load_session(sid)

    if st.get("pending") and _is_question(text) and s["engine"] == "rules":
        _side_turn(s, text)  # a question about the current check is not an answer, and not a diagnostic turn
        save_session(s)
        return load_session(sid)

    area, eq = load_area(s["area_id"]), session_eq(s)
    s["turns"] += 1
    if s["engine"] == "llm":
        if _llm_bot_turn(s, area, eq, text):
            _post_turn_checks(s)
            return load_session(sid)
        # Transient (rate limit / network): answer this turn from the decision tree, retry the LLM next turn
        _note_llm_fallback(s)
        if st.get("rca"):  # the LLM had already found the direct cause: carry on with the 5-Why
            _llm_why_fallback(s, area, eq)
            save_session(s)
            return load_session(sid)
    _rules_bot_turn(s, area, eq, text, choices)
    _post_turn_checks(s)
    return load_session(sid)


# ---------------------------------------------------------------------------
# Side conversation: questions and extra information at any point
# ---------------------------------------------------------------------------

def _is_question(text: str) -> bool:
    t = text.strip()
    return t.endswith("?") or bool(_QUESTION.match(t))


def _last_prompt(sid: str) -> dict | None:
    """The question or step the field operator still owes an answer to (the latest message offering replies)."""
    return next((m for m in reversed(messages(sid)) if m["type"] == "agent" and m.get("replies")), None)


def _side_system(s: dict, area: dict, eq: dict | None, prompt: dict | None) -> str:
    rep = s["report"]
    st = s["state"]
    lines = [
        "You are SiteBrain, the friendly operations copilot of a compressed-biogas plant, in the middle of troubleshooting "
        "with a field operator. They just asked a side question or shared extra information.",
        "Reply like a colleague on WhatsApp: plain words, practical, safe, at most 2 short sentences, no emoji. Answer the "
        "question directly from the knowledge below; if you don't know, say so and suggest the shift engineer. If they "
        "shared information, thank them and say in one sentence how it changes the picture (or that it doesn't). Do NOT "
        "ask a new check and do NOT repeat the pending question — SiteBrain repeats it after your reply.",
        "",
        f"EQUIPMENT: {eq['name'] + ' (' + eq['kind'] + ')' if eq else 'not identified yet'} in {area['name']}",
        f"REPORTED: {s['symptom']} — severity {rep.get('severity')}",
        f"STAGE: {st.get('phase') or 'diagnose'}",
    ]
    if prompt:
        lines.append(f"PENDING QUESTION/STEP: {prompt.get('prompt') or prompt.get('text')}")
        if prompt.get("how"):
            lines.append(f"HOW TO DO IT: {prompt['how']}")
    if s["causes"]:
        lines.append("LEADING CAUSES: " + "; ".join(f"{c['label']} {round(c['likelihood'] * 100)}%" for c in s["causes"][:3]))
    rca = st.get("rca") or {}
    if rca.get("direct_cause"):
        lines.append(f"DIRECT CAUSE: {rca['direct_cause']}" + (f" | ROOT CAUSE: {rca['root']}" if rca.get("root") else ""))
    fix = st.get("fix") or {}
    if fix.get("steps"):
        lines.append("FIX STEPS: " + " | ".join(f"{i + 1}. {x}" for i, x in enumerate(fix["steps"])))
    if eq and MAINTENANCE.get(eq["kind"]):
        lines.append("OPERATING LIMITS: " + "; ".join(f"{a} {b}" for a, b in MAINTENANCE[eq["kind"]].get("operating_limits", [])[:6]))
    for prof in conditions_for(area["code"]):
        lines.append(f"NORMAL CONDITIONS ({prof['title']}): " + "; ".join(f"{p[0]} {p[1]}" for p in prof["params"][:6]))
    return "\n".join(lines)


def _side_answer(s: dict, area: dict, eq: dict | None, text: str, prompt: dict | None) -> str:
    if llm.available():
        # the LLM picks the passages that fit this equipment and this question (re-ranking) and cites them
        docs = knowledge.search(f"{eq['kind'] if eq else ''} {text}", s["site_code"], 8)
        system = _side_system(s, area, eq, prompt) + (
            "\n\nPLANT DOCUMENT PASSAGES (use only those about this equipment, or general ones; list the numbers you "
            "relied on in `sources`, [] if none):\n" + knowledge.passages_block(docs, 450) if docs else
            "\n\nPLANT DOCUMENT PASSAGES: none found. Return sources [].")
        conv = transcript(s["id"])[-6:]
        while conv and conv[0]["role"] != "user":
            conv.pop(0)
        data = llm.complete_json(system, conv or [{"role": "user", "content": text}], llm.SIDE_SCHEMA, max_tokens=700)
        if data and data.get("reply"):
            used = knowledge.cited(docs, data["sources"])
            titles = list(dict.fromkeys(d["title"] for d in used))[:2]
            return data["reply"].strip() + (f" (Source: {'; '.join(titles)})" if titles else "")
    if not _is_question(text):
        return _vary(s, ["Thanks, noted — I've added that to the record.", "Good to know, I've noted it on the case.",
                         "Noted. That's useful context."], "note")
    t = text.lower()
    if prompt and prompt.get("how") and re.search(r"\b(how|where|check|measure|read|do i|do this)\b", t):
        return f"Here's how: {prompt['how']}"
    fact = _fact_answer(area, eq, text)
    if fact:
        return fact
    doc = _doc_answer(s, eq, text)
    if doc:
        return doc
    return ("I don't have a solid answer to that in my knowledge base. Check with the shift engineer, or tap "
            "Escalate To Expert and they'll pick it up with the full context.")


_STOP_Q = {"what", "normal", "is", "the", "for", "this", "should", "be", "how", "much", "much", "value", "usual", "typical",
           "range", "it", "of", "here", "our", "my", "a", "an", "do", "does", "can", "i", "we", "need"}


def _stems(text: str) -> set[str]:
    """Word stems for matching ("changed" ~ "change", "bolts" ~ "bolt")."""
    return {w[:5] for w in knowledge.tokenize(text) if w not in _STOP_Q}


def _fact_answer(area: dict, eq: dict | None, text: str) -> str | None:
    """Answer "what's normal for X?" from the structured knowledge: equipment limits and area operating conditions."""
    q = _stems(text)
    if not q:
        return None
    best, best_sc = None, 0.0
    if eq:
        for interval, task in MAINTENANCE.get(eq["kind"], {}).get("pm", []):
            pt = _stems(task)
            sc = len(q & pt) / (len(q) or 1)  # how much of the question the PM task covers
            if sc > best_sc and re.search(r"\b(how often|when|interval|frequency|schedule|change|replace|clean|grease)\b",
                                          text, re.I):
                best, best_sc = f"Per the maintenance plan for {eq['kind'].lower()}s: {interval.lower()} — {task}.", sc
        for param, val in MAINTENANCE.get(eq["kind"], {}).get("operating_limits", []):
            pt = _stems(param)
            sc = len(q & pt) / (len(pt) or 1)
            if sc > best_sc and not re.search(r"\b(how often|when|interval|schedule)\b", text, re.I):
                best, best_sc = f"Normal {param[0].lower() + param[1:]} for {eq['kind'].lower()}s here is {val}.", sc
    for prof in conditions_for(area["code"]):
        for p in prof["params"]:
            pt = _stems(p[0])
            sc = len(q & pt) / (len(pt) or 1)
            if sc > best_sc:
                best, best_sc = f"Normal {p[0][0].lower() + p[0][1:]} in {area['name']} is {p[1]}. {p[2]}.".replace("..", "."), sc
    return best if best_sc >= 0.5 else None


def _covers(d: dict, kind: str) -> bool:
    """Whether a search hit is about this equipment type, by the document's equipment tags (not its title).

    Untagged documents are general and apply to any equipment. A passage of a multi-equipment document
    (a gas-train SOP) must not be about other equipment only.
    """
    if kind not in knowledge.KIND_TERMS:  # generic "Machine": any document may apply
        return True
    tags = d.get("equipment_kinds") or []
    if tags and kind not in tags:
        return False
    here = knowledge.detect_kinds(d["excerpt"], min_hits=1)
    return not here or kind in here


def _doc_answer(s: dict, eq: dict | None, text: str) -> str | None:
    """The most relevant one or two sentences from a manual or SOP about this equipment type (or a general SOP)."""
    kind = (eq["kind"] if eq else "").lower()
    safety_q = re.search(r"\b(permit|lockout|loto|isolat\w*|lock|tag|gas test|ppe|safe)\b", text, re.I)
    q = _stems(text) | (_stems(f"permit lockout isolate isolator lock tag mandatory {kind} work") if safety_q else set())
    if safety_q:
        loto = next((d for d in knowledge.search(f"lock out tag out LOTO isolator {kind}", s["site_code"], 10)
                     if "loto" in d["title"].lower()), None)
        ref = f" ({loto['title'].split(' ')[0]})" if loto else ""
        return ("Yes — treat it as isolated work. Follow Lock-Out / Tag-Out" + ref + ": tell the control room, stop it "
                "locally, lock and tag the MCC isolator, close and tag the process valves, and prove zero energy before "
                "you start. Your site permit-to-work rules apply on top; gas-test first anywhere biogas can be present.")
    query = f"{kind} {text}"
    for d in knowledge.search(query, s["site_code"], 10):
        title = d["title"].lower()
        if "rca-guide" in title or "incident" in title:
            continue  # worked examples and logs are not instructions
        if safety_q and "loto" not in title:
            continue
        if not safety_q and eq and not _covers(d, eq["kind"]):
            continue  # a manual for another machine would mislead
        clean = re.sub(r"[#*_`>|]+", " ", d["excerpt"])
        sents = [x.strip(" -•\t") for x in re.split(r"(?<=[.!?])\s+|\n+", clean) if len(x.strip()) > 25]
        ranked = sorted(sents, key=lambda x: -len(q & _stems(x)))[:2]
        if ranked and len(q & _stems(ranked[0])) >= 2:  # a real match, not one shared word
            keep = re.sub(r"\s+", " ", " ".join(x for x in sents if x in ranked))
            return f"From {d['title']}: {keep[:320]}"
    return None


def _side_turn(s: dict, text: str, after: str = "") -> None:
    """Answer a side question or acknowledge extra information, then put the pending question back."""
    area, eq = load_area(s["area_id"]), session_eq(s)
    who, expert = _who(s)
    prompt = _last_prompt(s["id"])
    if not _is_question(text):
        s["state"].setdefault("notes", []).append({"text": text, "at": db.now_iso()})
    answer = _side_answer(s, area, eq, text, prompt)
    add_msg(s["id"], "agent", who=who, expert=expert, side=True, text=f"{answer} {after}".strip(),
            prompt=(prompt.get("prompt") or prompt.get("text")) if prompt else None, how=prompt.get("how") if prompt else None,
            fix_step=prompt.get("fix_step") if prompt else None, fix_total=prompt.get("fix_total") if prompt else None,
            why_step=prompt.get("why_step") if prompt else None, replies=prompt.get("replies") if prompt else None,
            multi=bool(prompt and prompt.get("multi")))


# ---------------------------------------------------------------------------
# Guided fix: one corrective step at a time, then check it works
# ---------------------------------------------------------------------------

def _start_fix(s: dict, who: str, expert: bool, steps: list[str], prevent: list[str]) -> None:
    st = s["state"]
    st["fix"] = {"steps": list(steps), "idx": 0, "skipped": [], "prevent": list(prevent or [])}
    st["phase"] = "fix"
    if not steps:
        _finish_fix(s, who, expert)
        return
    area, eq = load_area(s["area_id"]), session_eq(s)
    rules = _rules_for(s, area, eq)
    st["fix"]["safety"] = rules[0]["action"] if rules else None
    add_msg(s["id"], "agent", who=who, expert=expert,
            text=f"Let's fix it — {len(steps)} short step{'s' if len(steps) > 1 else ''}, one at a time. Tap Done as you "
                 "finish each one, and ask me anything along the way.",
            safety=st["fix"]["safety"] or "Follow your site safety rules and use the right protective equipment.")
    _ask_step(s, who, expert)


# Fix steps that open up, isolate or restart equipment get the safety note again
_HAZARD_STEP = re.compile(r"\b(isolat|lock|loto|purg|vent|depressur|open|dismantl|remov|replac|restart|start|energi|"
                          r"clean|drain|weld|hot work|enter)", re.I)


def _ask_step(s: dict, who: str, expert: bool, lead: str = "") -> None:
    f = s["state"]["fix"]
    step = f["steps"][f["idx"]]
    add_msg(s["id"], "agent", who=who, expert=expert, text=f"{lead} {step}".strip(), prompt=step,
            fix_step=f["idx"] + 1, fix_total=len(f["steps"]),
            safety=f.get("safety") if f.get("safety") and _HAZARD_STEP.search(step) else None,
            replies=[DONE, STEP_HOW, STEP_CANT] + ([ALL_STEPS] if len(f["steps"]) > 2 else []))


def _finish_fix(s: dict, who: str, expert: bool) -> None:
    f = s["state"]["fix"]
    if f["prevent"]:
        add_msg(s["id"], "agent", who=who, expert=expert, items=f["prevent"],
                text="One last thing — so this doesn't come back, I've added these to the case for the maintenance plan:")
    if f["skipped"]:
        add_msg(s["id"], "agent", who=who, expert=expert, items=[f["steps"][i] for i in f["skipped"]],
                text="These steps weren't done — I've flagged them on the case so the maintenance team picks them up:")
    s["state"]["phase"] = "verify"
    add_msg(s["id"], "agent", who=who, expert=expert, prompt="Is it working normally now?",
            text="Now run it and watch it for a few minutes. Is it working normally?", replies=[WORKING, NOT_WORKING])


def _fix_turn(s: dict, text: str, user: dict) -> dict:
    sid, st = s["id"], s["state"]
    who, expert = _who(s)
    t = text.strip()
    if st["phase"] == "verify":
        if t != WORKING and re.match(r"^(yes|yep|working|running|fine|all good|normal)\b", t, re.I):
            # closing ends the chat, so it only happens on the confirmed button
            add_msg(sid, "agent", who=who, expert=expert, prompt="Is it working normally now?",
                    text="Glad to hear it. Tap “Yes, it's working normally” to confirm — that closes the issue and "
                         "saves the root cause analysis.", replies=[WORKING, NOT_WORKING])
            save_session(s)
            return load_session(sid)
        if t == WORKING:
            _check_can_close(user)
            save_session(s)
            mark_resolved(sid, user)
            add_msg(sid, "agent", who=who, expert=expert,
                    text=f"Great work, {user['name']}. I've saved this root cause analysis to the knowledge base so the "
                         "next person gets there faster.")
            return load_session(sid)
        if t == NOT_WORKING or re.match(r"^(no|nope|not|still)\b", t, re.I):
            save_session(s)
            return not_resolved(sid, user)
        _side_turn(s, t)
        save_session(s)
        return load_session(sid)

    f = st["fix"]
    if t == ALL_STEPS:
        add_msg(sid, "agent", who=who, expert=expert, text="Here's the whole plan:",
                items=[("✓ " if i < f["idx"] else "→ " if i == f["idx"] else "") + x for i, x in enumerate(f["steps"])])
        _ask_step(s, who, expert, lead="We're on this one:")
    elif t == DONE or t == STEP_CANT or _DONE_TEXT.match(t) or _CANT_TEXT.search(t):
        skipped = t == STEP_CANT or bool(_CANT_TEXT.search(t))
        if skipped:
            f["skipped"].append(f["idx"])
        f["idx"] += 1
        if f["idx"] < len(f["steps"]):
            lead = ("Okay, I've noted that one for the maintenance team. Next:" if skipped
                    else _vary(s, ["Good. Next:", "Great, next one:", "Nice. Next:", "Done — next:"], f"step{f['idx']}"))
            _ask_step(s, who, expert, lead=lead)
        else:
            _finish_fix(s, who, expert)
    else:  # "How do I do this?", a question, or extra information about the step
        _side_turn(s, t)
    save_session(s)
    return load_session(sid)


def _rules_bot_turn(s: dict, area: dict, eq: dict, text: str, choices: list[str] | None = None) -> None:
    tree = tree_for(eq["kind"])
    st = s["state"]
    post = st["posterior"]
    before = dict(post)
    hint = report_hint(s["report"])
    flags = set(st.get("flags", []))
    contradiction = None

    if st.get("pending"):
        pending = next((q for q in tree["questions"] if q["id"] == st["pending"]), None)
        if pending and _skip_or_explain(s, tree, pending, text, "SiteBrain", False):
            s["turns"] = max(0, s["turns"] - 1)  # explaining or skipping a check is not a diagnostic turn
            save_session(s)
            return
        pending, picked = _answer_pending(tree, st, text, choices)
        if not picked:
            # not one of the answers: take it as an observation — nudge the causes it mentions, then re-ask
            s["turns"] = max(0, s["turns"] - 1)
            tt = set(knowledge.tokenize(text))
            for c in tree["causes"]:
                hit = tt & set(knowledge.tokenize(c["label"] + " " + " ".join(c["keys"])))
                if hit:
                    post[c["id"]] *= 1.0 + 0.3 * len(hit)
            st["posterior"] = _norm(post)
            s["causes"] = causes_view(tree, st["posterior"], st.get("excluded", []))
            s["confidence"] = s["causes"][0]["likelihood"] if s["causes"] else 0
            _side_turn(s, text)
            save_session(s)
            return
        opts = [pending["options"][i] for i in picked]
        # several options picked: the observation is any of them, so weigh each cause by their mean likelihood
        post = _norm({c: post[c] * sum(o["lik"].get(c, 1.0) for o in opts) / len(opts) for c in post})
        opt_flags = sorted({f for o in opts for f in o["flags"]})
        flags.update(opt_flags)
        st["answers"].append({"qid": pending["id"], "question": pending["text"],
                              "answer": "; ".join(o["label"] for o in opts), "flags": opt_flags})
        st["asked"].append(pending["id"])
        con = pending.get("contradiction")
        if con and con["option"] in picked:
            live = telemetry.latest(telemetry.snapshot(eq, condition(s)), con["tag"])
            if isinstance(live, (int, float)) and (("above" in con and live > con["above"]) or ("below" in con and live < con["below"])):
                contradiction = (f"Operator reported “{pending['options'][con['option']]['label']}” "
                                 f"but SCADA {con['tag']} reads {live}")
    else:
        # free-text field observation: nudge priors by keyword overlap with cause labels/keys
        tt = set(knowledge.tokenize(text))
        for c in tree["causes"]:
            ct = set(knowledge.tokenize(c["label"] + " " + " ".join(c["keys"])))
            if tt & ct:
                post[c["id"]] *= 1.0 + 0.5 * len(tt & ct)
        post = _norm(post)

    for c in st.get("excluded", []):
        post[c] = post.get(c, 0) * 0.05
    post = _norm(post)
    new_flags = flags - set(st.get("flags", []))
    st["posterior"], st["flags"] = post, sorted(flags)
    s["causes"] = causes_view(tree, post, st.get("excluded", []))
    s["confidence"] = s["causes"][0]["likelihood"] if s["causes"] else 0
    st["contradiction"] = contradiction

    if new_flags:
        _apply_safety(s, area, eq)

    lead = _reasoning(s, tree, before, post)
    if contradiction:
        lead = (f"Hold on — that doesn't match what SCADA shows ({contradiction.split(' but ')[-1]}). Double-check it "
                "if you can.")
    if s["confidence"] >= config.CONFIDENCE_THRESHOLD:
        _confirm_cause(s, area, eq, tree, "SiteBrain", lead=lead)
        save_session(s)
        return
    nxt = pick_question(tree, post, st["asked"], hint)
    st["pending"] = None
    if nxt:
        _ask(s, nxt, lead=lead + " " + _vary(s, ["Next:", "Now,", "One more thing:", "Next check:"], "next"))
    else:
        st["unidentified"] = True
    save_session(s)


# ---------------------------------------------------------------------------
# Finding → 5-Why → RCA summary
# ---------------------------------------------------------------------------

def _confirm_cause(s: dict, area: dict, eq: dict, tree: dict, who: str, expert: bool = False, lead: str = "") -> None:
    """The fishbone narrowed to one direct cause: give the immediate fix, then start asking why."""
    st = s["state"]
    cause = find_cause(tree, s["causes"][0]["id"])
    st["pending"] = None
    add_msg(s["id"], "finding", who=who, expert=expert, direct_cause=cause["label"],
            category=cause.get("category", "Machine"), category_label=CATEGORY_LABEL.get(cause.get("category"), "Machine"),
            confidence=s["confidence"], steps=cause["steps"],
            text=f"{lead} I'm fairly confident ({round(s['confidence'] * 100)}%) it's {cause['label'].lower()}.".strip())
    st["rca"] = {"cause": cause["id"], "direct_cause": cause["label"], "category": cause.get("category", "Machine"),
                 "chain": [], "node": []}
    if cause.get("case"):
        s["cited"] = sorted(set(s["cited"]) | {cause["case"]})
    s["identified_at"] = s.get("identified_at") or db.now_iso()
    if cause.get("why"):
        st["phase"] = "why"
        _ask_why(s, cause, who, expert, intro=True)
    else:
        _finalize_rca(s, area, eq, cause, None, who, expert)


def _why_node(cause: dict, path: list[int]) -> dict:
    node = cause["why"]
    for i in path:
        node = node["branches"][i]["then"]
    return node


def _ask_why(s: dict, cause: dict, who: str, expert: bool, intro: bool = False, lead: str = "") -> None:
    rca = s["state"]["rca"]
    node = _why_node(cause, rca["node"])
    if intro:
        text = f"Before we fix it, a minute on why it happened, so the fix sticks. {node['text']}"
    else:
        text = f"{lead} {node['text']}".strip()
    add_msg(s["id"], "agent", who=who, expert=expert, text=text, prompt=node["text"], how=node.get("how"),
            why_step=len(rca["chain"]) + 1,
            purpose="Knowing why it happened stops it from coming back." if intro else None,
            replies=[b["label"] for b in node["branches"]] + [NOT_SURE, SKIP_WHY])


def _match_branch(node: dict, text: str) -> int | None:
    t = text.strip().lower()
    for i, b in enumerate(node["branches"]):
        if b["label"].lower() == t:
            return i
    tt = set(knowledge.tokenize(t))
    best, best_s = None, 0.0
    for i, b in enumerate(node["branches"]):
        lt = set(knowledge.tokenize(b["label"]))
        sc = len(lt & tt) / len(lt) if lt else 0
        if sc > best_s:
            best, best_s = i, sc
    return best if best_s >= 0.5 else None


def _why_turn(s: dict, text: str) -> None:
    area, eq = load_area(s["area_id"]), session_eq(s)
    tree = tree_for(eq["kind"])
    st = s["state"]
    rca = st["rca"]
    cause = find_cause(tree, rca["cause"])
    node = _why_node(cause, rca["node"])
    who, expert = _who(s)
    t = text.strip()
    if t == SKIP_WHY or t.lower() == NOT_SURE.lower() or _NOT_SURE_TEXT.search(t):
        _finalize_rca(s, area, eq, cause, None, who, expert)
        return
    idx = _match_branch(node, t)
    if idx is None and (len(t.split()) < 4 or any(t.lower() == o["label"].lower()
                                                   for q in tree["questions"] for o in q["options"])):
        _side_turn(s, t)  # a stray tap or a short remark, not an explanation: note it and repeat the why
        return
    if idx is None:
        # the field operator knows their plant: their own explanation becomes the root cause
        rca["chain"].append({"why": node["text"], "because": t, "own": True})
        root = {"type": "root", "label": t[0].upper() + t[1:], "category": rca["category"], "correct": [],
                "prevent": ["Review this root cause with the maintenance engineer and add a preventive task to the PM plan"]}
        _finalize_rca(s, area, eq, cause, root, who, expert)
        return
    br = node["branches"][idx]
    rca["chain"].append({"why": node["text"], "because": br["label"]})
    rca["node"].append(idx)
    if br["then"]["type"] == "root":
        _finalize_rca(s, area, eq, cause, br["then"], who, expert)
    else:
        _ask_why(s, cause, who, expert, lead=_vary(s, ["I see.", "Okay.", "Understood.", "Right, that makes sense."], "why")
                 + " One more question.")


def _llm_why_fallback(s: dict, area: dict, eq: dict) -> None:
    """The LLM confirmed a direct cause, then became unavailable: continue on the matching knowledge-brain cause."""
    tree = tree_for(eq["kind"])
    rca = s["state"]["rca"]
    want = set(knowledge.tokenize(rca["direct_cause"]))
    best = max(tree["causes"], key=lambda c: len(want & set(knowledge.tokenize(c["label"]))) / (len(want) or 1))
    if len(want & set(knowledge.tokenize(best["label"]))) / (len(want) or 1) < 0.34 or not best.get("why"):
        finding = next((m for m in reversed(messages(s["id"])) if m["type"] == "finding"), {})
        _finalize_rca(s, area, eq, {"steps": finding.get("steps") or [], "case": None}, None, "SiteBrain")
        return
    rca.update(cause=best["id"], node=[], chain=[])
    s["state"]["phase"] = "why"
    _ask_why(s, best, "SiteBrain", False, lead="Let's keep going from my own notes on "
                                                f"{best['label'].lower()}.")


def _finalize_rca(s: dict, area: dict, eq: dict, cause: dict, root: dict | None, who: str, expert: bool = False) -> None:
    st = s["state"]
    rca = st["rca"]
    if root:
        root_label, category = root["label"], root["category"]
        prevent, extra = root["prevent"], root.get("correct") or []
    else:
        root_label = rca["chain"][-1]["because"] if rca["chain"] else rca["direct_cause"]
        category, extra = rca["category"], []
        prevent = ["Review this failure at the next maintenance meeting and agree a preventive task"]
    cases = [c for c in (cause.get("case"), (root or {}).get("case")) if c]
    steps = list(cause["steps"]) + [x for x in extra if x not in cause["steps"]]
    rules = _rules_for(s, area, eq)
    complete = bool(root) and not (rca["chain"] and rca["chain"][-1].get("own"))
    add_msg(s["id"], "solution", who=who, expert=expert, root_cause=root_label, direct_cause=rca["direct_cause"],
            category=category, category_label=CATEGORY_LABEL.get(category, category), why_chain=rca["chain"],
            steps=steps, preventive=prevent, safety=next((r["action"] for r in rules), None),
            basis=("past case " + ", ".join(cases) + " and " if cases else "") + "your field checks"
                  + (" and answers" if rca["chain"] else ""),
            text="Found the root cause." if complete else "Here's what we know.")
    rca.update(root=root_label, category=category, prevent=prevent)
    s["identified"] = 1
    s["root_cause"], s["steps"] = root_label, steps
    s["cited"] = sorted(set(s["cited"]) | set(cases))
    s["identified_at"] = s.get("identified_at") or db.now_iso()
    _start_fix(s, who, expert, steps, prevent)


def _post_turn_checks(s: dict) -> None:
    """Escalation triggers evaluated deterministically after every bot turn (SRS §4.2); they suggest, never escalate."""
    s = load_session(s["id"])
    if s["mode"] != "bot" or s["identified"]:
        return
    st = s["state"]
    reason = None
    if st.get("contradiction"):
        reason = f"Physical input contradicts SCADA telemetry — {st['contradiction']}"
    elif "particles" in st.get("flags", []):
        reason = "Critical safety risk: solid particle ingress toward gas compressors"
    elif s["turns"] >= config.MAX_DIAGNOSTIC_TURNS and s["confidence"] < config.CONFIDENCE_THRESHOLD \
            and not st.get("rca"):
        reason = (f"{config.MAX_DIAGNOSTIC_TURNS} diagnostic checks without root-cause confidence above "
                  f"{int(config.CONFIDENCE_THRESHOLD * 100)}%")
    elif st.get("unidentified"):
        reason = "Observations do not match any known cause in the knowledge base"
    if reason:
        suggest_escalation(s, reason)
        save_session(s)


# ---------------------------------------------------------------------------
# LLM path (Claude, Groq or any OpenAI-compatible model)
# ---------------------------------------------------------------------------

def _why_outline(node, depth: int = 0) -> list[str]:
    """Compact text rendering of a why tree for the LLM."""
    if not node:
        return []
    if node["type"] == "root":
        return [f"{'  ' * depth}ROOT [{node['category']}]: {node['label']} → prevent: {'; '.join(node['prevent'][:2])}"]
    out = [f"{'  ' * depth}WHY? {node['text']}"]
    for b in node["branches"]:
        out.append(f"{'  ' * (depth + 1)}- {b['label']}")
        out += _why_outline(b["then"], depth + 2)
    return out


def knowledge_context(s: dict, area: dict, eq: dict) -> str:
    tree = tree_for(eq["kind"])
    topo = topology.context_for(eq)
    rep = s["report"]
    lines = [
        f"EQUIPMENT: {eq['name']} | Area: {area['name']} | Type: {eq['kind']} | Site: {s['site_code']}",
        f"PROCESS TOPOLOGY: {topo['path']}",
        f"ISSUE REPORTED BY FIELD OPERATOR ({rep.get('reported_by')}, {rep.get('reported_at')}):",
        f"- Symptoms: {', '.join(rep.get('symptom_labels') or []) or 'none selected'}",
        f"- Severity (field operator's assessment): {rep.get('severity')}",
        f"- Description: {rep.get('description') or '—'}",
    ]
    snap = telemetry.snapshot(eq, condition(s))
    lines += ["", "SCADA LAST 30 MIN (oldest→newest):"]
    lines += [f"- {k}: {v}" for k, v in snap["tags"].items()]
    for prof in conditions_for(area["code"]):
        lines += ["", f"NORMAL OPERATING CONDITIONS — {prof['title']}:"]
        lines += [f"- {p[0]}: {p[1]}" for p in prof["params"][:8]]
    mk = MAINTENANCE.get(eq["kind"])
    if mk:
        lines += ["", f"MAINTENANCE KNOWLEDGE — {eq['kind']}: {mk.get('summary', '')}"]
        lines += [f"- limit: {a} {b}" for a, b in mk.get("operating_limits", [])[:6]]
        lines += [f"- PM {a}: {b}" for a, b in mk.get("pm", [])[:6]]
    # full 5-Why trees only for the leading causes; root causes alone for the rest (keeps the prompt small)
    lead = {c["label"].lower() for c in s["causes"][:2]} | {(s["state"].get("rca") or {}).get("direct_cause", "").lower()}
    lines += ["", "FISHBONE OF DIRECT CAUSES (6M category | cause | immediate corrective steps | 5-Why):"]
    for c in tree["causes"]:
        lines.append(f"* [{c.get('category', 'Machine')}] {c['label']} | {'; '.join(c['steps'][:3])}")
        if c["label"].lower() in lead:
            lines += ["    " + x for x in _why_outline(c.get("why"))]
        else:
            lines.append("    root causes: " + "; ".join(f"{r['label']} [{r['category']}]" for r in roots(c.get("why"))[:4]))
    lines += ["", "FIELD CHECKS AVAILABLE:"] + [f"- {q['text']} options: {' / '.join(o['label'] for o in q['options'])}"
                                                for q in tree["questions"]]
    cases = knowledge.match_cases(eq["kind"], report_hint(rep), s["site_code"])[:5]
    lines += ["", "PREVIOUS PROBLEMS & INCIDENTS (id | symptom | root cause | why chain | category | fix | prevention):"]
    lines += [f"{c['id']} | {c['title']} | {c['cause']} | {' > '.join(c.get('why_chain') or [])[:300]} | "
              f"{c.get('category') or '-'} | {c['fix'][:160]} | {(c.get('prevent') or '-')[:120]}" for c in cases]
    found = knowledge.search(f"{eq['kind']} {eq['name']} {report_hint(rep)}", s["site_code"], 8)
    docs = [d for d in found if _covers(d, eq["kind"])][:3]  # passages about this equipment, not just similar words
    if docs:
        lines += ["", "MANUAL / SOP EXCERPTS:"] + [f"[{d['title']}] {d['excerpt'][:350]}" for d in docs]
    return "\n".join(lines)


def transcript(sid: str) -> list[dict]:
    out = []
    for m in messages(sid):
        if m["type"] == "report":
            out.append({"role": "user", "content": f"Issue report on {m.get('equipment') or m.get('area')}: {m['text']} "
                                                   f"(severity {m.get('severity')})"})
        elif m["type"] == "user" or (m["type"] == "escalation" and m.get("text")):
            files = ", ".join(f["filename"] for f in m.get("attachments") or [])
            read = " ".join(media.as_text(f.get("analysis")) for f in m.get("attachments") or [] if f.get("analysis"))
            out.append({"role": "user", "content": " ".join(x for x in [m["text"], f"[attached: {files}]" if files else "",
                                                                        read] if x)})
        elif m["type"] == "agent":
            out.append({"role": "assistant", "content": (f"{m.get('who')}: " if m.get("expert") else "") + m["text"]})
        elif m["type"] == "finding":
            out.append({"role": "assistant", "content": f"Direct cause found: {m['direct_cause']} [{m.get('category')}]. "
                                                        f"Immediate actions: {'; '.join(m.get('steps') or [])}"})
        elif m["type"] == "solution":
            chain = " > ".join(f"{w['why']} {w['because']}" for w in m.get("why_chain") or [])
            out.append({"role": "assistant", "content": f"Root cause: {m['root_cause']}. Why chain: {chain or '-'}. "
                                                        f"Steps: {'; '.join(m['steps'])}"})
    while out and out[0]["role"] != "user":
        out.pop(0)
    merged = []
    for m in out:
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1]["content"] += "\n" + m["content"]
        else:
            merged.append(dict(m))
    return merged


def _bot_system(s: dict, area: dict, eq: dict) -> str:
    return "\n".join([
        "You are SiteBrain, the operations copilot for a compressed-biogas plant (digesters, feeding, solid-liquid "
        "separation, HWG, biogas upgradation). A field operator reported an issue on the equipment below. Work "
        "through it with them using standard root cause analysis: a FISHBONE (6M: Man, Machine, Method, Material, "
        "Measurement, Environment) to find the direct cause, then 5-WHY to find the systemic root cause.",
        "",
        "HOW TO TALK: like a colleague messaging on WhatsApp. Crisp, warm, plain words, second person. A whole message "
        "is at most 3 short sentences: `reply` is ONE short sentence saying what their answer means (what it rules out "
        "or points to), and `instruction` is one or two short sentences. Keep it safe (LOTO, gas test) in few words "
        "when relevant. No jargon, no emoji, no apologies, no repeating what they said. The field operator is "
        f"{s['report'].get('reported_by') or 'the field operator'}; use their name now and then, never 'Tech'.",
        "", knowledge_context(s, area, eq), "",
        "METHOD",
        "- The field operator does not decide what to do next: YOU direct them. They follow your instruction and "
        "report what they found.",
        "- stage 'fishbone': every turn, `reply` acknowledges the last answer and says what it means (no question, "
        "no list of options). `instruction` is ONE concrete physical check, written as a direction ending in what to "
        "report, e.g. \"With the pump isolated under LOTO, look at the seal face: is it scored or chipped?\". It is the "
        "check that best separates the remaining causes across the fishbone. `purpose` says in one short sentence why it "
        "matters; `how` says how to do it safely. `quick_replies` are 2-4 short possible RESULTS of that check — what "
        "the operator would observe (e.g. \"Seal face scored\", \"Seal face looks fine\", \"Leaking at the gland\") — "
        "NEVER actions, checks or suggestions (not \"Inspect the seal\", \"Measure pressure\"). Add \"I can't check this\" "
        "when it may be hard to do. The operator can pick several results at once (sent joined by \"; \"): weigh every "
        "one. Return causes with 6M category and likelihoods summing to ~1 after every answer.",
        "- The operator may have answered several checks at once (a 'Present condition' message): weigh every answer "
        "and never ask those checks again.",
        "- In stages 'why' and 'done' set instruction, purpose and how to null.",
        "- When one direct cause reaches likelihood >= 0.85, set stage 'why', fill direct_cause, fishbone_category and "
        "immediate_actions (3-5 corrective steps), and ask the first WHY question (use the cause's 5-Why tree as a guide, "
        "but accept the field operator's own explanation). Quick replies = likely answers + \"Not sure\".",
        "- In stage 'why', `reply` ALWAYS ends with the one WHY question (ending in \"?\"), and `quick_replies` are 2-4 "
        "likely answers to it — reasons, e.g. \"Screen was not cleaned\", \"No PM for the screen\" — plus \"Not sure\". "
        "Never tests, checks or actions as quick replies.",
        "- In stage 'why' ask one why per turn, appending to why_chain [{why, because}]. STOP as soon as an answer names "
        "a systemic gap — a missing or wrong procedure/SOP/checklist step, PM schedule, training, spares, feed-quality "
        "control, instrument calibration, design or environment — that IS the root cause; don't ask why about "
        "management decisions. Also stop after 4 whys or when they are not sure: "
        "then set stage 'done', identified=true, root_cause, fishbone_category of the root, steps (corrective) and "
        "preventive_actions. Cite case ids used.",
        "- Safety is enforced by a separate deterministic engine. If an answer reveals solid particles heading to "
        "compressors, bed channeling, gas leak, critical rotating-equipment condition, water carryover, low compressor "
        "oil, off-spec methane purity or H2S breakthrough, add the matching hazard_flags value.",
        "- If answers match no known cause during the fishbone stage, set unidentified=true.",
    ])


# A quick reply that tells the operator to do something is an action, not a result they observed
_ACTION_REPLY = re.compile(r"^(inspect|check|measure|listen|verify|look|test|open|replace|clean|tighten|confirm|monitor|"
                           r"record|ensure|isolate|remove|perform|examine|take|compare|observe|investigate|review|"
                           r"adjust|flush|drain|refill|top up|lubricate|restart|stop|run|install|repair|clear|"
                           r"unclog|reset|calibrate|contact|call|escalate|consider|try)\b", re.I)


def _llm_check(s: dict, area: dict, eq: dict, data: dict) -> None:
    """Direct the field operator to the LLM's next fishbone check, with its possible results as answers. When the
    model offers actions as answers or gives no instruction, ask the decision tree's next check instead."""
    st = s["state"]
    reply = (data.get("reply") or "").strip()
    instruction = (data.get("instruction") or "").strip()
    results = [r.strip() for r in data.get("quick_replies") or [] if r.strip() and r.strip() != CANT]
    if instruction and results and not any(_ACTION_REPLY.match(r) for r in results):
        # the same check as a decision-tree one (the LLM is shown them with their answers): record it as asked, so a
        # decision-tree turn during an LLM outage reads the answer against it and never asks it again
        said = {r.lower() for r in results}
        same = next((q for q in tree_for(eq["kind"])["questions"]
                     if len(said & {o["label"].lower() for o in q["options"]}) >= 2), None)
        st["pending"] = same["id"] if same else None
        if same and same["id"] not in st["asked"]:
            st["asked"].append(same["id"])
        add_msg(s["id"], "agent", who="SiteBrain", text=f"{reply} {instruction}".strip(), prompt=instruction,
                purpose=data.get("purpose"), how=data.get("how"), multi=True,
                replies=results[:4] + ([HOW] if data.get("how") else []) + [CANT])
        return
    tree = tree_for(eq["kind"])
    q = pick_question(tree, st["posterior"], st["asked"], report_hint(s["report"])) if st.get("posterior") else None
    if q:
        st["asked"].append(q["id"])  # the LLM sees the answer in the transcript; don't ask this check twice
        _ask(s, q, lead=reply + (" Next:" if reply else ""))
    else:
        add_msg(s["id"], "agent", who="SiteBrain",
                text=f"{reply} Tell me in your own words what you see at {eq['name']} right now — sound, temperature, "
                     "leaks, readings on the local gauges.".strip(),
                prompt="What do you see?", replies=[CANT])


def _llm_bot_turn(s: dict, area: dict, eq: dict, text: str | None) -> bool:
    conv = transcript(s["id"])
    data = llm.complete_json(_bot_system(s, area, eq), conv, llm.BOT_SCHEMA)
    if data is None:
        return False
    st = s["state"]
    if data.get("causes"):
        tot = sum(max(0.0, c["likelihood"]) for c in data["causes"]) or 1
        s["causes"] = sorted([{"label": c["label"], "category": c.get("category") or "Machine",
                               "likelihood": round(max(0.0, c["likelihood"]) / tot, 3)}
                              for c in data["causes"]], key=lambda c: -c["likelihood"])[:6]
        s["confidence"] = s["causes"][0]["likelihood"]
    s["cited"] = sorted(set(s["cited"]) | set(data.get("cited_cases") or []))
    before = set(st.get("flags", []))
    flags = before | (set(data.get("hazard_flags") or []) & set(safety.HAZARD_FLAGS))
    st["flags"] = sorted(flags)
    if flags - before:
        _apply_safety(s, area, eq)
    stage = data.get("stage") or ("done" if data.get("identified") else "fishbone")
    rules = _rules_for(s, area, eq)
    if stage in ("why", "done") and data.get("direct_cause") and not st.get("rca"):
        cat = data.get("fishbone_category") or "Machine"
        add_msg(s["id"], "finding", who="SiteBrain", direct_cause=data["direct_cause"], category=cat,
                category_label=CATEGORY_LABEL.get(cat, cat), confidence=s["confidence"],
                steps=data.get("immediate_actions") or data.get("steps") or [], safety=next((r["action"] for r in rules), None),
                text=f"I'm now fairly confident the direct cause is {data['direct_cause'].lower()}. "
                     "Make it safe and put it right with the steps below.")
        st["rca"] = {"cause": None, "direct_cause": data["direct_cause"], "category": cat, "chain": [], "node": []}
        s["identified_at"] = s.get("identified_at") or db.now_iso()
    if stage == "done" and data.get("identified") and data.get("root_cause"):
        cases = data.get("cited_cases") or []
        chain = [{"why": w.get("why", ""), "because": w.get("because", "")} for w in data.get("why_chain") or []]
        cat = data.get("fishbone_category") or (st.get("rca") or {}).get("category") or "Machine"
        add_msg(s["id"], "solution", who="SiteBrain", root_cause=data["root_cause"],
                direct_cause=(st.get("rca") or {}).get("direct_cause") or data.get("direct_cause"),
                category=cat, category_label=CATEGORY_LABEL.get(cat, cat), why_chain=chain,
                steps=data.get("steps") or [], preventive=data.get("preventive_actions") or [],
                basis=("past case " + ", ".join(cases) + " and " if cases else "") + "your field checks and answers",
                safety=next((r["action"] for r in rules), None), text="Found the root cause.")
        st["rca"] = {**(st.get("rca") or {}), "chain": chain, "root": data["root_cause"], "category": cat,
                     "prevent": data.get("preventive_actions") or []}
        s["identified"] = 1
        s["root_cause"], s["steps"] = data["root_cause"], data.get("steps") or []
        s["identified_at"] = s.get("identified_at") or db.now_iso()
        s["confidence"] = max(s["confidence"], config.CONFIDENCE_THRESHOLD)
        _start_fix(s, "SiteBrain", False, data.get("steps") or [], data.get("preventive_actions") or [])
    elif stage == "fishbone":
        _llm_check(s, area, eq, data)
        st["unidentified"] = bool(data.get("unidentified"))
    elif stage == "why" and "?" not in (data.get("reply") or "") and st.get("rca"):
        # no why question asked: the knowledge brain's 5-Why takes over when it has this cause, else ask it plainly
        if not st["rca"].get("chain"):
            _llm_why_fallback(s, area, eq)
        else:
            add_msg(s["id"], "agent", who="SiteBrain", text=f"{data.get('reply') or ''} Why did that happen?".strip(),
                    prompt="Why did that happen?", why_step=len(st["rca"]["chain"]) + 1, replies=[NOT_SURE, SKIP_WHY])
    else:
        replies = data.get("quick_replies") or []
        add_msg(s["id"], "agent", who="SiteBrain", text=data.get("reply") or "Tell me what you see.", replies=replies,
                why_step=(len(data.get("why_chain") or []) + 1) if stage == "why" else None)
        if stage == "why" and st.get("rca") and data.get("why_chain"):
            st["rca"]["chain"] = [{"why": w.get("why", ""), "because": w.get("because", "")} for w in data["why_chain"]]
    save_session(s)
    return True


# ---------------------------------------------------------------------------
# Escalation & expert
# ---------------------------------------------------------------------------

def checkpoint_matrix(s: dict, eq: dict | None) -> list[dict]:
    """Diagnostic matrix for the expert: what was reported, then every field check and its answer."""
    prefix = {"Scrubber": "SCR", "Filter": "FLT", "Compressor": "CMP", "Chiller": "CHL", "Membrane": "MEM"}.get(
        eq["kind"], eq["kind"][:3].upper()) if eq else "GEN"
    rep = s["report"]
    rows = [{"checkpoint_id": f"CHK-{prefix}-R{j + 1:02d}", "description": label, "status": "FAILED",
             "operator_input": f"Reported · {rep.get('severity')}", "expected": "Not present", "source": "issue report"}
            for j, label in enumerate(rep.get("symptom_labels") or [])]
    if rep.get("description"):
        rows.append({"checkpoint_id": f"CHK-{prefix}-R{len(rows) + 1:02d}", "description": "Field operator's description",
                     "status": "RECORDED", "operator_input": rep["description"][:160], "expected": "—",
                     "source": "issue report"})
    for j, a in enumerate(s["state"].get("answers", [])):
        rows.append({"checkpoint_id": f"CHK-{prefix}-F{j + 1:02d}", "description": a["question"],
                     "status": "FAILED" if a.get("flags") else "RECORDED", "operator_input": a["answer"],
                     "expected": "—", "source": "guided diagnosis"})
    for j, w in enumerate((s["state"].get("rca") or {}).get("chain", [])):
        rows.append({"checkpoint_id": f"CHK-{prefix}-W{j + 1:02d}", "description": w["why"], "status": "RECORDED",
                     "operator_input": w["because"], "expected": "—", "source": "5-Why"})
    return rows


def suggest_escalation(s: dict, reason: str) -> None:
    """An escalation trigger fired (SRS §4.2). Escalating is the field operator's call: recommend it once per reason,
    with an Escalate button, and keep helping in the meantime. The reason goes with the escalation if they take it."""
    st = s["state"]
    if reason in st.get("suggested", []):
        return
    st.setdefault("suggested", []).append(reason)
    add_msg(s["id"], "offer", reason=reason,
            text="I'd recommend bringing in a technical expert. Or I'll keep helping — you can continue the chat and we "
                 "will try to resolve it together.")


MAX_ATTACHMENTS = 5
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


def _check_files(attachments: list[dict]) -> None:
    if len(attachments) > MAX_ATTACHMENTS:
        raise SessionError(f"Attach at most {MAX_ATTACHMENTS} files")
    big = [a["filename"] for a in attachments if len(a["data"]) > MAX_ATTACHMENT_BYTES]
    if big:
        raise SessionError(f"Files must be {MAX_ATTACHMENT_BYTES // (1024 * 1024)} MB or smaller: {', '.join(big)}")
    if any(not a["data"] for a in attachments):
        raise SessionError("An attached file is empty")


def save_files(sid: str, user: dict, attachments: list[dict]) -> list[dict]:
    """Files shared in the chat (photos, PDFs, spreadsheets …): stored on the session, and handed to the expert's
    ticket if the issue is escalated later. Returns their metadata for the message."""
    _check_files(attachments)
    if not attachments:
        raise SessionError("No file attached")
    s = load_session(sid)
    if s["status"] in ("resolved", "closed"):
        raise SessionError("Session is closed. Report a new issue.", 409)
    esc = latest_escalation(sid) if s["mode"] == "expert" else None
    now, out = db.now_iso(), []
    for a in attachments:
        f = {"filename": a["filename"], "content_type": a["content_type"], "size": len(a["data"])}
        f["id"] = db.insert("attachments", {"ticket": esc["ticket"] if esc else None, "session_id": sid, **f,
                                            "data": a["data"], "uploaded_by": user["name"], "created_at": now})
        out.append(f)
    db.audit(user["name"], user["role"], "chat.files_shared", sid, {"files": [f["filename"] for f in out]},
             s["site_code"])
    return out


# helper replies that are not observations a photo or a voice note could show
_NOT_OBSERVATIONS = {HOW, CANT, NOT_SURE, SKIP_WHY, DONE, STEP_HOW, STEP_CANT, ALL_STEPS, WORKING, NOT_WORKING, CLOSE_REPLY}


def _media_context(s: dict, check_id: str | None) -> tuple[str, dict | None]:
    """What the attachment is about (equipment, report) and the check it may answer: the given condition check, or
    the question pending in the chat. No check while fixing (a photo never taps Done)."""
    area, eq = load_area(s["area_id"]), session_eq(s)
    rep = s["report"]
    ctx = (f"{eq['name']} ({eq['kind']}) in {area['name']}" if eq else f"somewhere in {area['name']}") + \
          f"; reported: {s['symptom'] or 'an abnormal condition'}; severity {rep.get('severity') or s['severity']}"
    if check_id and eq:
        q = next((q for q in tree_for(eq["kind"])["questions"] if q["id"] == check_id), None)
        return ctx, ({"text": q["text"], "options": [o["label"] for o in q["options"]]} if q else None)
    if s["state"].get("phase") in ("fix", "verify") or s["state"].get("survey"):
        return ctx, None
    p = _last_prompt(s["id"])
    opts = [r for r in (p or {}).get("replies") or [] if r not in _NOT_OBSERVATIONS]
    return ctx, ({"text": p.get("prompt") or p.get("text"), "options": opts} if p and opts else None)


def share_files(sid: str, user: dict, text: str, files: list[dict], caption: str = "", raw: list[dict] | None = None,
                check_id: str | None = None) -> None:
    """A chat message carrying files. With text it is an ordinary turn; files alone are acknowledged and the
    pending question or step is put back. With a caption (evidence for the report or for one check) the files
    are just filed under it: no turn, so the checks carry on undisturbed.

    While SiteBrain is troubleshooting, the files are read (media.py) before anything else: a voice note's words
    become the message, a photo or video that clearly shows one answer of the pending check answers it, and what
    every file shows goes into the conversation. Once escalated they go to the expert as they are."""
    s = load_session(sid)
    text = (text or "").strip()
    if s["mode"] == "bot" and raw and media.enabled():
        ctx, question = _media_context(s, check_id)
        tq = None
        if check_id and session_eq(s):
            tq = next((q for q in tree_for(session_eq(s)["kind"])["questions"] if q["id"] == check_id), None)
        for f, a in zip(files, raw):
            res = media.analyze(a, ctx, question)
            if res and tq and res.get("kind") == "audio" and res.get("english"):
                i = match_option(tq, res["english"])  # a spoken answer to the check, matched like a typed one
                res["answer"] = tq["options"][i]["label"] if i is not None else None
            if res:
                f["analysis"] = res
    read = [media.as_text(f.get("analysis")) for f in files if (f.get("analysis") or {}).get("summary")]
    if caption.strip():
        add_msg(sid, "user", text=caption.strip()[:200], author=user["name"], attachments=files, evidence=True,
                **({"check_id": check_id} if check_id else {}))
        if read:
            s["state"].setdefault("notes", []).extend({"text": f"{caption.strip()[:80]}: {r}", "at": db.now_iso()}
                                                      for r in read)
            save_session(s)
        return
    if read and s["mode"] == "bot":
        answers = {f["analysis"]["answer"] for f in files if (f.get("analysis") or {}).get("answer")}
        spoken = [f["analysis"]["summary"] for f in files if (f.get("analysis") or {}).get("kind") == "audio"
                  and f["analysis"].get("summary")]
        if not text and len(answers) == 1 and not spoken:
            heard = answers.pop()  # the photo shows the answer to the pending check
        else:
            heard = " ".join([text] + read).strip()
        send(sid, heard, user, files=files, display=text)
        return
    if user["role"] == "expert" and s["mode"] == "expert":
        human_expert_message(sid, user, text, None, None, files)
        return
    if text:
        send(sid, text, user, files=files)
        return
    add_msg(sid, "user", text="", author=user["name"], attachments=files)
    if s["mode"] == "expert":
        return  # the expert sees the files; SiteBrain stays out of the conversation
    names = _join([f["filename"] for f in files])
    prompt = _last_prompt(sid)
    who, expert = _who(s)
    add_msg(sid, "agent", who=who, expert=expert, side=True,
            text=f"Thanks — I've added {names} to this case. They go to the expert with everything else if you "
                 "escalate. Tell me in words what they show and I'll factor it in.",
            prompt=(prompt.get("prompt") or prompt.get("text")) if prompt else None, how=prompt.get("how") if prompt else None,
            fix_step=prompt.get("fix_step") if prompt else None, fix_total=prompt.get("fix_total") if prompt else None,
            why_step=prompt.get("why_step") if prompt else None, replies=prompt.get("replies") if prompt else None,
            multi=bool(prompt and prompt.get("multi")))


def chat_summary(sid: str) -> str:
    """A short summary of the chat so far, for the expert taking over (the operator sees it before escalating).
    Written by the LLM when one is set up, else put together from the report, the checks and the causes."""
    s = load_session(sid)
    area, eq = load_area(s["area_id"]), session_eq(s)
    st, rep = s["state"], s["report"] or {}
    where = f"{eq['name']} ({eq['kind']}) in {area['name']}" if eq else f"{area['name']} (equipment not identified)"
    if llm.available():
        conv = transcript(sid)
        if conv:
            text = "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in conv)[-12000:]
            res = llm.complete_json(
                "You hand a plant troubleshooting chat over to a technical expert. Summarise it in at most 120 words of "
                "plain sentences: the problem and where, what the field operator checked and found, the likely causes "
                "so far, anything already tried, and what is still open. No greeting, no markdown. "
                "JSON {\"summary\": str}.",
                [{"role": "user", "content": f"Equipment: {where}\n\n{text}"}],
                {"type": "object", "additionalProperties": False, "required": ["summary"],
                 "properties": {"summary": {"type": "string"}}}, max_tokens=500)
            if (res or {}).get("summary", "").strip():
                return res["summary"].strip()
    lines = [f"{s['symptom'] or 'Issue reported'} on {where}, severity {s['severity']}."]
    if rep.get("description"):
        lines.append(f"Operator's description: {rep['description']}")
    answered = [a for a in st.get("answers", []) if a.get("answer")]
    if answered:
        lines.append("Checks done: " + "; ".join(f"{a['question']} — {a['answer']}" for a in answered) + ".")
    skipped = len(st.get("skipped", []))
    if skipped:
        lines.append(f"{skipped} check{'s' if skipped != 1 else ''} could not be done.")
    if not answered and not skipped:
        lines.append("No checks have been answered yet.")
    found = next((m for m in reversed(messages(sid)) if m["type"] in ("finding", "solution")), None)
    if found:
        lines.append(f"SiteBrain's finding: {found.get('root_cause') or found.get('direct_cause')}.")
    elif s["causes"]:
        lines.append("Likely causes: " + ", ".join(f"{c['label']} ({round(c['likelihood'] * 100)}%)"
                                                   for c in s["causes"][:3]) + ".")
    flagged = st.get("suggested") or []
    if flagged:
        lines.append(f"Escalation suggested because: {'; '.join(flagged)}.")
    return "\n".join(lines)


def escalate(sid: str, user: dict, reason: str, description: str = "", attachments: list[dict] | None = None,
             chat_sum: str = "") -> dict:
    """Hand the session to an L2/L3 expert. Only ever when the field operator taps Escalate, with their own
    description and attachments ({filename, content_type, data}) for the expert's detailed analysis, and the
    summary of the chat they saw (written here when they sent none)."""
    description = (description or "").strip()
    chat_sum = (chat_sum or "").strip()[:4000] or chat_summary(sid)
    attachments = attachments or []
    _check_files(attachments)
    s = load_session(sid)
    if s["mode"] == "expert":
        raise SessionError("Session is already with an expert", 409)
    if s["status"] in ("resolved", "closed"):
        raise SessionError("Session is closed", 409)
    flagged = s["state"].get("suggested") or []
    if flagged:
        reason = f"{reason} · SiteBrain flagged: {'; '.join(flagged)}"
    area, eq = load_area(s["area_id"]), session_eq(s)
    site = db.q1("SELECT * FROM sites WHERE code=?", (s["site_code"],))
    interlocks = db.q("SELECT * FROM interlocks WHERE status!='released' AND (session_id=? OR equipment_id=?)",
                      (sid, eq["id"] if eq else ""))
    with escalation.Stopwatch() as sw:
        ticket = f"ESC-{area['code']}-{db.next_counter('ticket', 141)}"
        crit = s["severity"] == "Critical" or any(i["severity"] == "CRITICAL" for i in interlocks) \
            or "particles" in s["state"].get("flags", [])
        urgency = "Critical" if crit else ("High" if s["severity"] == "High" or interlocks else "Medium")
        snap = telemetry.snapshot(eq, condition(s)) if eq else {"tags": {}}
        conv = [{"role": "field operator" if m["type"] in ("user", "report") else (m.get("who") or "SiteBrain"),
                 "text": " ".join(x for x in [m.get("text") or (f"Root cause: {m.get('root_cause')}"
                                                                if m["type"] == "solution" else "")]
                                  + [media.as_text(f.get("analysis")) for f in m.get("attachments") or []] if x)}
                for m in messages(sid) if m["type"] in ("report", "user", "agent", "analysis", "solution")]
        payload = escalation.build_payload(ticket, site, area, eq, s, checkpoint_matrix(s, eq), conv, snap,
                                           interlocks, urgency, reason, s["causes"])
        files = [{"filename": a["filename"], "content_type": a["content_type"], "size": len(a["data"])} for a in attachments]
        payload["operator_request"] = {"requested_by": user["name"], "description": description, "attachments": files}
        payload["chat_summary"] = chat_sum
        _, role_label = escalation.target_role(eq["kind"] if eq else None)
        top = s["causes"][0]["label"] if s["causes"] else None
        summary = f"{s['symptom']}. " + (f"Leading hypothesis: {top}." if top
                                          else f"Equipment not yet identified in {area['name']}." if not eq else "")
        escalation.dispatch(ticket, payload, attachments, escalation.expert_emails(s["site_code"]))
    db.insert("escalations", {
        "ticket": ticket, "session_id": sid, "site_code": s["site_code"], "area_id": area["id"],
        "equipment_id": eq["id"] if eq else None, "urgency": urgency, "summary": summary.strip(),
        "trigger_reason": reason, "expert_name": UNASSIGNED, "expert_role": role_label,
        "status": "Active", "turns": s["turns"], "payload": payload, "compile_ms": sw.ms, "created_at": db.now_iso(),
    })
    now = db.now_iso()
    # files shared earlier in the chat go to the expert too
    db.ex("UPDATE attachments SET ticket=? WHERE session_id=? AND ticket IS NULL", (ticket, sid))
    for a, f in zip(attachments, files):
        f["id"] = db.insert("attachments", {"ticket": ticket, "session_id": sid, **f, "data": a["data"],
                                            "uploaded_by": user["name"], "created_at": now})
    add_msg(sid, "escalation", ticket=ticket, author=user["name"], text=description, attachments=files,
            summary=chat_sum)
    event(sid, f"Sent to the technical experts · {ticket}", "account-arrow-up-outline", "warn")
    save_session(s, mode="expert", status="escalated")
    db.audit(user["name"], user["role"], "escalation.dispatched", ticket,
             {"session": sid, "urgency": urgency, "trigger": reason, "compile_ms": sw.ms,
              "attachments": [f["filename"] for f in files]}, s["site_code"])
    event(sid, "The experts have been notified by email with this chat, your photos and readings. They will reply "
               "here when they can — you don't need to wait on this screen. You'll be notified when they reply.",
          "email-fast-outline", "info")
    return db.q1("SELECT * FROM escalations WHERE ticket=?", (ticket,))


UNASSIGNED = "Unassigned"  # escalations.expert_name until an expert claims the ticket


def _expert_who(esc: dict | None) -> str:
    name = (esc or {}).get("expert_name")
    return f"{name} · Technical Expert" if name and name != UNASSIGNED else "Technical Expert"


def human_expert_message(sid: str, user: dict, text: str, root_cause: str | None, steps: list[str] | None,
                         files: list[dict] | None = None) -> None:
    s = load_session(sid)
    esc = latest_escalation(sid)
    if not esc:
        raise SessionError("Session has no escalation", 409)
    if not esc["claimed_by"]:
        db.update("escalations", "ticket", esc["ticket"], {"claimed_by": user["id"], "expert_name": user["name"],
                                                           "status": "In Progress"})
        event(sid, f"{user['name']} ({user.get('title') or 'Technical Expert'}) is looking into this", "account-check-outline")
    if not esc["first_response_at"]:
        db.update("escalations", "ticket", esc["ticket"], {"first_response_at": db.now_iso()})
    who = f"{user['name']} · Technical Expert"
    if text or files:
        add_msg(sid, "agent", who=who, expert=True, text=text, **({"attachments": files} if files else {}))
    if root_cause and steps:
        add_msg(sid, "solution", who=user["name"], expert=True, root_cause=root_cause, steps=steps, basis="expert assessment")
        save_session(s, identified=1, root_cause=root_cause, steps=steps, identified_at=db.now_iso())
    escalation.notify_reporter(esc["ticket"], s, user["name"], text, root_cause)
    db.audit(user["name"], user["role"], "expert.message", sid, {"solution": bool(root_cause)}, s["site_code"])


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def _check_can_close(user: dict) -> None:
    if user["role"] != "field_operator":
        raise SessionError("Only the field operator can mark an issue resolved and close it", 403)


def mark_resolved(sid: str, user: dict, note: str = "") -> dict:
    """Close the issue. With a confirmed solution the RCA is saved as a knowledge-base case; otherwise it is logged
    to case history as closed, with the field operator's note on how it was settled."""
    _check_can_close(user)
    note = (note or "").strip()[:1000]
    s = load_session(sid)
    if s["status"] in ("resolved", "closed"):
        return s
    area, eq = load_area(s["area_id"]), session_eq(s)
    sol = next((m for m in reversed(messages(sid)) if m["type"] == "solution"), None)
    by_expert = s["mode"] == "expert"
    case_id = None
    if sol:
        hint = report_hint(s["report"])
        case_id = knowledge.next_case_id()
        chain = [f"{w['why']} {w['because']}" for w in sol.get("why_chain") or []]
        if sol.get("direct_cause"):
            chain.insert(0, f"What failed? {sol['direct_cause']}")
        db.insert("cases", {
            "id": case_id, "site_code": s["site_code"], "kinds": [eq["kind"] if eq else "Machine"],
            "keys": sorted({k for k in knowledge.CASE_KEYS if k in hint}),
            "title": f"{s['symptom'] or 'Field-reported issue'} on {eq['name'] if eq else area['name']}",
            "cause": sol["root_cause"], "fix": "; ".join(sol["steps"]), "why_chain": chain,
            "category": sol.get("category"), "prevent": "; ".join(sol.get("preventive") or []) or None,
            "equipment": eq["name"] if eq else None,
            "source": "Copilot session", "session_id": sid, "created_at": db.now_iso()})
    esc = latest_escalation(sid)
    if esc and esc["status"] != "Resolved":
        db.update("escalations", "ticket", esc["ticket"], {"status": "Resolved", "resolved_at": db.now_iso()})
    if note:
        add_msg(sid, "user", text=f"Closing note: {note}", author=user["name"])
    event(sid, f"Issue resolved and closed by {user['name']} · saved to the knowledge base as {case_id}" if sol
          else f"Issue closed by {user['name']} · logged to case history", "check-circle-outline", "ok")
    save_session(s, status="resolved" if sol else "closed", resolved_at=db.now_iso(),
                 resolved_by=("Expert" if by_expert else "SiteBrain") if sol else "Closed",
                 root_cause=s["root_cause"] or (sol["root_cause"] if sol else note or "No issue confirmed"))
    if sol:
        from . import learning
        learning.fit()  # every confirmed fix sharpens the decision tree for this equipment type
    db.audit(user["name"], user["role"], "session.resolved", sid, {"case": case_id, "by": "Expert" if by_expert else "SiteBrain",
                                                                    "note": note or None},
             s["site_code"])
    return load_session(sid)


def not_resolved(sid: str, user: dict) -> dict:
    s = load_session(sid)
    if not s["identified"]:
        raise SessionError("No resolution to reject", 409)
    st = s["state"]
    top = s["causes"][0].get("id") if s["causes"] else None
    if top and top in st.get("posterior", {}):
        st.setdefault("excluded", []).append(top)
    st.update(phase="diagnose", rca=None, pending=None, fix=None)
    save_session(s, identified=0, root_cause=None, steps=None, identified_at=None)
    return send(sid, PERSISTS, user)
