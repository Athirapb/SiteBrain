# SiteBrain AI — BUU Operations Copilot

SiteBrain is a conversational operations and technical-escalation copilot for Biogas Upgradation Unit (BUU) plants. Here is what a field technician gets:

- **Issue reporting.** The technician reports an issue against an equipment, or against an area when they don't know which equipment it is. The report has symptoms, a severity and a description.
- **Root cause analysis, the standard way.** For an area-level report, the copilot first works out which equipment it is. A **fishbone (Ishikawa, 6M)** of possible direct causes is then narrowed by field checks. Once the direct cause is confirmed, a **5-Why** drill-down finds the systemic root cause. The result is an RCA summary: why chain, 6M category, corrective and preventive actions.
- **Present condition first.** Before narrowing down, SiteBrain asks a set of field checks together in one form (4 by default, `SITEBRAIN_SURVEY`; 0 = one at a time). The set is chosen for the most information as a whole, so it covers different bones of the fishbone. All answers update the fishbone at once. Targeted one-at-a-time checks follow until one cause reaches the confidence threshold. The newest fishbone card in the chat updates live as answers come in.
- **Talks like a colleague.** Each check says why it's being asked. The technician can tap *How do I check this?* or *I can't check this*, or answer in their own words. Each answer is acknowledged with what it rules out or points to.
- **Safety interlocks.** Hazards in the report or the answers raise interlocks and advisories. They are recorded for the control room and shown beside the chat, but they never hold up the troubleshooting (there is no sign-off step).
- **Short, chat-sized messages.** Every SiteBrain message is at most three short sentences, like a WhatsApp message from a colleague. The LLM is told to write that way, and `crisp()` trims anything longer while keeping the question or step being asked. Why a check matters folds away behind *Why?*. Experts' own messages are never trimmed.
- **Answer by voice.** Next to the answers there is *Say it* (and *Say your answer* on a condition check). Tap, speak, and the recording is transcribed (any language) and matched to the options on screen by `match_spoken()`: "the first one", "about 90 degrees" (the range it falls in), "dark with metal fines and the level is low" (several on a multi-answer check), "I can't check it", "done", with the LLM as a last resort. A single-answer question is answered straight away; on a multi-answer check or a condition check the matches are ticked for you to confirm. On the report form, a voice note also ticks the symptoms it mentions.
- **Voice notes, photos and videos are read.** While SiteBrain is troubleshooting, every attachment is read (`media.py`, on the Groq key, free tier). Voice notes are transcribed by Whisper in any language, with an English version for the engine. A voice note in the chat counts as the operator's words, and one on the report form is written into the description. Photos are described by a vision model, which also says which answer of the pending check they show. A clear match answers it in the chat, or pre-selects it on a condition check; an unclear one is only a hint. Videos give a tiled strip of frames plus their soundtrack. PDFs, spreadsheets and CSV logs are summarised. What was heard or seen is shown under each file, goes to the LLM, and reaches the expert's package. Once the issue is escalated, files go to the expert as they are, unread. `SITEBRAIN_MEDIA=off` only stores them.
- **Files in the chat.** The field operator (or the expert) can attach photos, videos, PDFs, spreadsheets and documents to any message: up to 5 files of 10 MB each, by the paperclip, drag and drop or paste. If the issue is escalated later, the files go to the expert's ticket too.
- **Resolve & close.** Only the field operator can mark an issue resolved and close it. They confirm first, because closing ends the chat. A confirmed root cause is saved to the knowledge base. Without one, the issue is logged as closed, with an optional note on how it was settled.
- **Expert escalation.** Escalation to an L2/L3 expert happens only when the field operator taps *Escalate To Expert*. They add a description and up to 5 attachments (photos, videos, documents; 10 MB each) for the expert's analysis. SiteBrain never escalates on its own; when it can't reach a confident answer it recommends escalating. The full context goes with the escalation: the operator's description and files, the issue report, the transcript, the diagnostic matrix and a 30-minute SCADA snapshot.

It is built from the SRS/PRD *SiteBrain AI — BUU Operations Copilot V3.0* and the generated UI prototype. The **LLF Checksheet** workbook seeds the plant's areas and equipment. After that, they are maintained in **Plant Setup**.

```
SiteBrain/
├── backend/    FastAPI + PostgreSQL + LLM: Groq / Ollama / Claude (Python)
├── frontend/   React + Vite (GPS Renewables web design system)
├── docker-compose.yml   PostgreSQL 16 (host port 5433)
└── run.sh      one-command start
```

