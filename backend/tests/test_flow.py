"""End-to-end API tests on a freshly seeded PostgreSQL database with the deterministic engine.

Uses TEST_DATABASE_URL (default: the `sitebrain_test` database next to the dev one). It is wiped on every run.
"""
import os

os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL",
                                       "postgresql://sitebrain:sitebrain@localhost:5433/sitebrain_test")
os.environ["SITEBRAIN_LLM"] = "off"
os.environ["SITEBRAIN_INCIDENTS_DIR"] = "off"  # tests import their own sample reports
os.environ["SITEBRAIN_SURVEY"] = "0"  # one check at a time; test_condition_survey_* switch the survey on

import pytest
from fastapi.testclient import TestClient

from app import catalog, config, safety, seed
from app.diagnosis import CANT, DONE, HOW, NOT_SURE, NOT_WORKING, SKIP_WHY, STEP_HOW, WORKING
from app.main import app


@pytest.fixture(scope="module")
def client():
    seed.seed(reset=True)
    with TestClient(app) as c:
        yield c


def login(c, username):
    return {"Authorization": "Bearer " + c.post("/api/auth/login", json={"username": username}).json()["token"]}


def area_id(c, h, code):
    return next(a["id"] for a in c.get("/api/areas", headers=h).json() if a["code"] == code)


