"""Runtime configuration, read from environment variables (or backend/.env)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def _load_dotenv() -> None:
    env = BASE_DIR / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if v[:1] in ('"', "'") and v[1:].find(v[0]) >= 0:
            v = v[1:1 + v[1:].find(v[0])]  # quoted value: keep everything inside the quotes
        else:
            v = v.split(" #", 1)[0].split("\t#", 1)[0].strip()  # drop inline comment
        os.environ.setdefault(k.strip(), v)


_load_dotenv()

# PostgreSQL connection string, e.g. postgresql://user:password@host:5432/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sitebrain:sitebrain@localhost:5433/sitebrain")
DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))
CHECKSHEET_XLSX = Path(os.getenv("SITEBRAIN_CHECKSHEET", str(DATA_DIR / "LLF_Checksheet.xlsx")))
UPLOAD_DIR = DATA_DIR / "uploads"
# Historic PIR / RCA reports, in project folders nested to any depth (app/incidents.py). "off" disables the import.
_INCIDENTS = os.getenv("SITEBRAIN_INCIDENTS_DIR", str(BASE_DIR.parent / "data"))
INCIDENTS_DIR = None if _INCIDENTS.lower() == "off" else Path(_INCIDENTS)

# LLM: when no provider is configured the deterministic decision-tree engine runs alone.
LLM_ENABLED = os.getenv("SITEBRAIN_LLM", "auto").lower()  # auto | on | off
# anthropic | groq | openai_compat | auto (auto = first provider that has a key: anthropic, then groq)
LLM_PROVIDER = os.getenv("SITEBRAIN_LLM_PROVIDER", "auto").lower()

CLAUDE_MODEL = os.getenv("SITEBRAIN_MODEL", "claude-opus-5-5")
CLAUDE_EFFORT = os.getenv("SITEBRAIN_EFFORT", "low")

# Groq (free tier available at console.groq.com) — OpenAI-compatible API
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

# Any other OpenAI-compatible server, e.g. Ollama (free, local): http://localhost:11434/v1
OPENAI_COMPAT_BASE_URL = os.getenv("OPENAI_COMPAT_BASE_URL", "http://localhost:11434/v1")
OPENAI_COMPAT_API_KEY = os.getenv("OPENAI_COMPAT_API_KEY", "ollama")
OPENAI_COMPAT_MODEL = os.getenv("OPENAI_COMPAT_MODEL", "llama3.1:8b")

# Embeddings for semantic document search (hybrid with BM25): auto | local | openai_compat | off
#   auto/local = fastembed ONNX model on this machine (downloads ~70 MB once); off = BM25 keyword search only
EMBED_PROVIDER = os.getenv("SITEBRAIN_EMBED", "auto").lower()
EMBED_MODEL = os.getenv("SITEBRAIN_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
EMBED_OPENAI_BASE_URL = os.getenv("EMBED_OPENAI_BASE_URL", OPENAI_COMPAT_BASE_URL)
EMBED_OPENAI_API_KEY = os.getenv("EMBED_OPENAI_API_KEY", OPENAI_COMPAT_API_KEY)
EMBED_OPENAI_MODEL = os.getenv("EMBED_OPENAI_MODEL", "nomic-embed-text")
# A chunk found only by meaning (no shared keywords) must be at least this similar to the question
EMBED_MIN_SIM = float(os.getenv("SITEBRAIN_EMBED_MIN_SIM", "0.6"))

# Diagnostic loop policy (SRS §4.2)
MAX_DIAGNOSTIC_TURNS = int(os.getenv("SITEBRAIN_MAX_TURNS", "5"))
CONFIDENCE_THRESHOLD = float(os.getenv("SITEBRAIN_CONFIDENCE", "0.85"))
# Present-condition check: how many field checks are asked together, as one form, before the one-at-a-time
# follow-ups (0 or 1 = ask one check at a time from the start)
SURVEY_SIZE = int(os.getenv("SITEBRAIN_SURVEY", "0"))

# Learning from resolved sessions: authored likelihoods count as LEARN_STRENGTH sessions of prior evidence
LEARNING = os.getenv("SITEBRAIN_LEARNING", "true").lower() == "true"
LEARN_STRENGTH = float(os.getenv("SITEBRAIN_LEARN_STRENGTH", "10"))

# Reading attachments while SiteBrain troubleshoots (not once escalated): voice notes are transcribed, photos and
# video frames are described and matched to the pending check, documents are read. Any OpenAI-compatible API with
# speech-to-text and a vision model; by default the Groq key above (free tier).
MEDIA_ENABLED = os.getenv("SITEBRAIN_MEDIA", "on").lower() not in ("off", "false", "0")
MEDIA_API_KEY = os.getenv("MEDIA_API_KEY", GROQ_API_KEY)
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", GROQ_BASE_URL)
MEDIA_STT_MODEL = os.getenv("MEDIA_STT_MODEL", "whisper-large-v3-turbo")
MEDIA_VISION_MODEL = os.getenv("MEDIA_VISION_MODEL", "qwen/qwen3.8-27b")

# Optional outbound escalation channels (SRS §8: email/SMS digest; Teams webhook)
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ESCALATION_EMAIL_TO = os.getenv("ESCALATION_EMAIL_TO", "")

# The administrator, created on start-up when no user has this email. SITEBRAIN_ADMIN_PASSWORD is their password:
# it is applied on every start, so changing it here (and restarting) changes it. The administrator sets the passwords
# of the field operators and experts.
ADMIN_EMAIL = os.getenv("SITEBRAIN_ADMIN_EMAIL", "").strip().lower()
ADMIN_NAME = os.getenv("SITEBRAIN_ADMIN_NAME", "Administrator").strip() or "Administrator"
ADMIN_PASSWORD = os.getenv("SITEBRAIN_ADMIN_PASSWORD", "")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
