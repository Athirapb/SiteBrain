"""The SiteBrain knowledge brain: what the copilot knows about each equipment type and plant area.

  TREES        fishbone of direct causes + field checks + 5-Why trees, per equipment type (see dsl.py)
  MAINTENANCE  general maintenance knowledge per equipment type (PM tasks, failure modes, operating limits)
  CONDITIONS   normal operating conditions per plant area (what "good" looks like, why it matters, what to do)
  CASES        RCA case library from previous problems (seeded into the knowledge base)

Each group module (pumps.py, agitation.py, …) contributes to these; `python -m app.brain.check` validates them.
Incident reports and SOP / OEM documents live in data/docs and are indexed by knowledge.train().
"""
import copy
import importlib

from .dsl import CATEGORIES, CATEGORY_LABEL, depth, roots  # noqa: F401

GROUPS = ["pumps", "agitation", "feeding", "separation", "gas_movers", "hwg", "gas_cleaning"]

TREES: dict[str, dict] = {}
MAINTENANCE: dict[str, dict] = {}
CONDITIONS: list[dict] = []
CASES: list[dict] = []

for _name in GROUPS:
    try:
        _m = importlib.import_module(f"{__name__}.{_name}")
    except ModuleNotFoundError as e:
        if e.name != f"{__name__}.{_name}":
            raise
        continue
    TREES.update(getattr(_m, "TREES", {}))
    MAINTENANCE.update(getattr(_m, "MAINTENANCE", {}))
    CONDITIONS.extend(getattr(_m, "CONDITIONS", []))
    CASES.extend(getattr(_m, "CASES", []))

# Electrical and operational causes and checks shared by every equipment type (common.py), then the process causes:
# the process around the machine, and what it handles (process.py)
from . import common, process, variants  # noqa: E402

common.extend(TREES)
process.extend(TREES)


# Adjustments learned from resolved sessions (app/learning.py); authored TREES are never modified.
LEARNED: dict[str, dict] = {}
_EFFECTIVE: dict[str, dict] = {}


_TYPED: dict[tuple, dict] = {}


def set_learned(models: dict[str, dict]) -> None:
    LEARNED.clear()
    LEARNED.update(models)
    _EFFECTIVE.clear()
    _TYPED.clear()


def _apply(tree: dict, m: dict) -> dict:
    t = copy.deepcopy(tree)
    for c in t["causes"]:
        c["prior"] = c.get("prior", 1.0) * m["prior"].get(c["id"], 1.0)
    for q in t["questions"]:
        for o in q["options"]:
            for cid, r in m["lik"].get(q["id"], {}).get(o["label"], {}).items():
                o["lik"][cid] = min(20.0, max(0.02, o["lik"].get(cid, 1.0) * r))
    t["learned_from"] = m["sessions"]
    return t


def _learned(k: str) -> dict:
    if k not in LEARNED:
        return TREES[k]
    if k not in _EFFECTIVE:
        _EFFECTIVE[k] = _apply(TREES[k], LEARNED[k])
    return _EFFECTIVE[k]


def tree_for(kind: str | None, variant: str | None = None) -> dict:
    """The tree the engine uses: authored knowledge, plus what resolved sessions taught it, shaped to the
    equipment's type (variants.py) when it is known."""
    k = kind if kind in TREES else "Machine"
    v = variants.get(k, variant)
    if not v:
        return _learned(k)
    if (k, v["id"]) not in _TYPED:
        _TYPED[(k, v["id"])] = variants.apply(_learned(k), v)
    return _TYPED[(k, v["id"])]


def conditions_for(area_code: str | None) -> list[dict]:
    return [c for c in CONDITIONS if area_code and area_code in c["areas"]]


def find_cause(tree: dict, cause_id: str) -> dict | None:
    cause_id = (tree.get("aliases") or {}).get(cause_id, cause_id)  # a cause split up since the session began
    return next((c for c in tree["causes"] if c["id"] == cause_id), None)