def report(c, h, **body):
    r = c.post("/api/sessions", json={"severity": "Medium", "project_id": 1, **body}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def say(c, sid, text, h):
    r = c.post(f"/api/sessions/{sid}/messages", json={"text": text}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def last_replies(v):
    return next((m.get("replies") for m in reversed(v["messages"]) if m.get("replies")), None)


def test_workbook_seeds_the_equipment_inventory():
    items = catalog.parse_checksheet(config.CHECKSHEET_XLSX)
    assert len(items) == 111
    assert {i["unit"] for i in items} == {"BUU", "D1", "D2", "D3", "D4", "HWG", "SLS", "FEED", "CDT"}
    lp1 = next(i for i in items if i["name"] == "LP 1")
    assert lp1["kind"] == "Compressor" and "checks" not in lp1
    assert {"H2S Scrubber Vessel", "Gas Filtration Skid", "Membrane Upgrader"} <= {
        i["name"] for i in catalog.augment_with_process_assets(items)}


def test_report_flags_drive_safety_rules():
    gas = safety.report_flags({"symptoms": [], "severity": "Low", "description": "strong smell of gas near the flange"}, None)
    assert gas == {"gas_leak"}
    assert [r["rule_id"] for r in safety.evaluate(None, "Biogas Upgradation Unit", gas)] == ["GAS-01"]
    crit = safety.report_flags({"symptoms": ["vibration"], "severity": "Critical"}, "Agitator")
    assert "ROT-01" in [r["rule_id"] for r in safety.evaluate("Agitator", "D2 Agitator 3", crit)]
    mild = safety.report_flags({"symptoms": ["vibration"], "severity": "Medium"}, "Agitator")
    assert [r["rule_id"] for r in safety.evaluate("Agitator", "D2 Agitator 3", mild)] == ["ROT-02"]


def test_rbac(client):
    tech = login(client, "operator1")
    assert client.get("/api/analytics/daily", headers=tech).status_code == 403
    assert client.get("/api/equipment?site=GPS-BUU-02", headers=tech).status_code == 403
    assert client.get("/api/equipment", headers={}).status_code == 401
    assert client.post("/api/areas", json={"code": "X1", "name": "X"}, headers=tech).status_code == 403
    # control room work belongs to the expert: a field operator can't approve overrides or release interlocks
    assert client.post("/api/control/overrides/1/decide", json={"approve": True}, headers=tech).status_code == 403
    assert client.post("/api/control/interlocks/1/release", json={"note": "x"}, headers=tech).status_code == 403
    ex = login(client, "expert1")
    assert client.get("/api/analytics/daily", headers=ex).status_code == 200
    assert client.get("/api/control/interlocks", headers=ex).status_code == 200
    from app import db
    assert {u["role"] for u in db.q("SELECT role FROM users")} == {"field_operator", "expert"}


def test_report_needs_a_project_a_place_and_a_symptom(client):
    h = login(client, "operator1")
    d2 = area_id(client, h, "D2")
    assert client.post("/api/sessions", json={"project_id": 1, "symptoms": ["noise"]}, headers=h).status_code == 400
    assert client.post("/api/sessions", json={"project_id": 1, "area_id": d2}, headers=h).status_code == 400
    for project in ({}, {"project_id": 999}):
        r = client.post("/api/sessions", json={"area_id": d2, "symptoms": ["noise"], **project}, headers=h)
        assert r.status_code == 400 and "project" in r.json()["detail"]
    projects = client.get("/api/projects", headers=h).json()
    assert len(projects) == 17 and projects[8] == {"id": 9, "name": "Jio - Jhajjar 02", "op_id": None, "code": "PS_JHA_02"}
    v = report(client, h, project_id=8, area_id=d2, symptoms=["noise"])
    rep = v["session"]["report"]
    assert (rep["project"], rep["project_code"]) == ("Jio - Pilibhit 01", "PS_PIL_01")
    assert v["messages"][0]["project"] == "Jio - Pilibhit 01"


def test_symptoms_must_fit_the_equipment_or_area(client):
    h = login(client, "operator1")
    assert catalog.symptoms_for(["Membrane"]) == {"gas", "pressure", "quality"}
    r = client.post("/api/sessions", headers=h, json={"project_id": 1, "symptoms": ["quality"], "severity": "Medium",
                                                      "equipment_id": "GPS-BUU-04|D2|D2 Agitator 1"})
    assert r.status_code == 400 and "Gas quality off-spec" in r.json()["detail"]
    r = client.post("/api/sessions", headers=h, json={"project_id": 1, "symptoms": ["quality"], "severity": "Medium",
                                                      "area_id": area_id(client, h, "D2")})
    assert r.status_code == 400  # no equipment in a digester area shows gas quality
    report(client, h, area_id=area_id(client, h, "BUU"), symptoms=["quality"])


def test_several_answers_can_be_picked_for_one_check(client):
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|D2|D2 Agitator 2", symptoms=["vibration"])
    sid = v["session"]["id"]
    v = client.get(f"/api/sessions/{sid}", headers=h).json()
    ask = next(m for m in reversed(v["messages"]) if m.get("replies"))
    assert ask["multi"]
    picks = [r for r in ask["replies"] if r not in (HOW, CANT)][:2]
    r = client.post(f"/api/sessions/{sid}/messages", json={"text": "; ".join(picks), "choices": picks}, headers=h)
    assert r.status_code == 200, r.text
    v = r.json()
    assert next(m for m in v["messages"] if m["type"] == "user")["choices"] == picks
    assert v["session"]["turns"] == 1  # both picks answer the one check
    x = client.post(f"/api/sessions/{sid}/escalate", headers=h).json()
    matrix = client.get(f"/api/escalations/{x['escalation']['ticket']}",
                        headers=login(client, "expert1")).json()["payload"]["diagnostic_summary"]["checkpoint_matrix"]
    assert any(c["operator_input"] == "; ".join(picks) for c in matrix)


def test_escalated_chat_is_between_the_operator_and_the_expert(client):
    h, ex = login(client, "operator1"), login(client, "expert1")
    v = report(client, h, equipment_id="GPS-BUU-04|D2|D2 Agitator 4", symptoms=["noise"])
    sid = v["session"]["id"]
    v = client.post(f"/api/sessions/{sid}/escalate", headers=h).json()
    assert v["session"]["mode"] == "expert" and v["escalation"]["expert_name"] == "Unassigned"
    n = len(v["messages"])
    assert not any(m.get("expert") for m in v["messages"]), "no simulated expert joins"
    v = say(client, sid, "Noise is louder at the gearbox end", h)
    assert len(v["messages"]) == n + 1 and v["messages"][-1]["type"] == "user", "SiteBrain stays out of the chat"
    assert client.post(f"/api/sessions/{sid}/expert-message", json={"text": "Check the oil level"}, headers=h).status_code == 403
    v = client.post(f"/api/sessions/{sid}/expert-message", json={"text": "Check the oil level"}, headers=ex).json()
    assert v["escalation"]["expert_name"] == "Expert 1" and v["escalation"]["claimed_by"]
    assert v["messages"][-1]["expert"] and v["messages"][-1]["text"] == "Check the oil level"
    v = say(client, sid, "Oil is low", h)
    assert v["messages"][-1]["type"] == "user" and v["messages"][-1]["text"] == "Oil is low"
    v = client.post(f"/api/sessions/{sid}/expert-message", headers=ex,
                    json={"text": "", "root_cause": "Oil level not checked in PM", "steps": ["Top up the gearbox oil"]}).json()
    assert v["session"]["identified"]
    v = client.post(f"/api/sessions/{sid}/resolve", headers=h).json()
    assert v["session"]["status"] == "resolved" and v["session"]["resolved_by"] == "Expert"


def test_equipment_report_troubleshoots_without_signoff_then_resolves(client):
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|D2|D2 Agitator 3", symptoms=["vibration", "noise"],
               severity="Critical", description="Body shaking, grinding noise from the gearbox")
    sid = v["session"]["id"]
    assert v["session"]["pending_signoff"] == 0 and not any(m["type"] == "signoff" for m in v["messages"])
    assert any(i["rule_id"] == "ROT-01" for i in v["interlocks"]), "interlocks are still recorded for the control room"
    assert v["messages"][0]["type"] == "report"
    assert last_replies(v), "the first field check is asked straight after the report"
    for t in ["Intact, no play", "Above 85°C", "Dark with metal fines"]:
        v = say(client, sid, t, h)
    # fishbone narrowed to the direct cause → finding with immediate actions, then the 5-Why starts
    finding = next(m for m in v["messages"] if m["type"] == "finding")
    assert finding["direct_cause"] == "Gearbox output bearing wear" and finding["steps"]
    assert v["phase"] == "why" and SKIP_WHY in last_replies(v)
    assert "KB-0412" in v["session"]["cited"]
    for _ in range(5):  # follow the why tree down its first branches to a root cause
        if v["session"]["identified"]:
            break
        v = say(client, sid, last_replies(v)[0], h)
    sol = next(m for m in v["messages"] if m["type"] == "solution")
    assert v["session"]["identified"] == 1 and sol["why_chain"] and sol["preventive"]
    assert sol["category"] in ("Man", "Machine", "Method", "Material", "Measurement", "Environment")
    assert v["session"]["root_cause"] == sol["root_cause"] != "Gearbox output bearing wear"
    v = client.post(f"/api/sessions/{sid}/resolve", headers=h).json()
    assert v["session"]["status"] == "resolved" and v["session"]["resolved_by"] == "SiteBrain"
    cases = client.get("/api/kb/cases?q=D2 Agitator 3", headers=h).json()["items"]
    learned = next(c for c in cases if c["source"] == "Copilot session")
    assert learned["why_chain"] and learned["category"] and learned["prevent"]


def test_pump_seal_rca_reaches_a_systemic_root_cause(client):
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|D1|D1 RC Pump 1", symptoms=["leak"], description="slurry spraying at the shaft")
    sid = v["session"]["id"]
    assert any(m["type"] == "fishbone" for m in v["messages"])
    assert {b["category"] for b in v["fishbone"]} >= {"Machine", "Method", "Material"}
    q = next(m for m in reversed(v["messages"]) if m.get("replies"))
    assert q.get("purpose") and HOW in q["replies"] and CANT in q["replies"]
    for t in ["From the seal or gland", "No flow at all"]:
        v = say(client, sid, t, h)
    assert next(m for m in v["messages"] if m["type"] == "finding")["direct_cause"] == "Mechanical seal face damage"
    for t in ["It ran dry — flush water was off or weak", "Flush valve left closed after maintenance"]:
        v = say(client, sid, t, h)
    sol = next(m for m in v["messages"] if m["type"] == "solution")
    assert sol["root_cause"].startswith("No flush-water line-up check") and sol["category"] == "Method"
    assert [w["because"] for w in sol["why_chain"]] == ["It ran dry — flush water was off or weak",
                                                         "Flush valve left closed after maintenance"]
    assert v["rca"]["direct_cause"] == "Mechanical seal face damage"
    # then a guided fix, one step at a time — with help available at each step
    assert v["phase"] == "fix" and v["messages"][-1]["fix_step"] == 1 and DONE in last_replies(v)
    total = v["messages"][-1]["fix_total"]
    v = say(client, sid, STEP_HOW, h)
    assert v["messages"][-1]["side"] and v["messages"][-1]["fix_step"] == 1 and v["fix"]["idx"] == 0
    for n in range(total):
        v = say(client, sid, DONE, h)
    assert v["phase"] == "verify" and last_replies(v) == [WORKING, NOT_WORKING]
    assert any(m.get("items") == sol["preventive"] for m in v["messages"])
    v = say(client, sid, WORKING, h)
    assert v["session"]["status"] == "resolved" and v["session"]["resolved_by"] == "SiteBrain"


def test_technician_can_chat_anytime_and_reopen_when_fix_fails(client):
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|D4|D4 RC Pump 2", symptoms=["leak"])
    sid = v["session"]["id"]
    pending = last_replies(v)
    v = say(client, sid, "What is the normal discharge pressure for this pump?", h)
    side = v["messages"][-1]
    assert side["side"] and side["text"] and last_replies(v) == pending and v["session"]["turns"] == 0
    v = say(client, sid, "The pump was overhauled last week by a contractor", h)  # extra information, noted
    assert v["messages"][-1]["side"] and last_replies(v) == pending
    for t in ["From the seal or gland", "No flow at all", SKIP_WHY]:
        v = say(client, sid, t, h)
    v = say(client, sid, "Do I need a permit for this?", h)  # questions during the fix get answers too
    assert v["messages"][-1]["side"] and v["phase"] == "fix"
    while v["phase"] == "fix":
        v = say(client, sid, DONE, h)
    v = say(client, sid, NOT_WORKING, h)  # the fix didn't hold: back to the fishbone with that cause excluded
    assert v["session"]["status"] == "active" and not v["session"]["identified"] and v["phase"] == "diagnose"


def test_technician_can_ask_how_skip_checks_and_give_own_why(client):
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|D1|D1 RC Pump 2", symptoms=["leak"], severity="Low")
    sid = v["session"]["id"]
    asked = next(m for m in reversed(v["messages"]) if m.get("replies"))["text"]
    v = say(client, sid, HOW, h)
    assert v["messages"][-1]["text"].startswith("Here's how") and v["session"]["turns"] == 0
    v = say(client, sid, CANT, h)
    assert v["session"]["turns"] == 0 and v["messages"][-1]["text"] != asked
    client.post(f"/api/sessions/{sid}/resolve", headers=h)  # close it; the own-why path starts afresh

    v = report(client, h, equipment_id="GPS-BUU-04|D1|D1 RC Pump 2", symptoms=["leak"], severity="Low")
    sid = v["session"]["id"]
    for t in ["From the seal or gland", "No flow at all"]:
        v = say(client, sid, t, h)
    v = say(client, sid, "The flush pump was switched off to save power during the night shift", h)
    sol = next(m for m in v["messages"] if m["type"] == "solution")
    assert sol["root_cause"].startswith("The flush pump was switched off") and sol["why_chain"][-1].get("own")


def test_skipping_the_why_why_still_gives_an_rca_summary(client):
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|D1|D1 Transfer Pump 1", symptoms=["leak"])
    sid = v["session"]["id"]
    for t in ["From the seal or gland", "No flow at all", SKIP_WHY]:
        v = say(client, sid, t, h)
    sol = next(m for m in v["messages"] if m["type"] == "solution")
    assert v["session"]["identified"] == 1 and sol["root_cause"] == "Mechanical seal face damage" and not sol["why_chain"]


def test_llm_outage_during_why_why_continues_on_the_knowledge_brain(client):
    from app import db, diagnosis
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|D2|D2 RC Pump 1", symptoms=["leak"])
    sid = v["session"]["id"]
    s = diagnosis.load_session(sid)  # as if the LLM had confirmed the direct cause and asked the first why
    s["state"].update(rca={"cause": None, "direct_cause": "Mechanical seal face damage", "category": "Machine",
                           "chain": [], "node": []}, pending=None)
    diagnosis.save_session(s, engine="llm")
    v = say(client, sid, "The flush water was off", h)  # LLM is off in tests, so this turn falls back
    assert v["phase"] == "why" and v["rca"]["cause"] == "seal"
    assert v["messages"][-1]["why_step"] == 1 and SKIP_WHY in last_replies(v)


def test_knowledge_brain_is_trained(client):
    h = login(client, "expert1")
    stats = client.get("/api/kb/brain", headers=h).json()
    assert stats["rca_cases"] > 0 and stats["root_causes"] > 0 and stats["documents"] > 0
    lib = client.get("/api/kb/troubleshooting", headers=h).json()
    pump = next(x for x in lib if x["kind"] == "Pump")
    assert pump["maintenance"]["pm"] and all(c["why"] for c in pump["causes"])
    assert client.get("/api/kb/conditions", headers=h).status_code == 200
    again = client.post("/api/kb/train", headers=h).json()
    assert again["documents_added"] == 0 and again["documents_updated"] == 0  # idempotent


def test_area_report_is_localized_to_equipment_then_diagnosed(client):
    h = login(client, "operator1")
    v = report(client, h, area_id=area_id(client, h, "D2"), symptoms=["vibration"], severity="High")
    sid = v["session"]["id"]
    assert v["session"]["equipment_id"] is None and v["localizing"]
    replies = last_replies(v)
    assert NOT_SURE in replies and any("Agitator" in r for r in replies)
    v = say(client, sid, "D2 Agitator 1", h)
    assert v["session"]["equipment_id"] == "GPS-BUU-04|D2|D2 Agitator 1"
    assert not v["localizing"] and v["equipment"]["kind"] == "Agitator"
    assert any(m["type"] == "event" and "localized" in m["text"] for m in v["messages"])
    assert last_replies(v) and NOT_SURE not in last_replies(v)


def test_area_report_named_in_description_is_localized_directly(client):
    h = login(client, "operator1")
    v = report(client, h, area_id=area_id(client, h, "BUU"), symptoms=["noise"], description="LP 1 is knocking")
    assert v["session"]["equipment_id"] == "GPS-BUU-04|BUU|LP 1" and not v["localizing"]


def offers(v):
    return [m for m in v["messages"] if m["type"] == "offer"]


def test_area_report_that_cannot_be_localized_suggests_an_expert(client):
    h = login(client, "operator1")
    v = report(client, h, area_id=area_id(client, h, "SLS"), symptoms=["noise"])
    sid = v["session"]["id"]
    v = say(client, sid, NOT_SURE, h)
    assert v["localizing"] and "Decanter" in last_replies(v)  # narrowed by equipment type next
    v = say(client, sid, NOT_SURE, h)
    assert v["session"]["mode"] == "bot" and not v["escalation"], "never escalates on its own"
    assert "could not be localized" in offers(v)[-1]["reason"]
    v = client.post(f"/api/sessions/{sid}/escalate", headers=h).json()  # the operator takes the suggestion
    assert v["session"]["mode"] == "expert"
    assert "could not be localized" in v["escalation"]["trigger_reason"]
    x = client.get(f"/api/escalations/{v['escalation']['ticket']}", headers=login(client, "expert1")).json()
    assert x["payload"]["escalation_metadata"]["asset_id"] == "AREA-SLS"
    v = say(client, sid, "Decanter 2", h)  # naming it in the expert chat still records the equipment
    assert v["session"]["equipment_id"] == "GPS-BUU-04|SLS|Decanter 2"
    assert v["messages"][-1]["type"] == "event" and not any(m.get("expert") for m in v["messages"])


def test_telemetry_contradiction_suggests_an_expert_then_escalates_with_srs_payload(client):
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|BUU|LP 2", symptoms=["vibration"], severity="High")
    sid = v["session"]["id"]
    v = say(client, sid, "No unusual noise", h)
    assert v["session"]["mode"] == "bot" and "contradicts SCADA" in offers(v)[-1]["reason"]
    assert last_replies(v), "the checks carry on until the operator decides"
    v = client.post(f"/api/sessions/{sid}/escalate", headers=h).json()
    assert v["session"]["mode"] == "expert"
    assert v["escalation"]["trigger_reason"].startswith("Escalated by Field Operator 1")
    assert "contradicts SCADA" in v["escalation"]["trigger_reason"]
    x = client.get(f"/api/escalations/{v['escalation']['ticket']}", headers=login(client, "expert1")).json()
    p = x["payload"]
    assert set(p) >= {"escalation_metadata", "diagnostic_summary", "telemetry_window_30min", "escalation_target"}
    assert p["diagnostic_summary"]["failed_checkpoints"]
    assert p["diagnostic_summary"]["issue_report"]["symptoms"] == ["High vibration"]
    assert x["compile_ms"] < 30_000
    assert {o["channel"] for o in x["outbox"]} >= {"email", "sms"}


def test_turn_limit_only_suggests_an_expert(client):
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|SLS|WAM 2", symptoms=["flow"])
    sid = v["session"]["id"]
    for _ in range(config.MAX_DIAGNOSTIC_TURNS + 2):
        v = client.get(f"/api/sessions/{sid}", headers=h).json()
        if v["session"]["identified"]:
            break
        replies = last_replies(v)
        say(client, sid, replies[0] if replies else "not sure", h)
    v = client.get(f"/api/sessions/{sid}", headers=h).json()
    assert v["session"]["mode"] == "bot"
    assert v["session"]["identified"] or len(offers(v)) == 1, "suggested once, not on every turn"


def test_only_the_escalate_button_escalates_with_description_and_attachments(client):
    h, ex = login(client, "operator1"), login(client, "expert1")
    v = report(client, h, equipment_id="GPS-BUU-04|BUU|LP 3", symptoms=["noise"])
    sid = v["session"]["id"]
    v = say(client, sid, "Please escalate this, I need an expert", h)
    assert v["session"]["mode"] == "bot" and not v["escalation"], "typing does not escalate"
    photo, clip = b"\x89PNG fake image", b"fake video"
    r = client.post(f"/api/sessions/{sid}/escalate", headers=h, data={"description": "Knocking at the 2nd stage valve"},
                    files=[("files", ("valve.png", photo, "image/png")), ("files", ("sound.mp4", clip, "video/mp4"))])
    assert r.status_code == 200, r.text
    v = r.json()
    assert v["session"]["mode"] == "expert" and v["escalation"]["trigger_reason"].startswith("Escalated by Field Operator 1")
    note = next(m for m in v["messages"] if m["type"] == "escalation")
    assert note["text"] == "Knocking at the 2nd stage valve" and [f["filename"] for f in note["attachments"]] == ["valve.png", "sound.mp4"]
    x = client.get(f"/api/escalations/{v['escalation']['ticket']}", headers=ex).json()
    assert x["payload"]["operator_request"]["description"] == "Knocking at the 2nd stage valve"
    assert [a["size"] for a in x["attachments"]] == [len(photo), len(clip)]
    assert "Knocking at the 2nd stage valve" in x["outbox"][0]["body"] and "valve.png" in x["outbox"][0]["body"]
    r = client.get(f"/api/escalations/{x['ticket']}/attachments/{x['attachments'][0]['id']}", headers=h)
    assert r.status_code == 200 and r.content == photo and r.headers["content-type"] == "image/png"
    assert client.get(f"/api/escalations/{x['ticket']}/attachments/{x['attachments'][0]['id']}",
                      headers=login(client, "operator2")).status_code == 403  # another site's operator


def test_escalation_attachments_are_limited_and_html_never_renders(client):
    from app import diagnosis
    h = login(client, "operator1")
    sid = report(client, h, equipment_id="GPS-BUU-04|BUU|LP 4", symptoms=["noise"])["session"]["id"]
    big = b"x" * (diagnosis.MAX_ATTACHMENT_BYTES + 1)
    r = client.post(f"/api/sessions/{sid}/escalate", headers=h, files=[("files", ("big.mp4", big, "video/mp4"))])
    assert r.status_code == 400 and "big.mp4" in r.json()["detail"]
    r = client.post(f"/api/sessions/{sid}/escalate", headers=h,
                    files=[("files", (f"{i}.png", b"x", "image/png")) for i in range(diagnosis.MAX_ATTACHMENTS + 1)])
    assert r.status_code == 400
    assert client.get(f"/api/sessions/{sid}", headers=h).json()["session"]["mode"] == "bot"
    v = client.post(f"/api/sessions/{sid}/escalate", headers=h,
                    files=[("files", ("page.html", b"<script>alert(1)</script>", "text/html"))]).json()
    a = next(m for m in v["messages"] if m["type"] == "escalation")["attachments"][0]
    r = client.get(f"/api/escalations/{v['escalation']['ticket']}/attachments/{a['id']}", headers=h)
    assert r.headers["content-type"] == "application/octet-stream" and r.headers["content-disposition"].startswith("attachment")


def test_gas_smell_engages_a_non_overridable_interlock(client):
    tech, op = login(client, "operator1"), login(client, "expert1")
    v = report(client, tech, equipment_id="GPS-BUU-04|BUU|Gas Blower 1", symptoms=["gas"], severity="High")
    assert v["session"]["severity"] == "Critical"  # raised by the CRITICAL GAS-01 interlock
    il = client.get("/api/control/interlocks", headers=op).json()["items"]
    gas = next(i for i in il if i["rule_id"] == "GAS-01" and i["eq_name"] == "Gas Blower 1")
    o = client.post("/api/control/overrides", json={"interlock_id": gas["id"], "reason": "keep running"}, headers=tech).json()
    assert o["status"] == "blocked"


def test_plant_setup_manages_areas_and_equipment(client):
    op, tech = login(client, "expert1"), login(client, "operator1")
    r = client.post("/api/areas", json={"code": "ww", "name": "Wastewater Treatment"}, headers=op)
    assert r.status_code == 200, r.text
    area = r.json()
    assert area["code"] == "WW"
    assert client.post("/api/areas", json={"code": "WW", "name": "Other"}, headers=op).status_code == 409
    r = client.post("/api/equipment", json={"area_id": area["id"], "name": "Sludge Pump 1", "kind": "Pump"}, headers=op)
    assert r.status_code == 200, r.text
    eq_id = r.json()["id"]
    assert client.post("/api/equipment", json={"area_id": area["id"], "name": "sludge pump 1", "kind": "Pump"},
                       headers=op).status_code == 409
    r = client.put(f"/api/equipment?id={eq_id}", json={"area_id": area["id"], "name": "Sludge Pump A", "kind": "Pump",
                                                        "tag": "P-101"}, headers=op)
    assert r.status_code == 200 and r.json()["name"] == "Sludge Pump A"
    assert any(e["id"] == eq_id and e["unit_name"] == "Wastewater Treatment"
               for e in client.get("/api/equipment", headers=tech).json())

    # a single-equipment area localizes immediately
    v = report(client, tech, area_id=area["id"], symptoms=["leak"])
    assert v["session"]["equipment_id"] == eq_id
    assert client.delete(f"/api/equipment?id={eq_id}", headers=op).status_code == 409  # has issue history
    r = client.put(f"/api/equipment?id={eq_id}", json={"area_id": area["id"], "name": "Sludge Pump A", "kind": "Pump",
                                                        "active": False}, headers=op)
    assert r.status_code == 200
    assert all(e["id"] != eq_id for e in client.get("/api/equipment", headers=tech).json())
    assert client.delete(f"/api/areas/{area['id']}", headers=op).status_code == 409

    empty = client.post("/api/areas", json={"code": "TMP", "name": "Temporary"}, headers=op).json()
    assert client.put(f"/api/areas/{empty['id']}", json={"code": "TMP", "name": "Temporary Yard"}, headers=op).json()["name"] \
        == "Temporary Yard"
    assert client.delete(f"/api/areas/{empty['id']}", headers=op).status_code == 200


def test_old_demo_users_migrate_to_two_roles(client):
    from app import db, seed
    db.ex("UPDATE users SET name='A. Nair', username='tech', role='technician' WHERE username='operator1'")
    db.insert("users", {"name": "M. Das", "username": "operator", "role": "operator", "title": "Control Room Operator",
                        "site_code": "GPS-BUU-04", "token": "old-op"})
    db.ex("UPDATE messages SET payload = jsonb_set(payload, '{author}', '\"A. Nair\"') WHERE id = "
          "(SELECT MIN(id) FROM messages WHERE type='report')")
    seed.migrate_users()
    users = {u["username"]: u for u in db.q("SELECT * FROM users")}
    assert set(users) == {"operator1", "operator2", "expert1", "expert2"}
    assert users["operator1"]["name"] == "Field Operator 1" and users["operator1"]["role"] == "field_operator"
    assert not db.q1("SELECT id FROM messages WHERE payload::text LIKE '%A. Nair%'")
    seed.migrate_users()  # idempotent


def test_audit_log_is_append_only():
    from app import db
    with pytest.raises(Exception):
        db.ex("DELETE FROM audit_log")


def test_dashboards(client):
    op = login(client, "expert1")
    for p in ("daily", "weekly", "monthly"):
        r = client.get(f"/api/analytics/{p}", headers=op)
        assert r.status_code == 200
    d = client.get("/api/analytics/daily", headers=op).json()
    assert d["open_issues"] >= 1 and {s["shift"] for s in d["issues_by_shift"]} == {"A", "B", "C"}
    m = client.get("/api/analytics/monthly", headers=op).json()
    assert m["fcr_trend"] and m["fleet_uptime"]


def test_learning_smoothing_math():
    from app import brain, learning
    assert learning.fit_models({}, 10) == {}
    pump = brain.TREES["Pump"]
    flush = next(q for q in pump["questions"] if q["id"] == "flush")
    # 20 confirmed seal failures where the flush water was only weak — never "No flow at all"
    ev = {"Pump": [{"cause": "seal", "answers": [("flush", "Weak or on and off")]}] * 20}
    m = learning.fit_models(ev, 10)["Pump"]
    assert m["sessions"] == 20 and m["prior"]["seal"] > 3 and all(m["prior"][c] < 1 for c in m["prior"] if c != "seal")
    weak, none = m["lik"]["flush"]["Weak or on and off"]["seal"], m["lik"]["flush"]["No flow at all"]["seal"]
    assert weak > 1.5 and none < 0.5
    raw = [o["lik"].get("seal", 1.0) for o in flush["options"]]
    p_hat = [r / sum(raw) * m["lik"]["flush"][o["label"]]["seal"] for r, o in zip(raw, flush["options"])]
    assert abs(sum(p_hat) - 1) < 1e-9  # still a probability distribution over the answers
    brain.set_learned({"Pump": m})
    try:
        t = brain.tree_for("Pump")
        assert t is not pump and t["learned_from"] == 20
        assert next(c for c in t["causes"] if c["id"] == "seal")["prior"] > 3
        assert next(q for q in pump["questions"] if q["id"] == "flush")["options"][2]["lik"]["seal"] == 3.5  # authored untouched
    finally:
        brain.set_learned({})
    assert brain.tree_for("Pump") is pump  # no learning → exactly the authored tree


def test_resolved_sessions_teach_the_tree(client):
    from app import brain, learning
    h, ex = login(client, "operator1"), login(client, "expert1")
    before = learning.report("Pump")["kinds"][0]
    for n in range(3):  # three confirmed seal failures on different pumps
        v = report(client, h, equipment_id=f"GPS-BUU-04|D4|D4 RC Pump {1 + n % 2}" if n < 2 else "GPS-BUU-04|D4|D4 Transfer Pump 1",
                   symptoms=["leak"])
        sid = v["session"]["id"]
        for t in ["From the seal or gland", "No flow at all", SKIP_WHY]:
            v = say(client, sid, t, h)
        assert client.post(f"/api/sessions/{sid}/resolve", headers=h).json()["session"]["status"] == "resolved"
    rep = client.get("/api/kb/learning?kind=Pump", headers=ex).json()["kinds"][0]
    seal = next(c for c in rep["causes"] if c["id"] == "seal")
    assert rep["sessions"] >= before["sessions"] + 3 and seal["learned_share"] > seal["authored_share"]
    assert any(c["cause"] == "Mechanical seal face damage" and c["learned"] > c["authored"] for c in rep["changes"])
    # the next leak report on a pump starts with seal damage already more likely
    v = report(client, h, equipment_id="GPS-BUU-04|D3|D3 RC Pump 2", symptoms=["noise"])
    lead = {c["id"]: c["likelihood"] for c in v["session"]["causes"]}
    assert brain.tree_for("Pump")["learned_from"] >= 3 and lead.get("seal", 0) > 0


def test_documents_are_tagged_by_equipment_from_content():
    from app.diagnosis import _covers
    from app.knowledge import detect_kinds
    assert detect_kinds("Hot water generator burner lockout. Reset the HWG after purge. HWG flame sensor.") == ["HWG"]
    assert detect_kinds("Gas blower bearings. Blower belt tension. Blower vibration; the pump is fed separately.") == ["Blower"]
    assert detect_kinds("Permit to work and gas testing apply to all work on site.") == []
    blower = {"equipment_kinds": ["Blower"], "excerpt": "Grease the bearings every 500 h."}
    general = {"equipment_kinds": [], "excerpt": "Wear gloves and goggles."}
    gas_train = {"equipment_kinds": ["Chiller", "Compressor"], "excerpt": "Chiller outlet dew point below 5 °C."}
    assert not _covers(blower, "Pump") and _covers(blower, "Blower") and _covers(general, "Pump")
    assert _covers(gas_train, "Chiller") and not _covers(gas_train, "Compressor")  # passage is about the chiller only


def test_uploaded_manual_answers_questions_whatever_its_title(client):
    ex = login(client, "expert1")
    text = ("# Grundfos CR maintenance notes\n\nThe pump coupling hub takes lubricant grade Kluberplex BEM 41-132; "
            "never mix it with lithium greases on the pump coupling.\n\nPump casing bolts are retorqued after the "
            "first 24 hours of pump operation.").encode()
    r = client.post("/api/kb/documents", files={"file": ("grundfos-cr.md", text)}, data={"kind": "manual"}, headers=ex)
    assert r.status_code == 200, r.text
    assert r.json()["equipment_kinds"] == ["Pump"]  # "Pump" is nowhere in the title

    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|D1|D1 RC Pump 1", symptoms=["leak"], severity="Low")
    v = say(client, v["session"]["id"], "Which lubricant grade goes on the coupling hub?", h)
    assert any("Kluberplex" in (m.get("text") or "") for m in v["messages"]), [m.get("text") for m in v["messages"][-3:]]


def fake_llm(monkeypatch, reply):
    """Stand in for the LLM: `reply(system, messages, schema)` returns the parsed JSON (or None for an outage)."""
    from app import llm
    calls = []
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "provider", lambda: "groq")
    monkeypatch.setattr(llm, "complete_json", lambda system, messages, schema, max_tokens=0:
                        calls.append(schema) or reply(system, messages, schema))
    return calls