## Quick start

Requirements: Python 3.10+, Node 18+, and PostgreSQL 14+ (Docker is easiest).

```bash
./run.sh          # installs deps, builds the UI, serves everything on http://localhost:8000
./run.sh dev      # backend :8000 + hot-reloading UI on http://localhost:5173
```

Or run each part by hand:

```bash
docker compose up -d db                              # PostgreSQL on localhost:5433 (or point DATABASE_URL at your own server)

cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8000          # creates tables + seeds demo data on first start

cd frontend && npm install && npm run dev           # http://localhost:5173 (proxies /api → :8000)
```

To reset the demo data, run `cd backend && .venv/bin/python -m app.seed --reset` (drops and recreates all SiteBrain tables). A v2 database is migrated in place on startup (email sign-in, PST area), keeping its issues, cases and documents; older ones are rebuilt.

### Database

The backend uses **PostgreSQL** via `psycopg` 3 with a connection pool. Set the connection in `backend/.env`:

```env
DATABASE_URL=postgresql://sitebrain:sitebrain@localhost:5433/sitebrain
```

The default matches `docker-compose.yml`. To use an existing server instead, create a database (`createdb sitebrain`) and change `DATABASE_URL`. The app creates its tables on startup and seeds them if empty. Structured fields (issue reports, diagnostic state, chat payloads, escalation packages) are `JSONB` columns. A trigger makes `audit_log` reject `UPDATE`, `DELETE` and `TRUNCATE`.

### Language model (optional)

Copy `backend/.env.example` to `backend/.env` and configure one provider. `SITEBRAIN_LLM_PROVIDER=auto` picks the first one that has a key.

| Provider | Cost | Setting |
|---|---|---|
| **Groq** | Free tier (GPT-OSS: 30 requests/min, 1,000/day, 8K tokens/min) | `GROQ_API_KEY` from console.groq.com; default model `openai/gpt-oss-120b` |
| **Ollama** (local) | Free, runs on your machine | `SITEBRAIN_LLM_PROVIDER=openai_compat`, `OPENAI_COMPAT_MODEL=llama3.1:8b` |
| **Anthropic Claude** | Paid API | `ANTHROPIC_API_KEY`; model `claude-opus-5-5` with server-side refusal fallback |

All providers return JSON constrained to the same schema. Without any provider, or when a call fails (for example a Groq rate limit), the deterministic decision-tree engine answers that turn and the LLM is retried on the next one. That engine is the SRS §8 hackathon MVP, so every feature works offline.

The LLM never makes safety decisions. Interlocks, turn limits and escalation triggers are deterministic code in every mode.

## Knowledge brain

What the copilot knows lives in `backend/app/brain/`, one module per equipment group, written in a small DSL (`dsl.py`):

| Knowledge | Where | What it holds |
|---|---|---|
| Fishbone + field checks + 5-Why trees | `TREES` in `pumps.py`, `agitation.py`, `feeding.py`, `separation.py`, `gas_movers.py`, `hwg.py`, `gas_cleaning.py` | 13 equipment types · 95 direct causes on the 6M bones · 131 field checks (each with *how* and *why it matters*) · 325 systemic root causes with preventive actions |
| General maintenance knowledge | `MAINTENANCE` | PM schedule, failure modes and operating limits per equipment type |
| Site operating conditions | `CONDITIONS` | Normal envelope per area (digesters, feed hall, SLS, CDT, HWG, BUU compression, BUU gas cleaning): parameter, normal range, why it matters, what to do |
| RCA of previous problems | `CASES` | Curated cases with why chains, category and prevention |
| Incident reports, SOPs, OEM manuals, RCA guides | `backend/data/docs/` | Incident logs (CSV with why chain, category and preventive action columns) become cases; documents are BM25-indexed for search and the LLM |

`knowledge.train()` runs at every start (and from *Retrain Knowledge Brain* in the Knowledge Base). It upserts the case library and re-indexes changed documents. `python -m app.brain.check` is the quality gate: it validates the structure and simulates a technician for every direct cause, so each cause must be confirmable within the 5-check limit.

**Learning from resolved sessions** (`learning.py`). Every session marked resolved (the fix worked) is a labelled example: the confirmed direct cause and the answer given to each field check. SiteBrain uses these to update, per equipment type, how common each cause is and P(answer | cause) for every check. The update is Bayesian, with the engineers' authored likelihoods as the prior, worth `SITEBRAIN_LEARN_STRENGTH` sessions (default 10). With no data the trees behave exactly as authored. The authored files are never edited: the adjustment is applied on top and refitted at start-up, on *Retrain*, and after every resolve. *Knowledge Base → Troubleshooting Library* shows what has been learned for each type. Set `SITEBRAIN_LEARNING=false` to switch it off. Learning can only sharpen causes that already exist in the brain; engineers still add new ones.

