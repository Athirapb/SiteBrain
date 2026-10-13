"""Seed the database: sites, users, areas and equipment (from the LLF checksheet workbook), KB, history.

Run `python -m app.seed --reset` to rebuild from scratch. The app seeds automatically on first start, and
rebuilds a database created by an older schema version. History older than today is synthetic
(deterministic random) so dashboards have trends to show.
"""
import json
import random
import secrets
import sys
from datetime import datetime, timedelta, timezone

from . import config, db, knowledge
from .catalog import SYMPTOMS, UNIT_NAMES, UNIT_ORDER, augment_with_process_assets, parse_checksheet
from .brain import tree_for

SITES = [
    ("GPS-BUU-04", "LLF Biogas Plant", "LLF-CBG-01", "Primary demo site"),
    ("GPS-BUU-02", "Demo Plant North", "DPN-CBG-02", "Fleet demo site"),
    ("GPS-BUU-07", "Demo Plant South", "DPS-CBG-07", "Fleet demo site"),
]

# Project register: (id, name, op_id, code); all created/updated 2026-01-08 10:43:51
PROJECTS = [
    (1, "IGRPL - Sirsa 01", 9, "IGRPL_PS_SIR_01"),
    (2, "IGRPL - Sitapur 01", 13, "IGRPL_PS_SIT_01"),
    (3, "IGRPL - Jind 01", 6, "IGRPL_PS_JIN_01"),
    (4, "IGRPL - Jaunpur 01", 7, "IGRPL_PS_JAU_01"),
    (5, "IGRPL - Lakhimpur Kheri 01", 11, "IGRPL_PS_LAK_01"),
    (6, "IGRPL - Kaithal 01", 8, "IGRPL_PS_KAI_01"),
    (7, "CSL_R&D_Project", 15, "CSL_R&D_Project"),
    (8, "Jio - Pilibhit 01", 4, "PS_PIL_01"),
    (9, "Jio - Jhajjar 02", None, "PS_JHA_02"),
    (10, "IGRPL - Yamunanagar 01", 14, "IGRPL_PS_YAM_01"),
    (11, "Jio - Suratgarh 01", None, "PS_SUR_01"),
    (12, "Jio - Jind 02", None, "PS_JIN_02"),
    (13, "Jio - Jind 01", None, "PS_JIN_01"),
    (14, "Jio - CHA 01", None, "PS_CHA_01"),
    (15, "Jio - HAI 01", None, "PS_HAI_01"),
    (16, "IGRPL_PS_VIJ_01", 12, "IGRPL_PS_VIJ_01"),
    (17, "IGRPL_PS_BEM_01", 10, "IGRPL_PS_BEM_01"),
]
PROJECTS_AT = "2026-01-08T10:43:51Z"

USERS = [
    ("Field Operator 1", "operator1", "field_operator", "Field Operator", "GPS-BUU-04"),
    ("Field Operator 2", "operator2", "field_operator", "Field Operator", "GPS-BUU-02"),
    ("Expert 1", "expert1", "expert", "Level-3 Process Engineer", None),
    ("Expert 2", "expert2", "expert", "Level-2 Maintenance Lead", None),
]

# Earlier demo users → current ones (control room and executive duties moved to the experts)
RENAMED_USERS = {"tech": "operator1", "tech2": "operator2", "expert": "expert1", "expert2": "expert2"}
RENAMED_NAMES = {"A. Nair": "Field Operator 1", "J. Paul": "Field Operator 2", "R. Iyer": "Expert 1",
                 "S. Menon": "Expert 2", "M. Das": "Expert 1", "K. Rao": "Expert 1", "A. Rao": "Expert 2"}

AREA_DESCRIPTIONS = {
    "BUU": "Gas train: H2S scrubber, filtration, blowers, LP/HP compressors, chiller, membranes",
    "HWG": "Hot water generation for digester heating",
    "SLS": "Decanters and screens separating digestate",
    "FEED": "Feed preparation, shredding and dosing",
    "CDT": "Centrate / process storage tanks and pumps",
}