def test_llm_reads_uploads_to_tag_the_equipment(client, monkeypatch):
    from app import llm
    calls = fake_llm(monkeypatch, lambda *a: {"equipment_kinds": ["Blower", "Bogus"], "summary": "Belt drive care."})
    ex = login(client, "expert1")
    r = client.post("/api/kb/documents", files={"file": ("belts.md", b"Check the V-belt tension monthly.")},
                    data={"kind": "manual"}, headers=ex).json()
    assert r["equipment_kinds"] == ["Blower"] and r["tagged_by"] == "llm" and r["summary"] == "Belt drive care."
    assert calls == [llm.DOC_PROFILE_SCHEMA]  # one call per upload; unknown types are dropped

    r = client.post("/api/kb/documents", files={"file": ("belts2.md", b"Check the V-belt tension monthly.")},
                    data={"kind": "manual", "equipment_kind": "Pump"}, headers=ex).json()
    assert r["equipment_kinds"] == ["Pump"] and r["tagged_by"] == "uploader" and len(calls) == 1  # no call needed

    fake_llm(monkeypatch, lambda *a: None)  # LLM outage: keyword detection takes over
    r = client.post("/api/kb/documents", files={"file": ("chiller.md", b"Chiller dew point. Chiller defrost. Chiller trip.")},
                    data={"kind": "sop"}, headers=ex).json()
    assert r["equipment_kinds"] == ["Chiller"] and r["tagged_by"] == "keywords"


