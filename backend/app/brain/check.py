"""Quality gate for the knowledge brain.  Run:  python -m app.brain.check [Kind ...]

Structure: ids, 6M categories, likelihood keys, hazard flags, SCADA contradiction tags, why trees, texts.
Diagnosability: for every direct cause, simulate a technician whose answers match that cause (the option with the
strongest evidence for it) and check SiteBrain confirms it within the turn limit without confirming a wrong cause.
"""
import sys

from .. import config, safety, telemetry
from . import CATEGORIES, CONDITIONS, MAINTENANCE, TREES, CASES, depth, roots

MAX_LABEL = 60


def _tags(kind: str) -> set[str]:
    snap = telemetry.snapshot({"id": "x", "kind": kind, "name": "HP 1" if kind == "Compressor" else "x"})
    return {k for k, v in snap["tags"].items() if isinstance(v, list)}


def check_structure(kind: str, tree: dict) -> list[str]:
    err = []
    ids = [c["id"] for c in tree["causes"]]
    if len(set(ids)) != len(ids):
        err.append("duplicate cause ids")
    if not 3 <= len(ids) <= 9:
        err.append(f"{len(ids)} direct causes (want 3–9)")
    qids = [q["id"] for q in tree["questions"]]
    if len(set(qids)) != len(qids):
        err.append("duplicate question ids")
    tags = _tags(kind)
    for c in tree["causes"]:
        p = f"cause {c['id']}"
        if c.get("category") not in CATEGORIES:
            err.append(f"{p}: category {c.get('category')!r} not in {CATEGORIES}")
        if not c.get("steps"):
            err.append(f"{p}: no corrective steps")
        if any(k != k.lower() for k in c["keys"]):
            err.append(f"{p}: keys must be lowercase")
        w = c.get("why")
        if not w:
            err.append(f"{p}: no why tree")
            continue
        if depth(w) > 4:
            err.append(f"{p}: why tree deeper than 4")
        if len(roots(w)) < 2:
            err.append(f"{p}: why tree needs at least 2 root causes")
        for r in roots(w):
            if r["category"] not in CATEGORIES:
                err.append(f"{p}: root {r['label']!r} has category {r['category']!r}")
            if not r["prevent"]:
                err.append(f"{p}: root {r['label']!r} has no preventive action")
        stack = [w]
        while stack:
            n = stack.pop()
            if n["type"] != "why":
                continue
            labels = [b["label"] for b in n["branches"]]
            if len(labels) < 2 or len(set(l.lower() for l in labels)) != len(labels):
                err.append(f"{p}: why {n['text']!r} needs ≥2 distinct branches")
            err += [f"{p}: branch label too long: {l!r}" for l in labels if len(l) > MAX_LABEL]
            stack += [b["then"] for b in n["branches"]]
    for q in tree["questions"]:
        p = f"question {q['id']}"
        if not q.get("how") or not q.get("purpose"):
            err.append(f"{p}: needs both how= and purpose=")
        labels = [o["label"] for o in q["options"]]
        if len(labels) < 2 or len(set(l.lower() for l in labels)) != len(labels):
            err.append(f"{p}: needs ≥2 distinct options")
        for o in q["options"]:
            if len(o["label"]) > MAX_LABEL:
                err.append(f"{p}: option label too long: {o['label']!r}")
            bad = set(o["lik"]) - set(ids)
            if bad:
                err.append(f"{p}: option {o['label']!r} refers to unknown causes {sorted(bad)}")
            if any(v <= 0 for v in o["lik"].values()):
                err.append(f"{p}: likelihoods must be > 0")
            badf = set(o["flags"]) - set(safety.HAZARD_FLAGS)
            if badf:
                err.append(f"{p}: unknown hazard flags {sorted(badf)} (allowed: {safety.HAZARD_FLAGS})")
        con = q.get("contradiction")
        if con:
            if con["tag"] not in tags:
                err.append(f"{p}: contradiction tag {con['tag']!r} not simulated for {kind} (have {sorted(tags)})")
            if not 0 <= con["option"] < len(q["options"]) or not ({"above", "below"} & set(con)):
                err.append(f"{p}: contradiction needs a valid option index and above/below")
    if kind not in MAINTENANCE:
        err.append("no MAINTENANCE entry")
    return err


def simulate(tree: dict, cause: dict, hinted: bool = True) -> tuple[bool, int, str]:
    """(confirmed correctly, turns used, what happened)."""
    from ..diagnosis import _norm, initial_posterior, pick_question

    hint = " ".join(cause["keys"]) if hinted else ""
    post = initial_posterior(tree, hint, [])
    asked: list[str] = []
    ids = [c["id"] for c in tree["causes"]]
    for turn in range(1, config.MAX_DIAGNOSTIC_TURNS + 1):
        q = pick_question(tree, post, asked, hint)
        if not q:
            return False, turn - 1, "ran out of questions"

        def strength(o):
            others = [o["lik"].get(x, 1.0) for x in ids if x != cause["id"]]
            return o["lik"].get(cause["id"], 1.0) / (sum(others) / len(others))
        opt = max(q["options"], key=strength)
        post = _norm({c: post[c] * opt["lik"].get(c, 1.0) for c in post})
        asked.append(q["id"])
        top = max(post, key=post.get)
        if post[top] >= config.CONFIDENCE_THRESHOLD:
            return top == cause["id"], turn, f"confirmed {top} at {post[top]:.0%}"
    top = max(post, key=post.get)
    return False, config.MAX_DIAGNOSTIC_TURNS, f"best {top} at {post[top]:.0%} after {config.MAX_DIAGNOSTIC_TURNS} turns"


def main(kinds: list[str]) -> int:
    failures = 0
    for kind in kinds or sorted(TREES):
        tree = TREES[kind]
        if "category" not in tree["causes"][0]:
            print(f"{kind}: legacy tree (not yet in the brain) — skipped")
            continue
        errs = check_structure(kind, tree)
        sims = [(c["id"], *simulate(tree, c)) for c in tree["causes"]]
        bad = [s for s in sims if not s[1]]
        failures += len(errs) + len(bad)
        print(f"{kind}: {len(tree['causes'])} causes, {len(tree['questions'])} checks, "
              f"{sum(len(roots(c['why'])) for c in tree['causes'] if c.get('why'))} root causes — "
              f"{'OK' if not errs and not bad else 'FAIL'}")
        for e in errs:
            print(f"   ✗ {e}")
        for cid, ok, turns, what in sims:
            print(f"   {'✓' if ok else '✗'} {cid:<10} {turns} turn(s): {what}")
    print(f"\n{len(CASES)} RCA cases · {len(CONDITIONS)} operating-condition profiles · "
          f"{len(MAINTENANCE)} maintenance entries")
    ids = [c["id"] for c in CASES]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        print(f"✗ duplicate case ids: {sorted(dup)}")
        failures += 1
    for p in CONDITIONS:
        if not ({"id", "title", "areas", "params"} <= set(p)) or not p["params"]:
            print(f"✗ condition profile {p.get('id')} incomplete")
            failures += 1
        if not isinstance(p.get("notes", []), list) or any(len(x) != 4 for x in p.get("params", [])):
            print(f"✗ condition profile {p.get('id')}: notes must be a list and params 4-tuples")
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
