"""Technical expert escalation (SRS §4.2): payload compilation and dispatch.

The payload follows the SRS "Standard Escalation JSON Payload Format" and carries the full transcript,
issue report, diagnostic matrix and 30-minute SCADA window, so the expert never has to re-ask (context preservation).
Dispatch: email/SMS digest to the outbox (MVP), optional MS Teams webhook and SMTP when configured,
plus an EAM work-request record.
"""
import json
import logging
import smtplib
import time
import urllib.request
from email.message import EmailMessage

from . import config, db

log = logging.getLogger("sitebrain.escalation")

ROLE_FOR_KIND = {
    "Scrubber": ("LEVEL_3_PROCESS_ENGINEER", "Level-3 Process Engineer"),
    "Filter": ("LEVEL_3_PROCESS_ENGINEER", "Level-3 Process Engineer"),
    "Membrane": ("LEVEL_3_PROCESS_ENGINEER", "Level-3 Process Engineer"),
    "Chiller": ("LEVEL_3_PROCESS_ENGINEER", "Level-3 Process Engineer"),
}


def target_role(kind: str | None) -> tuple[str, str]:
    return ROLE_FOR_KIND.get(kind, ("LEVEL_3_MAINTENANCE_ENGINEER", "Level-3 Maintenance Engineer"))


def build_payload(ticket: str, site: dict, area: dict, eq: dict | None, session: dict, checks_matrix: list[dict],
                  transcript: list[dict], telemetry: dict, interlocks: list[dict], urgency: str,
                  trigger: str, causes: list[dict]) -> dict:
    channel_role, _ = target_role(eq["kind"] if eq else None)
    tags = telemetry.get("tags", {})
    failed = [c for c in checks_matrix if c["status"] == "FAILED"]
    report = session.get("report") or {}
    return {
        "escalation_metadata": {
            "ticket_id": ticket,
            "timestamp_utc": db.now_iso(),
            "site_code": site["code"],
            "project_code": report.get("project_code") or site["project_code"],
            "project_name": report.get("project"),
            "area": f"{area['name']} ({area['code']})",
            "asset_id": (eq.get("tag") or eq["id"]) if eq else f"AREA-{area['code']}",
            "asset_name": f"{eq['name']} ({area['name']})" if eq else f"{area['name']} — equipment not yet identified",
            "urgency_level": urgency.upper(),
            "trigger": trigger,
        },
        "diagnostic_summary": {
            "session_id": session["id"],
            "turns_executed": session["turns"],
            "ai_confidence_score": round(session["confidence"], 2),
            "primary_symptom": session.get("symptom") or "Field-reported issue",
            "probable_causes": causes[:3],
            "failed_checkpoints": failed,
            "checkpoint_matrix": checks_matrix,
            "root_cause_analysis": (session.get("state") or {}).get("rca"),
            "issue_report": {
                "project": report.get("project"),
                "reported_by": report.get("reported_by"), "reported_at": report.get("reported_at"),
                "symptoms": report.get("symptom_labels") or [], "severity": report.get("severity"),
                "description": report.get("description") or "",
            },
        },
        "safety_state": [{"rule_id": i["rule_id"], "action": i["action"], "status": i["status"]} for i in interlocks],
        "telemetry_window_30min": {k: v for k, v in tags.items()},
        "conversation_transcript": transcript,
        "escalation_target": {
            "channel": "MS_TEAMS_EXPERT_QUEUE" if config.TEAMS_WEBHOOK_URL else "EMAIL_SMS_DIGEST",
            "assigned_role": channel_role,
        },
    }