def test_llm_answers_from_the_passages_it_picks(client, monkeypatch):
    ex = login(client, "expert1")
    seen = {}

    def reply(system, messages, schema):
        seen["prompt"] = messages[0]["content"]
        return {"answer": "Keep dew point at 2-5 C per SOP-CHL-01.", "found": True, "sources": [2, 99, 2]}
    fake_llm(monkeypatch, reply)
    r = client.get("/api/kb/ask", params={"q": "dew point limit after the chiller"}, headers=ex).json()
    assert r["llm"] and r["found"] and r["answer"].startswith("Keep dew point")
    assert [h["cited"] for h in r["hits"]].count(True) == 1 and r["hits"][0]["cited"]  # made-up / repeated numbers ignored
    assert "[2]" in seen["prompt"] and "equipment:" in seen["prompt"]

    fake_llm(monkeypatch, lambda *a: None)  # outage: the search results alone
    r = client.get("/api/kb/ask", params={"q": "dew point limit after the chiller"}, headers=ex).json()
    assert r["answer"] is None and not r["llm"] and r["hits"]


def test_side_question_answer_cites_its_source(client, monkeypatch):
    from app import llm
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|D1|D1 RC Pump 1", symptoms=["leak"], severity="Low")

    def reply(system, messages, schema):
        if schema is llm.SIDE_SCHEMA:
            return {"reply": "Use Kluberplex BEM 41-132 on the coupling hub.", "sources": [1]}
        return None  # anything else falls back to the decision tree
    fake_llm(monkeypatch, reply)
    v = say(client, v["session"]["id"], "Which lubricant grade goes on the coupling hub?", h)
    assert any("Kluberplex BEM 41-132 on the coupling hub. (Source:" in (m.get("text") or "") for m in v["messages"])