SHIFT_START = {"A": 6, "B": 14, "C": 22}


def current_shift() -> tuple[str, datetime]:
    """The shift in progress now (A 06–14, B 14–22, C 22–06) and its local start time."""
    now = datetime.now().astimezone()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    starts = sorted(((sh, today - timedelta(days=d) + timedelta(hours=h))
                     for d in (0, 1) for sh, h in SHIFT_START.items()), key=lambda x: x[1])
    return [x for x in starts if x[1] <= now][-1]


def seed(reset: bool = False) -> None:
    version = db.schema_version()
    if reset or (version is not None and version != db.SCHEMA_VERSION):
        if not reset:
            print(f"Database schema v{version} is older than v{db.SCHEMA_VERSION}; rebuilding it …")
        db.drop_all()
    db.init_schema()
    seed_projects()
    if db.q1("SELECT code FROM sites LIMIT 1"):
        migrate_users()
        return
    random.seed(42)
    print("Seeding SiteBrain database …")

    for code, name, proj, loc in SITES:
        db.insert("sites", {"code": code, "name": name, "project_code": proj, "location": loc, "commissioned": "2025-03-01"})
    for name, uname, role, title, site in USERS:
        db.insert("users", {"name": name, "username": uname, "role": role, "title": title, "site_code": site,
                            "token": secrets.token_hex(16)})

    catalog = augment_with_process_assets(parse_checksheet(config.CHECKSHEET_XLSX))
    print(f"  parsed {len(catalog)} equipment from {config.CHECKSHEET_XLSX.name}")
    units = sorted({(it["unit"], it["unit_name"]) for it in catalog},
                   key=lambda u: (UNIT_ORDER.index(u[0]) if u[0] in UNIT_ORDER else 99, u[0]))
    equipment: dict[str, list[dict]] = {}
    areas: dict[str, dict[str, dict]] = {}
    now = db.now_iso()
    for code, *_ in SITES:
        areas[code] = {}
        for order, (unit, unit_name) in enumerate(units, 1):
            row = {"site_code": code, "code": unit, "name": UNIT_NAMES.get(unit, unit_name),
                   "description": AREA_DESCRIPTIONS.get(unit), "sort_order": order}
            row["id"] = db.insert("areas", row)
            areas[code][unit] = row
        equipment[code] = []
        for it in catalog:
            area = areas[code][it["unit"]]
            eq = {"id": f"{code}|{it['unit']}|{it['name']}", "site_code": code, "area_id": area["id"],
                  "name": it["name"], "kind": it["kind"], "tag": it.get("tag"), "created_at": now}
            db.insert("equipment", eq)
            equipment[code].append({**eq, "unit": it["unit"], "unit_name": area["name"]})
    print(f"  {sum(len(a) for a in areas.values())} areas, {sum(len(e) for e in equipment.values())} equipment")

    _seed_history(equipment, areas)
    res = knowledge.train()
    print(f"  knowledge brain: {res['cases']} cases, {res['documents']} documents, {res['root_causes']} root causes")
    db.set_counter("schema_version", db.SCHEMA_VERSION)
    db.audit("system", "engine", "seed.completed", None, {"equipment": sum(len(v) for v in equipment.values())})
    print("  done.")


def seed_projects() -> None:
    """Add any project in PROJECTS that the database does not have yet (runs on every start)."""
    db.executemany("INSERT INTO projects (id, name, op_id, code, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?) "
                   "ON CONFLICT DO NOTHING", [(*p, PROJECTS_AT, PROJECTS_AT) for p in PROJECTS])


