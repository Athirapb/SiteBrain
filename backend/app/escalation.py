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
    if payload.get("chat_summary"):
        lines += ["", "Summary of the chat so far:"] + [f"  {x}" for x in payload["chat_summary"].splitlines() if x.strip()]
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


def expert_emails(site_code: str) -> list[str]:
    """Active technical experts who cover this plant (fleet-wide experts cover every plant)."""
    return [u["email"] for u in db.q("SELECT email FROM users WHERE role='expert' AND active "
                                     "AND (site_code IS NULL OR site_code=?) ORDER BY id", (site_code,))]


def send_email(to: str, subject: str, body: str, files: list[tuple[str, str, bytes]] = ()) -> str:
    """Send through SMTP when it is configured: 'sent' or 'failed'; 'logged' when there is no SMTP server or no
    recipient (the outbox keeps every message either way). files: (filename, content type, data)."""
    if not (config.SMTP_HOST and to):
        return "logged"
    try:
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = subject, config.SMTP_USER or "sitebrain@localhost", to
        msg.set_content(body)
        for name, ctype, data in files:
            main, _, sub = (ctype or "application/octet-stream").partition("/")
            msg.add_attachment(data, maintype=main, subtype=sub or "octet-stream", filename=name)
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as s:
            s.starttls()
            if config.SMTP_USER:
                s.login(config.SMTP_USER, config.SMTP_PASSWORD)
            s.send_message(msg)
        return "sent"
    except (OSError, smtplib.SMTPException) as e:
        log.warning("SMTP dispatch failed: %s", e)
        return "failed"


def _outbox(ticket: str, channel: str, recipient: str, subject: str, body: str, status: str) -> dict:
    db.insert("outbox", {"ticket": ticket, "channel": channel, "recipient": recipient, "subject": subject,
                         "body": body, "status": status, "created_at": db.now_iso()})
    return {"channel": channel, "recipient": recipient, "status": status}


def dispatch(ticket: str, payload: dict, attachments: list[dict] | None = None,
             recipients: list[str] | None = None) -> list[dict]:
    """Notify the experts. The escalation is answered when they get to it, not as a live chat, so the email
    carries everything they need. ESCALATION_EMAIL_TO overrides the list of experts for the plant."""
    subject, body, sms = digest(payload)
    results = []

    def out(channel, recipient, subj, text, status):
        results.append(_outbox(ticket, channel, recipient, subj, text, status))

    to = config.ESCALATION_EMAIL_TO or ", ".join(recipients or [])
    files = [(f"{ticket}.json", "application/json", json.dumps(payload, indent=2).encode())]
    files += [(a["filename"], a["content_type"], a["data"]) for a in attachments or []]
    out("email", to or "l3-experts@site.local", subject, body, send_email(to, subject, body, files))
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


def notify_reporter(ticket: str, session: dict, expert_name: str, text: str, root_cause: str | None) -> dict | None:
    """An expert replied: tell the person who reported the issue, so they don't have to wait in the app."""
    u = db.q1("SELECT email, name FROM users WHERE id=?", (session.get("user_id"),)) if session.get("user_id") else None
    if not u:
        return None
    subject = f"{ticket} · {expert_name} replied about {session.get('symptom') or 'your issue'}"
    lines = [f"Hello {u['name']},", "", f"{expert_name} replied on {ticket} ({session['id']}):", ""]
    if text:
        lines.append(text)
    if root_cause:
        lines += ["", f"Root cause: {root_cause}"]
    lines += ["", "Open SiteBrain → My Past Issues to see the full reply and continue."]
    body = "\n".join(lines)
    return _outbox(ticket, "email", u["email"], subject, body, send_email(u["email"], subject, body))