def llm_check(**over):
    """A fishbone-stage LLM turn (BOT_SCHEMA) with the given fields replaced."""
    return {"reply": "No flush flow points to seal starvation.", "instruction": None, "purpose": None, "how": None,
            "quick_replies": [], "stage": "fishbone", "causes": [{"label": "Seal starvation", "likelihood": 0.6,
                                                                  "category": "Machine"}],
            "cited_cases": [], "direct_cause": None, "fishbone_category": None, "immediate_actions": None,
            "why_chain": [], "identified": False, "root_cause": None, "steps": None, "preventive_actions": None,
            "unidentified": False, "hazard_flags": [], **over}


def test_llm_directs_the_operator_and_offers_results_as_answers(client, monkeypatch):
    from app import llm
    monkeypatch.setattr(llm, "available", lambda: True)
    fake_llm(monkeypatch, lambda *a: llm_check(
        instruction="With the pump isolated under LOTO, look at the seal face: is it scored or chipped?",
        purpose="A worn face confirms seal damage.", how="Remove the seal guard and use a torch.",
        quick_replies=["Seal face scored", "Seal face looks fine", "I can't check this"]))
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|D1|D1 RC Pump 2", symptoms=["noise"])
    ask = next(m for m in reversed(v["messages"]) if m.get("replies"))
    assert ask["text"].endswith("is it scored or chipped?") and ask["purpose"] == "A worn face confirms seal damage."
    assert ask["replies"] == ["Seal face scored", "Seal face looks fine", HOW, CANT] and ask["multi"]