def migrate_users() -> None:
    """Bring a database seeded with the earlier six demo users (four roles) to the two-role model. Idempotent.

    Users are renamed in place (ids, tokens and history links survive), the control-room operator and executive
    accounts are removed, and their names in session, chat, escalation and safety records are updated. The audit
    log is append-only by design and keeps the names it was written with.
    """
    if not db.q1("SELECT id FROM users WHERE role IN ('technician', 'operator', 'executive') LIMIT 1"):
        return
    print("Migrating demo users to the field operator / expert roles …")
    by_username = {u[1]: u for u in USERS}
    for old, new in RENAMED_USERS.items():
        name, uname, role, title, site = by_username[new]
        db.ex("UPDATE users SET name=?, username=?, role=?, title=?, site_code=? WHERE username=?",
              (name, uname, role, title, site, old))
    db.ex("DELETE FROM users WHERE role IN ('technician', 'operator', 'executive')")
    for name, uname, role, title, site in USERS:  # any of the current users that did not exist before
        if not db.q1("SELECT id FROM users WHERE username=?", (uname,)):
            db.insert("users", {"name": name, "username": uname, "role": role, "title": title, "site_code": site,
                                "token": secrets.token_hex(16)})
    text_cols = [("sessions", "report", True), ("sessions", "state", True), ("messages", "payload", True),
                 ("escalations", "payload", True), ("escalations", "expert_name", False),
                 ("escalations", "summary", False), ("interlocks", "acknowledged_by", False),
                 ("interlocks", "released_by", False), ("overrides", "requested_by", False),
                 ("overrides", "decided_by", False), ("outbox", "body", False)]
    for old, new in RENAMED_NAMES.items():
        for table, col, is_json in text_cols:
            cast = "::jsonb" if is_json else ""
            db.ex(f"UPDATE {table} SET {col} = replace({col}::text, ?, ?){cast} WHERE {col}::text LIKE ?",
                  (old, new, f"%{old}%"))


def _symptoms_for(cause: dict) -> list[str]:
    """Report symptoms a technician would plausibly pick for a historical cause."""
    keys = " ".join(cause["keys"])
    picked = [sy["id"] for sy in SYMPTOMS if any(k in keys for k in sy["keys"])]
    return picked[:2] or ["noise"]