The numeric ranges come from published literature and OEM practice, not this plant's design data. A process engineer should confirm them against the nameplates and commissioning records.

## Users and sign-in

Everyone signs in with **email and password**. Nobody is seeded except the **administrator**, set in `backend/.env`:

```env
SITEBRAIN_ADMIN_EMAIL=you@gpsrenewables.com
SITEBRAIN_ADMIN_NAME=Your Name
SITEBRAIN_ADMIN_PASSWORD=...     # 8+ characters; applied on every start, so change it here and restart
```

The administrator adds the field operators and experts and **sets their passwords** (typed or generated, then passed on to the person). *Set Password* gives someone a new one and signs them out. Passwords are stored as scrypt hashes. The sign-in page works like the GPS LLF app: pick **Field Operator** or **Technical Expert**, then enter email and password (the *Administrator sign in* link is below the cards). Each account signs in only through its own card.

| Role | Who | Sections |
|---|---|---|
| Field Operator | Shift In-Charge, Mechanical / E&I Engineers, Plant Manager | Report An Issue · My Past Issues · Knowledge Base |
| Technical Expert | Central O&M team, Design Engineers (one plant, or all plants) | Issues Queue · My Past Resolutions · Knowledge Base |
| Administrator | From `SITEBRAIN_ADMIN_EMAIL` / `SITEBRAIN_ADMIN_PASSWORD` | Users: add with a password, edit, set a new password, switch off, delete (only without history) |

The administrator sets each user's plant, designation, usual project and usual area. The project and area are filled in on that user's issue reports.

## Demo script

1. **Set up.** Sign in as the administrator and add a field operator (plant *LLF Biogas Plant*, usual area *Digester 2*) and an expert (all plants), giving each a password.
2. **Report.** Sign in as the field operator. *Report An Issue* opens with the project and area filled in. Pick **D2 Agitator 3**, *Abnormal noise*, and attach a photo or record a voice note. Press *Start Troubleshooting*.
3. **Quick analysis.** SiteBrain lists the possible causes, most likely first, then asks four checks one at a time (*Check 1 of 4*). Answers are blue chips; Next / Send are green buttons. Each check can take a photo, video or voice note. *Similar Past Cases* sits at the bottom right.
4. **Detailed analysis and resolution.** SiteBrain asks why it happened until it reaches the root cause, then walks through the fix one step at a time, with the safety note on the steps that need it. *Yes, it's working* resolves and closes the issue and saves it to the Knowledge Base.
5. **Expert help.** When SiteBrain can't get to a confident answer it says *I'd recommend bringing in a technical expert…* with **Escalate to Technical Expert** or **Will try to resolve myself**. The ⋮ menu also has *Get expert help* and *It's fixed — close the issue* at any time. Escalating emails the experts (the outbox when SMTP is not configured); it is not a live chat.
6. **Expert.** Sign in as the expert. The *Issues Queue* shows new issues and those waiting for a reply. The issue opens with the chat in the middle and an **Issue Summary** on the right (reported issue, findings so far, every photo/video/file, similar cases) plus **Plant Live Data** (simulated in this version). A reply emails the reporter, whose *My Past Issues* marks it *Expert replied*. *Share Resolution* sends the confirmed cause and fix steps.

The control room, dashboards and plant setup APIs are still in the backend, but they are not in the navigation of any role.

## How the SRS maps to the build