def test_llm_offering_actions_as_answers_falls_back_to_a_field_check(client, monkeypatch):
    from app import llm
    monkeypatch.setattr(llm, "available", lambda: True)
    fake_llm(monkeypatch, lambda *a: llm_check(quick_replies=["Inspect seal face for wear", "Measure discharge pressure"]))
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|BUU|Chiller Pump 1", symptoms=["noise"])
    ask = next(m for m in reversed(v["messages"]) if m.get("replies"))
    assert ask["text"].startswith("No flush flow points to seal starvation. Next:")
    assert not any(r.startswith(("Inspect", "Measure")) for r in ask["replies"]) and CANT in ask["replies"]
    assert ask["prompt"] and ask["multi"]  # a decision-tree check with its results as answers


def test_llm_outage_never_repeats_a_check_the_llm_already_asked(client, monkeypatch):
    fake_llm(monkeypatch, lambda *a: llm_check(
        instruction="With the pump stopped, open the bearing housing: what are the oil level and colour like?",
        quick_replies=["Level OK, oil clean", "Low, leaking at the oil seal", "Dark, burnt or milky"]))
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|BUU|Chiller Pump 2", symptoms=["noise"])
    sid = v["session"]["id"]
    fake_llm(monkeypatch, lambda *a: None)  # rate limited: the decision tree answers this turn
    v = say(client, sid, "Level OK, oil clean", h)
    ask = next(m for m in reversed(v["messages"]) if m.get("replies"))
    assert "Level OK, oil clean" not in ask["replies"], "the oil check is not asked twice"
    assert v["session"]["turns"] == 1