def _seed_history(equipment: dict, areas: dict) -> None:
    """Synthetic closed sessions over ~180 days so weekly/monthly analytics have trends."""
    rng = random.Random(7)
    now = datetime.now(timezone.utc)
    experts = [("Expert 1", "Level-3 Process Engineer"), ("Expert 2", "Level-2 Maintenance Lead")]
    weights = {"Agitator": 5, "Pump": 6, "Compressor": 3, "Blower": 2, "Decanter": 2, "WAM": 1.5, "Shredder": 1.5,
               "HWG": 1, "Chiller": 1, "Scrubber": 1.2, "Filter": 0.8, "Membrane": 0.8, "Machine": 0.5}
    sid_n, esc_n = 1000, 0
    sess_rows, msg_rows, esc_rows, il_rows = [], [], [], []
    for code, eqs in equipment.items():
        pool = [e for e in eqs]
        wts = [weights.get(e["kind"], 1) for e in pool]
        for day in range(180, 0, -1):
            # FCR improves over time: escalation probability falls from ~32% to ~12%
            p_esc = 0.32 - 0.20 * (180 - day) / 180
            for _ in range(rng.choice([0, 1, 1, 2, 2, 3])):
                eq = rng.choices(pool, wts)[0]
                tree = tree_for(eq["kind"])
                cause = rng.choice(tree["causes"])
                start = now - timedelta(days=day, hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
                sev = rng.choices(["Low", "Medium", "High", "Critical"], [1, 5, 3, 1.2])[0]
                escalated = rng.random() < p_esc
                ident = start + timedelta(minutes=rng.randint(4, 18) + (rng.randint(20, 90) if escalated else 0))
                res = ident + timedelta(minutes=rng.randint(10, 60) * (4 if escalated else 1))
                sid_n += 1
                sid = f"S-{sid_n}"
                sy = _symptoms_for(cause)
                labels = [x["label"] for x in SYMPTOMS if x["id"] in sy]
                symptom = ", ".join(labels)
                iso = lambda d: d.replace(microsecond=0).isoformat().replace("+00:00", "Z")
                report = {"symptoms": sy, "symptom_labels": labels, "severity": sev, "description": "",
                          "reported_by": "Field Operator 1" if code == "GPS-BUU-04" else "Field Operator 2", "reported_at": iso(start)}
                sess_rows.append((sid, code, eq["area_id"], eq["id"], json.dumps(report), "resolved",
                                  "expert" if escalated else "bot", "rules",
                                  rng.randint(5, 7) if escalated else rng.randint(2, 4), round(rng.uniform(0.86, 0.97), 2),
                                  json.dumps([{"label": cause["label"], "likelihood": 0.9}]), json.dumps([]), json.dumps({}),
                                  1, symptom, cause["label"], json.dumps(cause["steps"]),
                                  "Expert" if escalated else "SiteBrain", sev, 0, iso(start), iso(ident), iso(res)))
                msg_rows += [
                    (sid, "report", json.dumps({"text": symptom, "symptoms": labels, "severity": sev, "description": "",
                                                "author": report["reported_by"], "area": eq["unit_name"],
                                                "equipment": eq["name"]}), iso(start)),
                    (sid, "solution", json.dumps({"who": experts[0][0] if escalated else "SiteBrain", "expert": escalated,
                                                  "root_cause": cause["label"], "steps": cause["steps"],
                                                  "basis": "expert assessment" if escalated else "decision tree"}), iso(ident)),
                    (sid, "event", json.dumps({"text": "Session resolved", "icon": "check-circle-outline", "tone": "ok"}), iso(res)),
                ]
                if escalated:
                    esc_n += 1
                    ex = rng.choice(experts)
                    esc_at = start + timedelta(minutes=rng.randint(8, 20))
                    esc_rows.append((f"ESC-{eq['unit']}-{esc_n}", sid, code, eq["area_id"], eq["id"],
                                     "Critical" if sev == "Critical" else rng.choice(["High", "Medium"]),
                                     f"{symptom}. Leading hypothesis: {cause['label']}.",
                                     "5 diagnostic turns without root-cause confidence >85%", ex[0], ex[1], None, "Resolved",
                                     5, json.dumps({}), rng.randint(180, 2400), iso(esc_at),
                                     iso(esc_at + timedelta(minutes=rng.randint(3, 15))), iso(res)))
                if sev in ("High", "Critical") and rng.random() < 0.45:
                    rule = {"Compressor": "CMP-01", "Scrubber": "SCR-01", "Filter": "FLT-01", "Chiller": "CHL-01",
                            "Membrane": "MEM-01"}.get(eq["kind"], "ROT-01")
                    il_rows.append((code, eq["area_id"], eq["id"], sid, rule, "interlock", "Historical interlock", symptom,
                                    "CRITICAL" if sev == "Critical" else "HIGH", "released", "Field Operator 1", iso(start), "Expert 1",
                                    iso(res), 1, iso(start)))
    db.executemany("INSERT INTO sessions (id, site_code, area_id, equipment_id, report, status, mode, engine, turns, "
                  "confidence, causes, cited, state, identified, symptom, root_cause, steps, resolved_by, severity, "
                  "pending_signoff, created_at, identified_at, resolved_at) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", sess_rows)
    db.executemany("INSERT INTO messages (session_id, type, payload, created_at) VALUES (?,?,?,?)", msg_rows)
    db.executemany("INSERT INTO escalations (ticket, session_id, site_code, area_id, equipment_id, urgency, summary, "
                  "trigger_reason, expert_name, expert_role, claimed_by, status, turns, payload, compile_ms, created_at, "
                  "first_response_at, resolved_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", esc_rows)
    db.executemany("INSERT INTO interlocks (site_code, area_id, equipment_id, session_id, rule_id, category, action, reason, "
                  "severity, status, acknowledged_by, acknowledged_at, released_by, released_at, prevented_damage, created_at) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", il_rows)
    db.set_counter("session", 2424)
    open_ticket = f"ESC-BUU-{esc_n + 1}"
    db.set_counter("ticket", esc_n + 1)
    print(f"  {len(sess_rows)} historical sessions, {len(esc_rows)} escalations, {len(il_rows)} interlock events")

    # An open escalation in progress for the expert queue
    hp2 = next(e for e in equipment["GPS-BUU-04"] if e["name"] == "HP 2")
    t0 = now - timedelta(hours=2)
    iso = lambda d: d.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    report = {"symptoms": ["noise"], "symptom_labels": ["Abnormal noise"], "severity": "High",
              "description": "Clatter at the valve covers after valve plate replacement, worse at full load",
              "reported_by": "Field Operator 1", "reported_at": iso(t0)}
    db.insert("sessions", {"id": "S-2419", "site_code": "GPS-BUU-04", "area_id": hp2["area_id"], "equipment_id": hp2["id"],
                           "report": report, "status": "escalated",
                           "mode": "expert", "engine": "rules", "turns": 5, "confidence": 0.46,
                           "causes": [{"id": "valve", "label": "Suction / discharge valve plate failure", "likelihood": 0.46},
                                      {"id": "oilleak", "label": "Crankcase oil leak leading to bearing oil starvation", "likelihood": 0.31}],
                           "cited": [], "state": {"posterior": {"oilleak": 0.31, "valve": 0.46, "particle": 0.15, "gasket": 0.08},
                                                  "asked": ["knock", "oil", "valvetemp"], "pending": None, "answers": [],
                                                  "flags": ["rotating_abnormal"], "excluded": [], "expert_turns": 0,
                                                  "phase": "diagnose", "loc": None},
                           "identified": 0, "symptom": "Abnormal noise: clatter at the valve covers after valve plate replacement",
                           "severity": "High", "pending_signoff": 0, "created_at": iso(t0)})
    for typ, p in [
        ("report", {"text": "Abnormal noise: clatter at the valve covers after valve plate replacement, worse at full load",
                    "symptoms": ["Abnormal noise"], "severity": "High", "description": report["description"],
                    "author": "Field Operator 1", "area": "Biogas Upgradation Unit", "equipment": "HP 2"}),
        ("analysis", {"text": "Abnormal noise reported on HP 2 (Biogas Upgradation Unit), severity High. A few field "
                              "checks will confirm the cause before I recommend a fix.", "safety_rules": [], "footnote": ""}),
        ("agent", {"who": "SiteBrain", "text": "Feel/IR the suction valve covers. Is one valve noticeably hotter than the others?"}),
        ("user", {"text": "Uniform temperature", "author": "Field Operator 1"}),
        ("event", {"text": f"Auto-escalated {open_ticket} · 5 diagnostic turns without root-cause confidence >85% (best 46%)",
                   "icon": "account-arrow-up-outline", "tone": "warn"}),
        ("agent", {"who": "Expert 2 · Technical Expert", "expert": True,
                   "text": "Valve temps uniform rules out a single broken plate. Check piston ring blow-by at the crankcase breather — any oil mist?"}),
    ]:
        db.insert("messages", {"session_id": "S-2419", "type": typ, "payload": p, "created_at": iso(t0)})
    db.insert("escalations", {"ticket": open_ticket, "session_id": "S-2419", "site_code": "GPS-BUU-04",
                              "area_id": hp2["area_id"], "equipment_id": hp2["id"], "urgency": "High",
                              "summary": "Abnormal noise after valve plate replacement. Leading hypothesis: piston ring wear.",
                              "trigger_reason": "5 diagnostic turns without root-cause confidence >85% (best 46%)",
                              "expert_name": "Expert 2", "expert_role": "Level-2 Maintenance Lead", "status": "In Progress",
                              "turns": 5, "payload": {}, "compile_ms": 412, "created_at": iso(t0 + timedelta(minutes=9)),
                              "first_response_at": iso(t0 + timedelta(minutes=15))})


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