def digest(payload: dict) -> tuple[str, str, str]:
    m, d = payload["escalation_metadata"], payload["diagnostic_summary"]
    subject = f"[{m['urgency_level']}] {m['ticket_id']} · {m['asset_name']} · {m['site_code']}"
    lines = [
        subject, "",
        f"Project: {m['project_code']}",
        f"Trigger: {m['trigger']}",
        f"Symptom: {d['primary_symptom']}",
        f"AI checks: {d['turns_executed']} · confidence {int(d['ai_confidence_score'] * 100)}%",
    ]
    req = payload.get("operator_request") or {}
    if req.get("description"):
        lines += ["", f"Field operator's description ({req['requested_by']}):", f"  {req['description']}"]
    if req.get("attachments"):
        lines += ["", "Attachments:"] + [f"  {a['filename']} ({a['content_type']}, {a['size'] // 1024 or 1} KB)"
                                         for a in req["attachments"]]
    lines += ["", "Diagnostic matrix:"]
    for c in d["checkpoint_matrix"]:
        lines.append(f"  [{c['status']:<6}] {c['checkpoint_id']} {c['description']}: {c['operator_input']}")
    if payload["safety_state"]:
        lines += ["", "Safety interlocks:"] + [f"  {s['rule_id']} ({s['status']}): {s['action']}" for s in payload["safety_state"]]
    if d["probable_causes"]:
        lines += ["", "Probable causes:"] + [f"  {int(c['likelihood'] * 100)}% {c['label']}" for c in d["probable_causes"]]
    lines += ["", "Transcript:"] + [f"  {t['role']}: {t['text']}" for t in payload["conversation_transcript"][-12:]]
    body = "\n".join(lines)
    sms = f"SiteBrain {m['urgency_level']} {m['ticket_id']}: {m['asset_name']} — {d['primary_symptom'][:90]}"
    return subject, body, sms


def dispatch(ticket: str, payload: dict, attachments: list[dict] | None = None) -> list[dict]:
    subject, body, sms = digest(payload)
    results = []

    def out(channel, recipient, subj, text, status):
        db.insert("outbox", {"ticket": ticket, "channel": channel, "recipient": recipient, "subject": subj,
                             "body": text, "status": status, "created_at": db.now_iso()})
        results.append({"channel": channel, "recipient": recipient, "status": status})

    # Email digest
    status = "logged"
    if config.SMTP_HOST and config.ESCALATION_EMAIL_TO:
        try:
            msg = EmailMessage()
            msg["Subject"], msg["From"], msg["To"] = subject, config.SMTP_USER or "sitebrain@localhost", config.ESCALATION_EMAIL_TO
            msg.set_content(body)
            msg.add_attachment(json.dumps(payload, indent=2).encode(), maintype="application", subtype="json",
                               filename=f"{ticket}.json")
            for a in attachments or []:
                main, _, sub = (a["content_type"] or "application/octet-stream").partition("/")
                msg.add_attachment(a["data"], maintype=main, subtype=sub or "octet-stream", filename=a["filename"])
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as s:
                s.starttls()
                if config.SMTP_USER:
                    s.login(config.SMTP_USER, config.SMTP_PASSWORD)
                s.send_message(msg)
            status = "sent"
        except (OSError, smtplib.SMTPException) as e:
            log.warning("SMTP dispatch failed: %s", e)
            status = "failed"
    out("email", config.ESCALATION_EMAIL_TO or "l3-experts@site.local", subject, body, status)
    out("sms", "+91-L3-ONCALL", subject, sms, "logged")

    if config.TEAMS_WEBHOOK_URL:
        try:
            req = urllib.request.Request(config.TEAMS_WEBHOOK_URL, method="POST",
                                         data=json.dumps({"text": f"**{subject}**\n\n```\n{body[:3500]}\n```"}).encode(),
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10).read()
            out("teams", "MS_TEAMS_EXPERT_QUEUE", subject, body, "sent")
        except OSError as e:
            log.warning("Teams dispatch failed: %s", e)
            out("teams", "MS_TEAMS_EXPERT_QUEUE", subject, body, "failed")

    out("eam", "EAM work request", subject, json.dumps(payload["escalation_metadata"]), "logged")
    return results


class Stopwatch:
    def __enter__(self):
        self.t = time.perf_counter()
        return self

    def __exit__(self, *a):
        self.ms = int((time.perf_counter() - self.t) * 1000)