def test_llm_why_turn_without_a_why_question_falls_back_to_the_5_why(client, monkeypatch):
    fake_llm(monkeypatch, lambda *a: llm_check(
        stage="why", reply="Partial clog points to fibres reaching the pump.", direct_cause="Mechanical seal face damage",
        fishbone_category="Machine", immediate_actions=["Replace the seal"],
        quick_replies=["Yes, pressure improves temporarily", "No change"]))
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|BUU|Cooling Water Pump 1", symptoms=["leak"])
    ask = next(m for m in reversed(v["messages"]) if m.get("replies"))
    assert ask["why_step"] == 1 and ask["text"].rstrip().endswith("?") and SKIP_WHY in ask["replies"]
    assert "No change" not in ask["replies"] and v["phase"] == "why"


# ---------------------------------------------------------------------------
# Historic PIR / RCA reports
# ---------------------------------------------------------------------------

PIR_FORM = """Field | Details
Project Code | PS_BAR_ 01
Document Number | Ele/D/02/RC Pump-01
Failure Title | D-2 RC pump motor showing earth fault
Failure Date/Time | 17-08-2025, 9:30 AM
Failure Type (Mechanical/Electrical/Instrumentation/Civil) | Electrical
Incident Description | Motor not running; megger value low and showing earth fault with body.
What Went Wrong | Slurry ingress in motor through gearbox after the gland leaked.
Immediate Action Taken | Decoupled the faulty motor and resumed operation with spare motor.
Is it a Repeat Failure (Y/N) | No"""

RCA_REPORT = """Root Cause Analysis Report
Incident Title: CST 2 Hammer Mill mesh damaged
Unit: H2
Equipment: CST Hammer Mill
Date of Incident: 13/4/26
Problem Description:
During normal operation output flow was reduced and abnormal vibration was observed.
Immediate Action Taken:
Hammer Mill operation stopped immediately.
Root Cause Analysis:
Why 1: Why did the Hammer Mill stop functioning properly? ➡ Because the mesh was damaged.
Why 2: Why was the mesh damaged?
→ Because foreign material and stones came with the paddy feed.
Root Cause:
Risk Assessment (Before Corrective Action)
Permanent Corrective & Preventive Actions (CAPA)
Action Type | Description | Target Date | Status | Responsibility
Corrective | Mesh replaced and hammer mill restored | 13-04-2026 | Completed | Anil
Preventive | Install a magnet and stone trap ahead of the mill | 30-04-2026 | Open | Kailash
Horizontal Deployment | Same trap at all CST mills |  |  | """

PDF_PIR = """PREMINARY INFORMATION REPORT
FIELD DETAILS
PIR Number GPS/KKD/01/PIR/30
Incident Title PST-2 AGITATOR Cable connector burns
Incident Date/Time 26/05/2026 14:00
Incident group/Type Over load
What went wrong  The VFD shows alarm AL13 and agitator trip on overload
Immediate Action Taken ● Replaced the cable connectors"""


def test_reports_are_read_by_their_field_labels():
    from app import incidents
    p = incidents.parse(PIR_FORM, "PIR/PIR FY25-26/GPS_JIO_03/PS_BAR_01/D-2 RC pump.docx")
    assert (p["type"], p["project"], p["kind"], p["failure_type"]) == ("PIR", "PS_BAR_01", "Pump", "Electrical")
    assert p["title"] == "D-2 RC pump motor showing earth fault" and p["cause"].startswith("Slurry ingress")
    assert p["corrective"] == ["Decoupled the faulty motor and resumed operation with spare motor."]
    assert incidents.is_incident(p)

    r = incidents.parse(RCA_REPORT, "RCA/RCA FY26-27/PS_BAR_01/GPSR_JIO3_BB_RCA_012.docx")
    assert (r["type"], r["kind"], r["equipment"], r["project"]) == ("RCA", "Shredder", "CST Hammer Mill", "PS_BAR_01")
    assert r["why_chain"] == ["Why did the Hammer Mill stop functioning properly? Because the mesh was damaged",
                              "Why was the mesh damaged? Because foreign material and stones came with the paddy feed"]
    assert r["root_cause"] == "Because foreign material and stones came with the paddy feed"  # blank Root Cause: last why
    assert r["category"] == "Material" and r["corrective"] == ["Mesh replaced and hammer mill restored"]
    assert r["preventive"] == ["Install a magnet and stone trap ahead of the mill", "Same trap at all CST mills"]

    d = incidents.parse(PDF_PIR, "PIR/PIR FY26-27/GPS_KKD_01/PIR 30.pdf")
    assert d["title"] == "PST-2 AGITATOR Cable connector burns" and d["kind"] == "Agitator"
    assert d["project"] == "PS_KKD_01" and "AL13" in d["cause"] and d["date"].startswith("26/05/2026")


def _docx(text: str) -> bytes:
    """A minimal Word file: each line a paragraph, "a | b" lines a table row."""
    import io
    import zipfile
    from xml.sax.saxutils import escape
    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    para = lambda t: f"<w:p><w:r><w:t>{escape(t)}</w:t></w:r></w:p>"
    body = "".join(f"<w:tbl><w:tr>{''.join(f'<w:tc>{para(c)}</w:tc>' for c in l.split(' | '))}</w:tr></w:tbl>"
                   if " | " in l else para(l) for l in text.splitlines())
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", f'<?xml version="1.0"?><w:document {w}><w:body>{body}</w:body></w:document>')
    return buf.getvalue()


