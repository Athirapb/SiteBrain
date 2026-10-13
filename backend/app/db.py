"""PostgreSQL persistence. Every operational table is partitioned by site_code (SRS §6 tenant isolation).

Queries elsewhere in the app are written with `?` placeholders; `_sql()` translates them to psycopg's
`%s` style, so call sites stay short. Structured columns are JSONB; timestamps are ISO-8601 UTC text.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Iterable

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from .config import DATABASE_URL, DB_POOL_MAX

log = logging.getLogger("sitebrain.db")
_pool: ConnectionPool | None = None

# Tables whose primary key is a generated integer `id` (insert() returns it)
SERIAL_TABLES = {"users", "areas", "attachments", "messages", "interlocks", "overrides", "documents", "chunks", "outbox", "audit_log"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS sites (
    code TEXT PRIMARY KEY,
    sort_order SERIAL,
    name TEXT NOT NULL,
    project_code TEXT NOT NULL,
    location TEXT,
    commissioned TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL,              -- field_operator | expert
    title TEXT,
    site_code TEXT REFERENCES sites(code),  -- NULL = fleet-wide access
    token TEXT UNIQUE
);

-- Plant areas (units) and their equipment, maintained from the Plant Setup screen
CREATE TABLE IF NOT EXISTS areas (
    id SERIAL PRIMARY KEY,
    site_code TEXT NOT NULL REFERENCES sites(code),
    code TEXT NOT NULL,              -- short code, e.g. BUU, D1
    name TEXT NOT NULL,
    description TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (site_code, code)
);

CREATE TABLE IF NOT EXISTS equipment (
    id TEXT PRIMARY KEY,             -- site|area|name at creation; never changes on edit
    site_code TEXT NOT NULL REFERENCES sites(code),
    area_id INTEGER NOT NULL REFERENCES areas(id),
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    tag TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_equipment_site ON equipment(site_code);
CREATE INDEX IF NOT EXISTS ix_equipment_area ON equipment(area_id);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    site_code TEXT NOT NULL,
    area_id INTEGER NOT NULL REFERENCES areas(id),
    equipment_id TEXT REFERENCES equipment(id),  -- NULL until an area-level report is localized
    user_id INTEGER,
    report JSONB NOT NULL DEFAULT '{}',  -- {symptoms, severity, description, reported_by, reported_at}
    status TEXT NOT NULL,            -- active | escalated | resolved | closed
    mode TEXT NOT NULL,              -- bot | expert
    engine TEXT NOT NULL,            -- rules | llm
    turns INTEGER NOT NULL DEFAULT 0,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
    causes JSONB NOT NULL DEFAULT '[]',
    cited JSONB NOT NULL DEFAULT '[]',
    state JSONB NOT NULL DEFAULT '{}',
    identified INTEGER NOT NULL DEFAULT 0,
    symptom TEXT,
    root_cause TEXT,
    steps JSONB,
    resolved_by TEXT,
    severity TEXT NOT NULL DEFAULT 'Low',
    pending_signoff INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    identified_at TEXT,
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_sessions_site ON sessions(site_code, created_at);
CREATE INDEX IF NOT EXISTS ix_sessions_eq ON sessions(equipment_id, status);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    type TEXT NOT NULL,              -- user | agent | analysis | solution | offer | event | signoff
    payload JSONB NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_messages_session ON messages(session_id, id);

CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    site_code TEXT,
    kinds JSONB NOT NULL,
    keys JSONB NOT NULL,
    title TEXT NOT NULL,
    cause TEXT NOT NULL,
    fix TEXT NOT NULL,
    source TEXT NOT NULL,
    session_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS escalations (
    ticket TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    site_code TEXT NOT NULL,
    area_id INTEGER NOT NULL REFERENCES areas(id),
    equipment_id TEXT REFERENCES equipment(id),
    urgency TEXT NOT NULL,
    summary TEXT NOT NULL,
    trigger_reason TEXT NOT NULL,
    expert_name TEXT NOT NULL,
    expert_role TEXT NOT NULL,
    claimed_by INTEGER,
    status TEXT NOT NULL,            -- Active | In Progress | Resolved
    turns INTEGER NOT NULL DEFAULT 0,
    payload JSONB NOT NULL DEFAULT '{}',
    compile_ms INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    first_response_at TEXT,
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_escalations_site ON escalations(site_code, created_at);

CREATE TABLE IF NOT EXISTS interlocks (
    id SERIAL PRIMARY KEY,
    site_code TEXT NOT NULL,
    area_id INTEGER NOT NULL REFERENCES areas(id),
    equipment_id TEXT REFERENCES equipment(id),  -- NULL for an area-wide hazard (e.g. gas smell in the area)
    target_equipment_id TEXT,
    session_id TEXT,
    rule_id TEXT NOT NULL,
    category TEXT NOT NULL,          -- interlock | advisory
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,            -- engaged | acknowledged | released
    acknowledged_by TEXT,
    acknowledged_at TEXT,
    released_by TEXT,
    released_at TEXT,
    prevented_damage INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_interlocks_site ON interlocks(site_code, created_at);
CREATE INDEX IF NOT EXISTS ix_interlocks_eq ON interlocks(equipment_id, status);

CREATE TABLE IF NOT EXISTS overrides (
    id SERIAL PRIMARY KEY,
    site_code TEXT NOT NULL,
    interlock_id INTEGER NOT NULL REFERENCES interlocks(id),
    equipment_id TEXT,
    requested_by TEXT NOT NULL,
    reason TEXT NOT NULL,
    guard_active INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,            -- pending | approved | rejected | blocked
    decided_by TEXT,
    decided_at TEXT,
    decision_note TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    kind TEXT NOT NULL,              -- manual | sop | log | checksheet
    filename TEXT,
    site_code TEXT,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    uploaded_by TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    doc_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outbox (
    id SERIAL PRIMARY KEY,
    ticket TEXT,
    channel TEXT NOT NULL,           -- email | sms | teams | eam
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL,            -- queued | sent | failed | logged
    created_at TEXT NOT NULL
);

-- Immutable, append-only audit trail (SRS §6 cold-store compliance)
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    ts TEXT NOT NULL,
    site_code TEXT,
    actor TEXT NOT NULL,
    role TEXT NOT NULL,
    action TEXT NOT NULL,
    entity TEXT,
    detail JSONB NOT NULL DEFAULT '{}'
);
CREATE OR REPLACE FUNCTION audit_log_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS audit_log_no_change ON audit_log;
CREATE TRIGGER audit_log_no_change BEFORE UPDATE OR DELETE OR TRUNCATE ON audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION audit_log_append_only();

-- Knowledge brain (additive, so existing databases upgrade in place)
ALTER TABLE cases ADD COLUMN IF NOT EXISTS why_chain JSONB NOT NULL DEFAULT '[]';
ALTER TABLE cases ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS prevent TEXT;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS equipment TEXT;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS doc_id INTEGER;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS checksum TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS equipment_kinds JSONB;  -- equipment types it covers; [] = general
ALTER TABLE documents ADD COLUMN IF NOT EXISTS tagged_by TEXT;      -- uploader | llm | keywords
ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary TEXT;        -- one line, written by the LLM
ALTER TABLE cases ADD COLUMN IF NOT EXISTS project TEXT;            -- historic PIR / RCA reports (app/incidents.py)
ALTER TABLE cases ADD COLUMN IF NOT EXISTS occurred TEXT;           -- failure date as the report gives it
ALTER TABLE cases ADD COLUMN IF NOT EXISTS report JSONB;            -- every field parsed from the report
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding BYTEA;       -- float32 unit vector (app/embeddings.py)
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embed_model TEXT;      -- model that produced it; re-embedded on change

-- Projects an issue is raised against (company project register; seed.PROJECTS)
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    op_id INTEGER,                   -- NULL when the project has no operations id
    code TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Files the field operator attaches when escalating or in the chat (photos, videos, reports, spreadsheets)
CREATE TABLE IF NOT EXISTS attachments (
    id SERIAL PRIMARY KEY,
    ticket TEXT NOT NULL REFERENCES escalations(ticket),
    session_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size INTEGER NOT NULL,
    data BYTEA NOT NULL,
    uploaded_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_attachments_ticket ON attachments(ticket);
-- files shared in the copilot chat belong to the session; they get the ticket if the issue is escalated
ALTER TABLE attachments ALTER COLUMN ticket DROP NOT NULL;
CREATE INDEX IF NOT EXISTS ix_attachments_session ON attachments(session_id);

CREATE TABLE IF NOT EXISTS counters (
    name TEXT PRIMARY KEY,
    value INTEGER NOT NULL
);
"""

