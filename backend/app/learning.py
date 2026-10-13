"""Learning the decision trees from resolved sessions.

Every session the field operator marks resolved (the fix worked) is a labelled example: the confirmed direct cause,
and the answer given to each field check on the way there. From these we update two things per equipment type:

  1. How common each direct cause is (base rate), which scales the starting point of the fishbone.
  2. How each cause tends to answer each check, P(answer | cause), which scales the check's likelihoods.

Both are Bayesian with the engineers' authored knowledge as the prior, worth LEARN_STRENGTH sessions
(Dirichlet smoothing):  P̂(answer | cause) = (α·P_authored + n_answer) / (α + n_cause_asked)
The learned likelihood is the authored one × P̂ / P_authored, so with no data nothing changes, and with
α=10 ten confirmed sessions weigh as much as the authored judgement. Authored trees are never edited;
the adjustment is applied on top (brain.set_learned) and can be switched off with SITEBRAIN_LEARNING=false.

Caveat: sessions only exist for causes SiteBrain or an expert confirmed, so learning sharpens what the plant
actually sees; it cannot discover a cause that is not in the knowledge brain. Engineers still add those.
"""
import logging
import math
from collections import Counter, defaultdict

from . import brain, config, db, knowledge

log = logging.getLogger("sitebrain.learning")
_last: dict = {}


def _cause_of(state: dict, tree: dict) -> str | None:
    """The confirmed direct cause as a tree cause id (LLM sessions are matched by label)."""
    rca = state.get("rca") or {}
    ids = {c["id"] for c in tree["causes"]}
    if rca.get("cause") in ids:
        return rca["cause"]
    label = rca.get("direct_cause")
    if not label:
        return None
    want = set(knowledge.tokenize(label))
    best, score = None, 0.0
    for c in tree["causes"]:
        have = set(knowledge.tokenize(c["label"]))
        sc = len(want & have) / (len(want | have) or 1)
        if sc > score:
            best, score = c["id"], sc
    return best if score >= 0.5 else None


def evidence() -> dict[str, list[dict]]:
    """{kind: [{cause, answers: [(question id, option label)]}]} from resolved sessions."""
    out: dict[str, list[dict]] = defaultdict(list)
    rows = db.q("SELECT s.state, e.kind FROM sessions s JOIN equipment e ON e.id=s.equipment_id "
                "WHERE s.status='resolved' AND s.identified=1")
    for r in rows:
        tree = brain.TREES.get(r["kind"])
        if not tree:
            continue
        st = db.loads(r["state"], {})
        cause = _cause_of(st, tree)
        if cause:
            out[r["kind"]].append({"cause": cause, "answers": [(a["qid"], a["answer"])
                                                               for a in st.get("answers", []) if a.get("qid")]})
    return out


def fit_models(ev: dict[str, list[dict]], strength: float) -> dict[str, dict]:
    """Pure: evidence → per-kind adjustments {prior: {cause: ×}, lik: {qid: {label: {cause: ×}}}, sessions}."""
    models = {}
    for kind, items in ev.items():
        tree = brain.TREES.get(kind)
        if not tree or not items:
            continue
        ids = [c["id"] for c in tree["causes"]]
        n_cause = Counter(i["cause"] for i in items)
        total = sum(n_cause[c] for c in ids)
        prior = {c: (strength / len(ids) + n_cause[c]) / (strength + total) * len(ids) for c in ids}
        seen: dict = defaultdict(lambda: defaultdict(Counter))  # qid → cause → label counts
        for i in items:
            for qid, label in i["answers"]:
                seen[qid][i["cause"]][label] += 1
        lik: dict = {}
        for q in tree["questions"]:
            labels = [o["label"] for o in q["options"]]
            for c, cnt in seen.get(q["id"], {}).items():
                n = sum(cnt[l] for l in labels)
                if not n:
                    continue
                raw = [o["lik"].get(c, 1.0) for o in q["options"]]
                tot = sum(raw)
                for o, r in zip(q["options"], raw):
                    p0 = r / tot
                    lik.setdefault(q["id"], {}).setdefault(o["label"], {})[c] = ((strength * p0 + cnt[o["label"]])
                                                                                 / (strength + n)) / p0
        models[kind] = {"prior": prior, "lik": lik, "sessions": len(items), "per_cause": dict(n_cause)}
    return models


def fit() -> dict:
    """Refit from the database and apply on top of the knowledge brain. Cheap; runs at start and on each resolve."""
    models = fit_models(evidence(), config.LEARN_STRENGTH) if config.LEARNING else {}
    brain.set_learned(models)
    _last.clear()
    _last.update(fitted_at=db.now_iso(), sessions=sum(m["sessions"] for m in models.values()),
                 kinds=sorted(models), enabled=config.LEARNING, strength=config.LEARN_STRENGTH)
    if models:
        log.info("learned from %s resolved sessions across %s", _last["sessions"], ", ".join(_last["kinds"]))
    return dict(_last)


def report(kind: str | None = None) -> dict:
    """What the learning changed, per equipment type, for the Knowledge Base."""
    kinds = [kind] if kind else sorted(brain.TREES)
    out = []
    for k in kinds:
        tree, m = brain.TREES.get(k), brain.LEARNED.get(k)
        if not tree:
            continue
        n = len(tree["causes"])
        causes = [{"id": c["id"], "label": c["label"], "sessions": (m or {}).get("per_cause", {}).get(c["id"], 0),
                   "authored_share": round(1 / n, 3),
                   "learned_share": round((m["prior"][c["id"]] if m else 1.0) / n, 3)} for c in tree["causes"]]
        changes = []
        if m:
            label = {c["id"]: c["label"] for c in tree["causes"]}
            for q in tree["questions"]:
                for o in q["options"]:
                    for c, r in m["lik"].get(q["id"], {}).get(o["label"], {}).items():
                        if abs(math.log(r)) > 0.05:
                            a = o["lik"].get(c, 1.0)
                            changes.append({"check": q["text"], "answer": o["label"], "cause": label[c],
                                            "authored": round(a, 2), "learned": round(min(20, max(0.02, a * r)), 2)})
            changes.sort(key=lambda x: -abs(math.log(x["learned"] / x["authored"])))
        out.append({"kind": k, "sessions": (m or {}).get("sessions", 0), "causes": causes, "changes": changes[:12]})
    return {**_last, "kinds": out}