def test_historic_reports_in_nested_project_folders_feed_the_knowledge_base(client, tmp_path):
    import openpyxl
    from app import incidents
    site = tmp_path / "PIR" / "PIR FY25-26" / "GPS_JIO_03" / "PS_BAR_01"
    site.mkdir(parents=True)
    (site / "D-2 RC pump.docx").write_bytes(_docx(PIR_FORM))
    (site / "Copy of D-2 RC pump.docx").write_bytes(_docx(PIR_FORM))  # the same file filed twice
    rca = tmp_path / "RCA" / "RCA FY26-27" / "PS_BAR_01" / "April 2026"
    rca.mkdir(parents=True)
    (rca / "GPSR_JIO3_BB_RCA_012.docx").write_bytes(_docx(RCA_REPORT))
    wb = openpyxl.Workbook()
    for row in [("Report Title", "SHREDDER-1 POWER CABLE DAMAGED"), ("Discipline", "ELECTRICAL"),
                ("Why 1", "Why did the cable fail?", "Insulation degradation due to moisture ingress.", "Yes"),
                ("Why 2", "Why moisture ingress?", "Cable laid without a proper trench.", "Yes")]:
        wb.active.append(row)
    wb.save(rca / "SHREDDER-1 RCA.xlsx")
    admin = tmp_path / "PIR" / "PS_Jind_01" / "Store _Jind 1" / "Vendor Invoice"
    admin.mkdir(parents=True)
    (admin / "invoice.docx").write_bytes(_docx("Invoice | 12,000"))

    res = incidents.import_all(tmp_path)
    assert res["files"] == 4 and res["added"] == 3 and res["errors"] == 0  # the invoice is skipped, the copy once
    h = login(client, "expert1")
    cases = client.get("/api/kb/cases?q=hammer mill", headers=h).json()["items"]
    mill = next(c for c in cases if c["id"].startswith("RCA-"))
    assert mill["kinds"] == ["Shredder"] and mill["category"] == "Material" and len(mill["why_chain"]) == 2
    assert mill["project"] == "PS_BAR_01" and mill["source"].startswith("RCA report · PS_BAR_01")
    detail = client.get(f"/api/kb/cases/{mill['id']}", headers=h).json()
    assert detail["report"]["preventive"][0].startswith("Install a magnet") and detail["file"].endswith("RCA_012.docx")
    shredder = client.get("/api/kb/cases?q=SHREDDER-1 POWER CABLE", headers=h).json()["items"][0]
    assert shredder["why_chain"][1] == "Why moisture ingress? Cable laid without a proper trench"
    hits = client.get("/api/kb/search?q=slurry ingress motor gearbox earth fault", headers=h).json()
    assert any("D-2 RC pump" in x["title"] for x in (hits if isinstance(hits, list) else hits.get("items", [])))

    assert incidents.import_all(tmp_path)["added"] == 0  # unchanged files are not read again
    (site / "D-2 RC pump.docx").unlink()
    (site / "Copy of D-2 RC pump.docx").unlink()
    assert incidents.import_all(tmp_path)["removed"] == 1
    assert not client.get("/api/kb/cases?q=earth fault&source=pir", headers=h).json()["items"]


def test_files_shared_in_the_chat_and_only_the_operator_closes(client):
    h, ex = login(client, "operator1"), login(client, "expert1")
    v = report(client, h, equipment_id="GPS-BUU-04|D2|D2 Agitator 2", symptoms=["noise"])
    sid = v["session"]["id"]
    replies = last_replies(v)
    files = [("files", ("gearbox.jpg", b"\xff\xd8\xff fake jpeg", "image/jpeg")),
             ("files", ("readings.xlsx", b"PK fake workbook", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))]
    r = client.post(f"/api/sessions/{sid}/files", headers=h, files=files)
    assert r.status_code == 200, r.text
    v = r.json()
    up = next(m for m in reversed(v["messages"]) if m["type"] == "user")
    assert [f["filename"] for f in up["attachments"]] == ["gearbox.jpg", "readings.xlsx"]
    assert v["session"]["turns"] == 0 and last_replies(v) == replies, "files alone don't answer the pending check"
    got = client.get(f"/api/sessions/{sid}/files/{up['attachments'][0]['id']}", headers=ex)
    assert got.status_code == 200 and got.content == b"\xff\xd8\xff fake jpeg"
    r = client.post(f"/api/sessions/{sid}/files", headers=h, data={"text": "Photo of the gearbox"},
                    files=[("files", ("note.pdf", b"%PDF-1.4 fake", "application/pdf"))])
    sent = next(m for m in reversed(r.json()["messages"]) if m["type"] == "user")
    assert sent["text"] == "Photo of the gearbox" and sent["attachments"][0]["filename"] == "note.pdf"
    assert r.json()["messages"][-1]["type"] == "agent", "a message with files gets a reply like any other"
    assert client.post(f"/api/sessions/{sid}/resolve", headers=ex).status_code == 403
    v = client.post(f"/api/sessions/{sid}/resolve", headers=h, json={"note": "Loose guard bolt tightened"}).json()
    assert v["session"]["status"] == "closed" and v["session"]["root_cause"] == "Loose guard bolt tightened"
    assert client.post(f"/api/sessions/{sid}/files", headers=h,
                       files=[("files", ("x.png", b"x", "image/png"))]).status_code == 409


def test_history_lists_the_project(client):
    h = login(client, "operator1")
    rows = client.get("/api/sessions?project_id=1", headers=h).json()
    assert rows and all(r["project_id"] == 1 and r["project"] for r in rows)


@pytest.fixture
def survey_on(monkeypatch):
    monkeypatch.setattr(config, "SURVEY_SIZE", 4)


def test_condition_survey_asks_checks_together_and_updates_the_fishbone(client, survey_on):
    from app.brain import tree_for
    from app.diagnosis import pick_survey
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|D2|D2 Agitator 1", symptoms=["vibration", "noise"],
               severity="High", description="Grinding noise from the gearbox")
    sid = v["session"]["id"]
    sv = next(m for m in v["messages"] if m["type"] == "survey")
    assert 2 <= len(sv["questions"]) <= 4 and v["survey"] == [q["id"] for q in sv["questions"]]
    assert len({q["id"] for q in sv["questions"]}) == len(sv["questions"])
    assert not last_replies(v), "no single check is asked while the condition survey is open"
    # free text while the survey is open is answered, and the survey stays open
    v = say(client, sid, "It started after the night shift", h)
    assert v["survey"] and v["session"]["turns"] == 0
    tree = tree_for("Agitator")
    first = sv["questions"][0]
    answers = {first["id"]: first["options"][:2]}
    r = client.post(f"/api/sessions/{sid}/survey", headers=h,
                    json={"answers": answers, "skipped": [sv["questions"][1]["id"]]})
    assert r.status_code == 200, r.text
    v = r.json()
    assert v["survey"] is None and v["checks"] == 1 and v["session"]["turns"] == 1
    up = next(m for m in reversed(v["messages"]) if m["type"] == "user")
    assert up["survey"][0]["a"] == "; ".join(first["options"][:2]) and up["survey"][1]["a"] == CANT
    fbs = [m for m in v["messages"] if m["type"] == "fishbone"]
    assert len(fbs) == 2 and fbs[-1]["updated"] == "after 1 check" and fbs[-1]["bones"] != fbs[0]["bones"]
    # the checks left blank are still available as follow-ups; answered and skipped ones never come back
    asked = [q for q in tree["questions"] if q["id"] in (first["id"], sv["questions"][1]["id"])]
    nxt = next(m for m in reversed(v["messages"]) if m.get("replies"))
    assert nxt["prompt"] not in [q["text"] for q in asked]
    assert client.post(f"/api/sessions/{sid}/survey", headers=h, json={"answers": answers}).status_code == 409
    # the set is picked jointly: never two copies of the same check, and it beats asking the top check alone
    post = {c["id"]: 1 / len(tree["causes"]) for c in tree["causes"]}
    assert len(pick_survey(tree, post, [], "", 4)) >= 2


def test_condition_survey_can_be_declined(client, survey_on):
    h = login(client, "operator1")
    v = report(client, h, equipment_id="GPS-BUU-04|D2|D2 Agitator 2", symptoms=["noise"])
    sid = v["session"]["id"]
    v = client.post(f"/api/sessions/{sid}/survey", headers=h, json={}).json()
    assert v["survey"] is None and v["checks"] == 0 and last_replies(v), "back to one check at a time"
    assert v["messages"][-2]["text"] == "Ask me one check at a time"
