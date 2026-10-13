"""Operational analytics (SRS §7): daily operations, weekly reliability, monthly executive summary."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from . import db

SUBSYSTEM = {
    "Scrubber": "H2S Scrubbers", "Filter": "Gas Filtration", "Compressor": "Compressors", "Blower": "Blowers",
    "Chiller": "Chillers", "Membrane": "Membranes", "Agitator": "Agitators", "Pump": "Pumps",
    "Decanter": "Decanters", "WAM": "Screens (WAM)", "Shredder": "Shredders", "HWG": "HWG", "Machine": "Other machines",
    "Unlocalized": "Area-level (equipment not identified)",
}
SHIFT_OF_HOUR = [("C", 0), ("A", 6), ("B", 14), ("C", 22)]  # local shift start hours


def _ts(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _since(days: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _site_clause(site: str | None, col: str = "site_code") -> tuple[str, list]:
    return (f" AND {col}=?", [site]) if site else ("", [])


def _minutes(a: str | None, b: str | None) -> float | None:
    ta, tb = _ts(a), _ts(b)
    if not ta or not tb:
        return None
    return max(0.0, (tb - ta).total_seconds() / 60)


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 1) if xs else None


def _sessions(site, days):
    sc, sp = _site_clause(site, "s.site_code")
    return db.q(f"SELECT s.*, COALESCE(e.kind, 'Unlocalized') AS kind, COALESCE(e.name, a.name) AS eq_name, "
                f"a.name AS unit_name FROM sessions s JOIN areas a ON a.id=s.area_id "
                f"LEFT JOIN equipment e ON e.id=s.equipment_id WHERE s.created_at>=?{sc} ORDER BY s.created_at",
                [_since(days)] + sp)


def _shift(iso: str) -> str:
    h = _ts(iso).astimezone().hour
    return [sh for sh, start in SHIFT_OF_HOUR if h >= start][-1]


def daily(site: str | None) -> dict:
    sess = _sessions(site, 1)
    sc, sp = _site_clause(site)
    open_sess = db.q(f"SELECT severity, COUNT(*) n FROM sessions WHERE status IN ('active','escalated'){sc} GROUP BY severity", sp)
    matrix = {k: 0 for k in ("Low", "Medium", "High", "Critical")}
    for r in open_sess:
        matrix[r["severity"]] = r["n"]

    # Equipment health from open issues: Critical / Abnormal = an open Critical / other issue on the equipment
    total_eq = db.q1(f"SELECT COUNT(*) n FROM equipment WHERE active{sc}", sp)["n"]
    worst: dict[str, str] = {}
    for r in db.q(f"SELECT equipment_id, severity FROM sessions WHERE status IN ('active','escalated') "
                  f"AND equipment_id IS NOT NULL{sc}", sp):
        if worst.get(r["equipment_id"]) != "Critical":
            worst[r["equipment_id"]] = "Critical" if r["severity"] == "Critical" else "Abnormal"
    health = {"Normal": total_eq - len(worst), "Abnormal": sum(1 for v in worst.values() if v == "Abnormal"),
              "Critical": sum(1 for v in worst.values() if v == "Critical")}

    by_shift = defaultdict(lambda: {"resolved": 0, "escalated": 0, "open": 0})
    for s in sess:
        b = by_shift[_shift(s["created_at"])]
        b["resolved" if s["status"] in ("resolved", "closed") else "escalated" if s["mode"] == "expert" else "open"] += 1

    ilog = db.q(f"""SELECT i.*, COALESCE(e.name, a.name) AS eq_name, a.name AS unit_name FROM interlocks i
                   JOIN areas a ON a.id=i.area_id LEFT JOIN equipment e ON e.id=i.equipment_id
                   WHERE i.created_at>=?{_site_clause(site, 'i.site_code')[0]} ORDER BY i.created_at DESC""",
                [_since(1)] + sp)
    return {
        "period": "day",
        "mttd_min": _avg(_minutes(s["created_at"], s["identified_at"]) for s in sess),
        "mttr_min": _avg(_minutes(s["created_at"], s["resolved_at"]) for s in sess if s["status"] == "resolved"),
        "sessions_today": len(sess),
        "resolved_today": sum(1 for s in sess if s["status"] == "resolved"),
        "open_issues": sum(matrix.values()),
        "area_level_today": sum(1 for s in sess if s["kind"] == "Unlocalized"),
        "anomaly_matrix": [{"severity": k, "count": v} for k, v in matrix.items()],
        "equipment_health": [{"status": k, "count": v} for k, v in health.items()],
        "issues_by_shift": [{"shift": k, **by_shift[k]} for k in ("A", "B", "C")],
        "interlock_log": [{"id": i["id"], "rule_id": i["rule_id"], "category": i["category"], "action": i["action"],
                           "equipment": f"{i['eq_name']} · {i['unit_name']}", "severity": i["severity"],
                           "status": i["status"], "created_at": i["created_at"]} for i in ilog],
    }


def weekly(site: str | None) -> dict:
    sess = _sessions(site, 7)
    sc, sp = _site_clause(site)
    dist = Counter(SUBSYSTEM.get(s["kind"], s["kind"]) for s in sess if s["severity"] != "Low")
    total = sum(dist.values()) or 1
    cum, pareto = 0, []
    for k, v in dist.most_common():
        cum += v
        pareto.append({"subsystem": k, "count": v, "cumulative_pct": round(100 * cum / total, 1)})
    esc = db.q(f"SELECT e.*, s.created_at AS s_created FROM escalations e LEFT JOIN sessions s ON s.id=e.session_id "
               f"WHERE e.created_at>=?{_site_clause(site, 'e.site_code')[0]}", [_since(7)] + sp)
    closed = [s for s in sess if s["status"] in ("resolved", "closed", "escalated")]
    with_solution = [s for s in sess if s["status"] == "resolved"]
    days = []
    for d in range(6, -1, -1):
        day = (datetime.now(timezone.utc) - timedelta(days=d)).date()
        ds = [s for s in sess if _ts(s["created_at"]).date() == day]
        days.append({"date": day.isoformat(), "sessions": len(ds),
                     "escalated": sum(1 for s in ds if s["mode"] == "expert"),
                     "resolved_by_copilot": sum(1 for s in ds if s["resolved_by"] == "SiteBrain")})
    return {
        "period": "week",
        "sessions": len(sess),
        "failure_pareto": pareto,
        "escalation_rate_pct": round(100 * sum(1 for s in sess if s["mode"] == "expert") / len(sess), 1) if sess else 0,
        "mtte_min": _avg(_minutes(e["s_created"], e["created_at"]) for e in esc),
        "payload_compile_ms": _avg(e["compile_ms"] for e in esc),
        "sop_compliance_pct": round(100 * len(with_solution) / len(closed), 1) if closed else None,
        "daily": days,
    }


def monthly(site: str | None) -> dict:
    sc, sp = _site_clause(site)
    sites = db.q(f"SELECT * FROM sites WHERE 1=1{_site_clause(site, 'code')[0]}", sp)
    hours = 30 * 24
    uptime = []
    for st in sites:
        # Plant production stops when a gas-train asset (BUU) has a Critical incident; other units run on standby.
        crit = db.q("SELECT s.created_at, s.resolved_at FROM sessions s JOIN areas a ON a.id=s.area_id "
                    "WHERE s.site_code=? AND s.severity IN ('Critical','High') AND a.code='BUU' AND s.created_at>=?",
                    (st["code"], _since(30)))
        down = min(hours, sum((_minutes(c["created_at"], c["resolved_at"]) or 240) / 60 for c in crit))
        uptime.append({"site": st["code"], "name": st["name"], "operational_hours": round(hours - down),
                       "downtime_hours": round(down, 1), "uptime_pct": round(100 * (hours - down) / hours, 2)})

    il = db.q(f"SELECT rule_id, prevented_damage FROM interlocks WHERE created_at>=?{sc}", [_since(30)] + sp)
    avoided = sum(1 for i in il if i["prevented_damage"])
    by_rule = Counter(i["rule_id"] for i in il if i["prevented_damage"])

    now = datetime.now(timezone.utc)
    months = []
    for m in range(5, -1, -1):
        start = (now.replace(day=1) - timedelta(days=31 * m)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = (start + timedelta(days=32)).replace(day=1)
        rows = db.q(f"SELECT status, mode, resolved_by FROM sessions WHERE created_at>=? AND created_at<?{sc}",
                    [start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")] + sp)
        resolved = [r for r in rows if r["status"] == "resolved"]
        fcr = round(100 * sum(1 for r in resolved if r["resolved_by"] == "SiteBrain") / len(resolved), 1) if resolved else None
        months.append({"month": start.strftime("%b %Y"), "sessions": len(rows), "fcr_pct": fcr,
                       "kb_new": len(resolved)})
    kb_total = db.q1("SELECT COUNT(*) n FROM cases")["n"] + sum(m["kb_new"] for m in months)
    docs = db.q1("SELECT COUNT(*) n, COALESCE(SUM(chunk_count),0) c FROM documents")
    return {
        "period": "month",
        "fleet_uptime": uptime,
        "fleet_uptime_pct": round(sum(u["operational_hours"] for u in uptime) /
                                  max(1, sum(u["operational_hours"] + u["downtime_hours"] for u in uptime)) * 100, 2),
        "critical_incidents_avoided": avoided,
        "avoided_by_rule": [{"rule_id": k, "count": v} for k, v in by_rule.most_common()],
        # ingress is only possible if someone overrode a particle-protection interlock
        "particulate_ingress_events": db.q1(
            f"SELECT COUNT(*) n FROM overrides o JOIN interlocks i ON i.id=o.interlock_id WHERE o.status='approved' "
            f"AND i.rule_id='CMP-01' AND o.created_at>=?{_site_clause(site, 'o.site_code')[0]}", [_since(30)] + sp)["n"],
        "fcr_trend": months,
        "fcr_target_pct": 80,
        "kb_expansion": {"total_packages": kb_total, "documents": docs["n"], "chunks": docs["c"],
                         "this_month": months[-1]["kb_new"]},
    }