| SRS | Implementation |
|---|---|
| §1 Knowledge base engine | `knowledge.py`: KB cases with similarity matching, BM25 retrieval over ingested PDFs/SOPs/CSV logs/XLSX |
| §1 Asset topology | `topology.py`: rule-based P&ID dependency lookup (Digesters → H2S Scrubber → Filter Skid → Blowers → LP Compressors → Chiller → Membrane → HP → CBG) |
| §1 / §5 Safety interlock engine | `safety.py`: the §5 matrix (SCR-01, FLT-01, CMP-01, CHL-01, MEM-01), plus LOTO, gas, oil-startup and seal rules. Hazards come from the issue report (for example a gas smell, or Critical vibration on rotating equipment) and from field-check answers. Mandatory chat sign-off; bypass blocked while the secondary guard filter is reported inactive |
| §2 Role views + RBAC | `auth.py`: two roles — field operator and L2/L3 expert (who also holds the control-room approvals, so a bypass is never approved by the person requesting it); role-specific navigation; site-bound users isolated by `site_code` |
| §3 State machine | `diagnosis.py`: issue report → localize to an equipment (area-level reports) → fishbone field checks (Bayesian over the knowledge brain, or the LLM following the same method) → finding (direct cause + immediate actions) → 5-Why → RCA summary (corrective + preventive) / L2-L3 escalation. If the LLM drops out mid-why, the decision tree carries on |
| §4.2 Escalation triggers | Recommend escalating (the field operator decides): more than 5 turns without >85% confidence · SCADA contradiction · critical safety risk (particles toward compressors) · no matching cause · issue cannot be localized to an equipment |
| §4.2 Payload format | `escalation.py`: `escalation_metadata`, `diagnostic_summary` (with the issue report), `telemetry_window_30min`, `escalation_target`, plus the transcript and safety state |
| Plant configuration | `routers/setup.py` + Plant Setup view: areas and equipment per site (create, edit, deactivate, delete when there is no history) |
| §6 Data handling | Tenant isolation by `site_code`/`project_code`; batch document ingestion; append-only `audit_log` (a PostgreSQL trigger rejects UPDATE/DELETE/TRUNCATE). Plant Setup changes are audited |
| §7 Dashboards | `analytics.py`. Daily: MTTD/MTTR, anomaly matrix, equipment health from open issues, issues reported by shift, interlock log. Weekly: Pareto, escalation rate, MTTE, SOP compliance. Monthly: uptime, incidents avoided, FCR trend, KB growth |
| §8 MVP escalation output | Email/SMS digest and EAM record written to the outbox. A real MS Teams webhook and SMTP are used when configured |
| §9 Context preservation | One session record holds every answer; the expert sees the same chat and the compiled package |

## Data notes

- **Areas and equipment.** The seed parses all 111 equipment items from `backend/data/LLF_Checksheet.xlsx`, one area per sheet (BUU, D1–D4, HWG, SLS, FEED, CDT), with the *CDT & PST* sheet split into Primary Sludge Tank (the `PST …` equipment) and Concentrated Digestate Tank. Areas are listed in process order: FEED, PST, D1–D4, HWG, CDT, SLS, BUU. The workbook is used only for this inventory; its checkpoints are not used. The §5 process skids the workbook doesn't list (H₂S Scrubber Vessel, Gas Filtration Skid, Membrane Upgrader) are added to the BUU. That makes 114 equipment per site. Edit them in Plant Setup.
- **Sites.** There are three sites: the LLF plant plus two demo sites for the fleet view.
- **Simulated data.** SCADA telemetry is **simulated** (`telemetry.py`). There is no live MQTT/OPC-UA feed in the MVP, so values follow the open issue on the equipment (reported symptoms, severity and hazards found during diagnosis). Without an open issue they stay at baseline. Session history older than today is **synthetic**, generated deterministically so that the weekly and monthly dashboards have trends.
- **Seed documents.** The SOP, OEM, RCA-guide and incident-log documents in `backend/data/docs` were researched and written for this demo; they are not the plant's own records. They are indexed on start.

## Tests

```bash
cd backend && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/python -m pytest -q
```

Tests run against `TEST_DATABASE_URL` (default: the `sitebrain_test` database the compose file creates). That database is wiped on every run.

The tests cover the xlsx inventory import, report-driven safety rules, RBAC, sign-off gating through to resolution, area-level localization (by answer, by description and the escalation when it fails), contradiction escalation and the payload, the turn-limit escalation, the unsafe-bypass block, Plant Setup CRUD rules, the append-only audit log, and the dashboards.

## API

Interactive docs are at `http://localhost:8000/docs`. Main routes:

- `/api/areas`, `/api/equipment` (GET for everyone; POST/PUT/DELETE need the `config` permission)
- `/api/sessions` (POST reports an issue: `area_id` and/or `equipment_id`, `symptoms`, `severity`, `description`), `/api/sessions/*` (messages, signoff, escalate as multipart `description` + `files`, resolve)
- `/api/escalations/*` (including `/api/escalations/{ticket}/attachments/{id}`)
- `/api/control/*` (interlocks, overrides)
- `/api/kb/*` (cases, troubleshooting library, operating conditions, brain stats, `POST /api/kb/train`, documents, search)
- `/api/analytics/{daily|weekly|monthly}`
- `/api/audit`
