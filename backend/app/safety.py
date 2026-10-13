"""Deterministic safety interlock matrix (SRS §5).

Safety decisions never come from the LLM. Hazards are raised as flags from two sources: the field operator's
issue report (report_flags) and the answers given during guided diagnosis (decision-tree option flags).
INTERLOCK rules are recorded for the control room (release and bypass overrides happen there); ADVISORY rules
show a warning banner. Neither holds up the troubleshooting chat.
"""
import re

from . import db
from .catalog import ROTATING

# Hazard flags the engine understands (decision-tree options and the LLM may raise these)
HAZARD_FLAGS = ["particles", "channeling", "gas_leak", "rotating_critical", "rotating_abnormal", "water_carryover",
                "h2s_breakthrough", "bypass_open", "guard_inactive", "offspec_gas", "low_oil", "seal_leak", "belt_wear"]

_GAS_TEXT = re.compile(r"gas\s*(smell|leak)|smell\w*\s+(of\s+)?(gas|h2s|rotten)|\blel\b|leak\w*\s+gas", re.I)


def report_flags(report: dict, kind: str | None) -> set[str]:
    """Hazards implied by the issue report itself, before any field check is answered."""
    sy = set(report.get("symptoms") or [])
    sev = report.get("severity") or "Medium"
    text = report.get("description") or ""
    flags: set[str] = set()
    if "gas" in sy or _GAS_TEXT.search(text):
        flags.add("gas_leak")
    rotating = kind in ROTATING
    if rotating and sy & {"noise", "vibration"}:
        flags.add("rotating_critical" if sev == "Critical" else "rotating_abnormal")
    if kind == "Pump" and "leak" in sy and sev in ("High", "Critical"):
        flags.add("seal_leak")
    if kind == "HWG" and "belt" in sy:
        flags.add("belt_wear")
    if kind == "Compressor" and "lube" in sy:
        flags.add("low_oil")
    if kind == "Membrane" and "quality" in sy:
        flags.add("offspec_gas")
    if kind == "Scrubber" and "quality" in sy:
        flags.add("h2s_breakthrough")
    return flags


def _rule(rule_id, category, sev, action, reason, target=None, prevents=False):
    return {"rule_id": rule_id, "category": category, "severity": sev, "action": action, "reason": reason,
            "target": target, "prevents_damage": prevents}


def evaluate(kind: str | None, name: str, flags: set[str] | list[str] | None) -> list[dict]:
    """Rules triggered by the hazard flags on an equipment (kind None = area-level, not yet localized)."""
    f = set(flags or [])
    out: list[dict] = []

    if kind == "Scrubber" and "channeling" in f:
        out.append(_rule("SCR-01", "interlock", "CRITICAL",
                         "Lock downstream filter bypass valve in the CLOSED position",
                         "Top distributor mesh failure / bed channeling on H2S scrubber", "Gas Filtration Skid", True))
    if kind in ("Scrubber", "Filter") and "particles" in f:
        out.append(_rule("CMP-01", "interlock", "CRITICAL",
                         "Trip LP compressor load line — solid particle ingress risk upstream",
                         "Media carryover / element rupture toward compressor suction", "LP compressors", True))
    if kind == "Scrubber" and "h2s_breakthrough" in f:
        out.append(_rule("SCR-02", "advisory", "HIGH",
                         "Wear H2S personal monitor; confirm sulfur breakthrough with downstream sample",
                         "Downstream H2S breakthrough suspected"))

    if kind == "Filter" and "bypass_open" in f:
        if "guard_inactive" in f:
            out.append(_rule("FLT-01", "interlock", "CRITICAL",
                             "Invalidate bypass execution — secondary guard filter is not active",
                             "Filter bypass open without secondary guard", "Gas Filtration Skid", True))
        else:
            out.append(_rule("FLT-02", "advisory", "HIGH",
                             "Bypass permitted only while secondary guard filter stays active; log the bypass window",
                             "Filter bypass found open"))

    if kind == "Chiller" and "water_carryover" in f:
        out.append(_rule("CHL-01", "interlock", "CRITICAL",
                         "Halt feed to separation membranes until dew point is back within 2–5°C",
                         "Dew point / water carryover above limit", "Membrane Upgrader", True))

    if kind == "Membrane" and "offspec_gas" in f:
        out.append(_rule("MEM-01", "interlock", "HIGH",
                         "Divert off-spec gas to flare / recycle loop; block pipeline injection",
                         "Methane purity below specification", "CBG Pipeline", True))

    if "gas_leak" in f:
        out.append(_rule("GAS-01", "interlock", "CRITICAL",
                         "Isolate the unit, ventilate, confirm with a portable gas detector. No hot work or ignition sources",
                         "Gas leak reported", name))

    if kind in ROTATING and "rotating_critical" in f:
        out.append(_rule("ROT-01", "interlock", "CRITICAL",
                         "Stop the equipment and apply LOTO before inspecting Critical vibration or abnormal sound",
                         "Critical vibration / abnormal sound on rotating equipment", name, True))

    if kind == "Compressor" and "low_oil" in f:
        out.append(_rule("OIL-01", "interlock", "HIGH",
                         "Startup blocked — do not restart the compressor until oil is topped up to 60–80%",
                         "Compressor oil level low", name, True))

    if kind == "Pump" and "seal_leak" in f:
        out.append(_rule("SEAL-01", "advisory", "HIGH",
                         "Isolate suction and discharge valves and drain the casing before seal or gland work",
                         "Seal / gland leakage"))
    if kind == "HWG" and "belt_wear" in f:
        out.append(_rule("BELT-01", "advisory", "HIGH",
                         "Stop the ID fan and apply LOTO. Never adjust a running belt", "ID fan belt wear"))
    if kind in ROTATING and "rotating_abnormal" in f and not any(r["rule_id"] == "ROT-01" for r in out):
        out.append(_rule("ROT-02", "advisory", "MEDIUM",
                         "Keep clear of rotating parts; trend vibration each hour and stop at Critical",
                         "Abnormal vibration / sound"))
    # de-duplicate by rule id
    seen, uniq = set(), []
    for r in out:
        if r["rule_id"] not in seen:
            seen.add(r["rule_id"])
            uniq.append(r)
    return uniq


