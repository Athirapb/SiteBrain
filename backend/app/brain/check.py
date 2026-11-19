"""Quality gate for the knowledge brain.  Run:  python -m app.brain.check [Kind ...]

Structure: ids, 6M categories, likelihood keys, hazard flags, SCADA contradiction tags, why trees, texts.
Diagnosability: for every direct cause, simulate a technician whose answers match that cause (the option with the
strongest evidence for it) and check SiteBrain confirms it within the turn limit without confirming a wrong cause.
"""
import re
import sys

from .. import config, safety, telemetry
from . import CATEGORIES, CONDITIONS, MAINTENANCE, TREES, CASES, depth, roots, variants

MAX_LABEL = 60


def _tags(kind: str) -> set[str]:
    snap = telemetry.snapshot({"id": "x", "kind": kind, "name": "HP 1" if kind == "Compressor" else "x"})
    return {k for k, v in snap["tags"].items() if isinstance(v, list)}


def check_structure(kind: str, tree: dict) -> list[str]:
    err = []
    ids = [c["id"] for c in tree["causes"]]
    if len(set(ids)) != len(ids):
        err.append("duplicate cause ids")
    # the shared ones (common.py, process.py) and a type's own ones (variants.py) are not counted
    own = [c for c in tree["causes"] if c["id"][:2] not in ("e_", "o_") and c["id"] != "p_conn"]
    if not 3 <= len(own) <= 9:
        err.append(f"{len(own)} direct causes of its own (want 3–9)")
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
    from ..diagnosis import clear_leader, initial_posterior, pick_question, real_causes, update_posterior
    from .dsl import is_normal_answer

    hint = " ".join(cause["keys"]) if hinted else ""
    post = initial_posterior(tree, hint, [])
    asked: list[str] = []
    ids = [c["id"] for c in tree["causes"]]
    turn = 0
    while True:
        q = pick_question(tree, post, asked, hint)
        if not q:  # the engine's end of checks: the clear best fit, else "no fault found"
            best = clear_leader(post)
            if best:
                return best == cause["id"], turn, f"best fit {best} at {real_causes(post)[best]:.0%} after all checks"
            real = real_causes(post)
            top = max(real, key=real.get)
            return False, turn, f"no clear cause after all checks (best {top} at {real[top]:.0%})"
        turn += 1

        # a typical case: the check shows the abnormal reading this cause clearly predicts (multiplier ≥ 1.5), else
        # it reads healthy
        mult = [o["lik"].get(cause["id"], 1.0) for o in q["options"]]
        healthy = [i for i, o in enumerate(q["options"]) if is_normal_answer(o["label"])]
        pick = max(range(len(mult)), key=lambda i: mult[i])
        if mult[pick] < 1.5 and healthy:
            pick = max(healthy, key=lambda i: mult[i])
        post = update_posterior(post, q, [pick])
        asked.append(q["id"])
        real = real_causes(post)
        top = max(real, key=real.get)
        if real[top] >= config.CONFIDENCE_THRESHOLD:
            return top == cause["id"], turn, f"confirmed {top} at {real[top]:.0%}"


def check_normal_options(tree: dict) -> list[str]:
    """A "normal" reading must not count as evidence for a cause the check doesn't test: among the causes the
    check says nothing about (no option above 1.5), P(normal | cause) should be about the same."""
    from ..diagnosis import _answer_lik
    from .dsl import is_normal_answer

    warn = []
    ids = [c["id"] for c in tree["causes"]]
    for q in tree["questions"]:
        untested = [c for c in ids if max(o["lik"].get(c, 1.0) for o in q["options"]) < 1.5
                    and c[:2] not in ("e_", "o_", "p_", "v_")]  # these favour healthy machine readings on purpose
        if len(untested) < 2:
            continue
        for i, o in enumerate(q["options"]):
            if not is_normal_answer(o["label"]):
                continue
            ps = {c: _answer_lik(q, i, c) for c in untested}
            mid = sorted(ps.values())[len(ps) // 2]
            for c, p in ps.items():
                if p > mid * 1.2:
                    warn.append(f"question {q['id']}: {o['label']!r} favours untested cause {c} "
                                f"({p:.2f} vs {mid:.2f} typical)")
    return warn


def check_variants(kind: str) -> list[str]:
    """Each type of the kind: valid ids, its bias / drop / evidence refer to real causes and checks."""
    err = []
    base = TREES[kind]
    cause_ids = {c["id"] for c in base["causes"]}
    q_ids = {q["id"] for q in base["questions"]}
    vs = variants.variants(kind)
    if len({v["id"] for v in vs}) != len(vs):
        err.append("duplicate type ids")
    if len(vs) > 1 and not any(v["default"] for v in vs):
        err.append("no default type")
    for v in vs:
        p = f"type {v['id']}"
        if not v["look"] or not v["works"] or not v["normal"]:
            err.append(f"{p}: needs look, works and normal")
        own = {c["id"] for c in v["causes"]}
        if any(not c.startswith("v_") for c in own):
            err.append(f"{p}: its own cause ids must start with v_")
        bad = set(v["bias"]) - cause_ids
        if bad:
            err.append(f"{p}: bias for unknown causes {sorted(bad)}")
        bad = set(v["drop"]) - q_ids
        if bad:
            err.append(f"{p}: drops unknown checks {sorted(bad)}")
        for qid, _pat, lik in v["evidence"]:
            if qid not in q_ids or set(lik) - cause_ids - own:
                err.append(f"{p}: evidence on {qid} refers to unknown checks or causes")
    return err


def _report(name: str, kind: str, tree: dict, errs: list[str]) -> int:
    warns = check_normal_options(tree)
    sims = [(c["id"], *simulate(tree, c)) for c in tree["causes"]]
    bad = [s for s in sims if not s[1]]
    print(f"{name}: {len(tree['causes'])} causes, {len(tree['questions'])} checks, "
          f"{sum(len(roots(c['why'])) for c in tree['causes'] if c.get('why'))} root causes — "
          f"{'OK' if not errs and not bad else 'FAIL'}")
    for e in errs:
        print(f"   ✗ {e}")
    for w in warns:
        print(f"   ⚠ {w}")
    for cid, ok, turns, what in sims:
        print(f"   {'✓' if ok else '✗'} {cid:<10} {turns} turn(s): {what}")
    return len(errs) + len(bad)


def main(kinds: list[str]) -> int:
    failures = 0
    for kind in kinds or sorted(TREES):
        tree = TREES[kind]
        if "category" not in tree["causes"][0]:
            print(f"{kind}: legacy tree (not yet in the brain) — skipped")
            continue
        failures += _report(kind, kind, tree, check_structure(kind, tree) + check_variants(kind))
        for v in variants.variants(kind):
            if len(variants.variants(kind)) > 1 or v["causes"] or v["bias"] or v["drop"]:
                typed = variants.apply(tree, v)
                failures += _report(f"{kind} · {v['label']}", kind, typed, check_structure(kind, typed))
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