# `readings` is the retired shift-checksheet table; it stays here so a reset drops it from older databases.
ALL_TABLES = ["attachments", "projects", "audit_log", "outbox", "chunks", "documents", "overrides", "interlocks", "escalations", "cases",
              "messages", "sessions", "readings", "equipment", "areas", "users", "sites", "counters"]

# Bump when SCHEMA changes incompatibly; seed() rebuilds a database created by an older version.
SCHEMA_VERSION = 2


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=DB_POOL_MAX, open=True, timeout=30,
                               kwargs={"autocommit": True, "row_factory": dict_row})
    return _pool


def close() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def _sql(sql: str) -> str:
    return sql.replace("%", "%%").replace("?", "%s")


def _param(v: Any) -> Any:
    return Jsonb(v) if isinstance(v, (dict, list)) else v


def init_schema() -> None:
    with pool().connection() as c:
        c.execute(SCHEMA)


def schema_version() -> int | None:
    """Version stamped in `counters`; None for an empty database, 1 for one that predates versioning."""
    with pool().connection() as c:
        if not c.execute("SELECT to_regclass('sites') AS t").fetchone()["t"]:
            return None
        if not c.execute("SELECT to_regclass('counters') AS t").fetchone()["t"]:
            return 1
        row = c.execute("SELECT value FROM counters WHERE name='schema_version'").fetchone()
        return row["value"] if row else 1