def engage(site_code: str, area_id: int, eq: dict | None, rules: list[dict], session_id: str | None,
           actor: str = "SiteBrain") -> list[dict]:
    """Persist triggered interlocks (idempotent per equipment — or area, when not localized — and rule)."""
    engaged = []
    for r in rules:
        if eq:
            existing = db.q1("SELECT * FROM interlocks WHERE equipment_id=? AND rule_id=? AND status!='released'",
                             (eq["id"], r["rule_id"]))
        else:
            existing = db.q1("SELECT * FROM interlocks WHERE area_id=? AND equipment_id IS NULL AND rule_id=? "
                             "AND status!='released'", (area_id, r["rule_id"]))
        if existing:
            if session_id and not existing["session_id"]:
                db.update("interlocks", "id", existing["id"], {"session_id": session_id})
            engaged.append({**existing, **r, "id": existing["id"], "status": existing["status"]})
            continue
        row = {
            "site_code": site_code, "area_id": area_id, "equipment_id": eq["id"] if eq else None,
            "target_equipment_id": r.get("target"),
            "session_id": session_id, "rule_id": r["rule_id"], "category": r["category"], "action": r["action"],
            "reason": r["reason"], "severity": r["severity"],
            "status": "engaged" if r["category"] == "interlock" else "acknowledged",
            "prevented_damage": 1 if r.get("prevents_damage") else 0, "created_at": db.now_iso(),
        }
        row["id"] = db.insert("interlocks", row)
        db.audit(actor, "engine", "interlock.engaged" if r["category"] == "interlock" else "advisory.raised",
                 f"interlock:{row['id']}", {"rule": r["rule_id"], "equipment": row["equipment_id"], "area": area_id,
                                            "action": r["action"]}, site_code)
        engaged.append({**row, **r})
    return engaged


def bypass_guard_active(site_code: str) -> bool:
    """Is the secondary guard filter in service? It is, unless diagnosis found it inactive (open FLT-01)."""
    if not db.q1("SELECT id FROM equipment WHERE site_code=? AND kind='Filter' AND active", (site_code,)):
        return False
    return not db.q1("SELECT id FROM interlocks WHERE site_code=? AND rule_id='FLT-01' AND status!='released'",
                     (site_code,))


# Rules whose override would open a bypass path to downstream rotating machinery
BYPASS_RULES = {"SCR-01", "FLT-01", "CMP-01"}
NON_OVERRIDABLE = {"GAS-01", "ROT-01"}