def drop_all() -> None:
    with pool().connection() as c:
        c.execute("DROP TABLE IF EXISTS " + ", ".join(ALL_TABLES) + " CASCADE")


def q(sql: str, params: Iterable[Any] = ()) -> list[dict]:
    with pool().connection() as c:
        return c.execute(_sql(sql), tuple(params)).fetchall()


def q1(sql: str, params: Iterable[Any] = ()) -> dict | None:
    with pool().connection() as c:
        return c.execute(_sql(sql), tuple(params)).fetchone()


def ex(sql: str, params: Iterable[Any] = ()) -> None:
    with pool().connection() as c:
        c.execute(_sql(sql), tuple(_param(p) for p in params))


def executemany(sql: str, rows: list[tuple]) -> None:
    """Bulk insert in one transaction (used by the seeder)."""
    with pool().connection() as c, c.transaction(), c.cursor() as cur:
        cur.executemany(_sql(sql), [tuple(_param(v) for v in r) for r in rows])


def insert(table: str, row: dict) -> Any:
    """Insert a row; returns the generated id for SERIAL tables, else None."""
    cols = list(row.keys())
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(['%s'] * len(cols))})"
    if table in SERIAL_TABLES:
        sql += " RETURNING id"
    with pool().connection() as c:
        cur = c.execute(sql, tuple(_param(v) for v in row.values()))
        return cur.fetchone()["id"] if table in SERIAL_TABLES else None


def update(table: str, key: str, key_val: Any, row: dict) -> None:
    sets = ",".join(f"{k}=%s" for k in row)
    with pool().connection() as c:
        c.execute(f"UPDATE {table} SET {sets} WHERE {key}=%s", tuple(_param(v) for v in row.values()) + (key_val,))


def next_counter(name: str, start: int) -> int:
    """Atomic sequence for human-readable ids (S-2425, ESC-BUU-175, KB-0809)."""
    with pool().connection() as c:
        return c.execute("INSERT INTO counters (name, value) VALUES (%s, %s) ON CONFLICT (name) "
                         "DO UPDATE SET value = counters.value + 1 RETURNING value", (name, start)).fetchone()["value"]


def set_counter(name: str, value: int) -> None:
    with pool().connection() as c:
        c.execute("INSERT INTO counters (name, value) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET value = EXCLUDED.value",
                  (name, value))


def loads(v: Any, default: Any = None) -> Any:
    """JSONB columns arrive already decoded; this also tolerates JSON text."""
    if v is None:
        return default
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except (TypeError, ValueError):
        return default


def audit(actor: str, role: str, action: str, entity: str | None = None,
          detail: dict | None = None, site_code: str | None = None) -> None:
    insert("audit_log", {"ts": now_iso(), "site_code": site_code, "actor": actor, "role": role,
                         "action": action, "entity": entity, "detail": detail or {}})
