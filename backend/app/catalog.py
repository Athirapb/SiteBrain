"""Equipment catalog and issue vocabulary.

The LLF shift checksheet workbook is used once, to seed the plant's areas and equipment. After that,
areas and equipment are maintained from the Plant Setup screen. The workbook has one sheet per unit,
and each equipment block looks like:
    <Equipment name> | Date | Shift - A/B/C
    Sr. No | Check points | Check Remark | Remark
    1      | Oil level    | 60-80%       |
Blocks are laid out in two side-by-side column groups, so we scan every cell for "Sr. No".

Issues are reported by the field operator against an area or an equipment, with symptoms from SYMPTOMS.
"""
import re
from pathlib import Path

UNIT_NAMES = {
    "BUU": "Biogas Upgradation Unit", "D1": "Digester 1", "D2": "Digester 2", "D3": "Digester 3",
    "D4": "Digester 4", "HWG": "Hot Water Generator", "SLS": "Solid-Liquid Separation",
    "FEEDING H1 AND H2": "Feeding H1 & H2", "CDT AND PST": "Concentrated Digestate Tank",
    "PST": "Primary Sludge Tank",
}
UNIT_CODES = {"FEEDING H1 AND H2": "FEED", "CDT AND PST": "CDT"}
# The plant's process order (feed → digestion → heating → digestate handling → gas upgrading), as the O&M team
# reads it; the area pickers follow it.
UNIT_ORDER = ["FEED", "PST", "D1", "D2", "D3", "D4", "HWG", "CDT", "SLS", "BUU"]

KIND_ICON = {
    "Agitator": "fan", "Pump": "pump", "Blower": "weather-windy", "Compressor": "engine-outline",
    "Decanter": "rotate-3d-variant", "WAM": "cog-outline", "Shredder": "saw-blade", "HWG": "water-boiler",
    "Chiller": "snowflake", "Machine": "factory", "Scrubber": "filter-variant", "Filter": "air-filter",
    "Membrane": "molecule",
}
KINDS = list(KIND_ICON)
ROTATING = {"Agitator", "Pump", "Blower", "Compressor", "Decanter", "WAM", "Shredder", "HWG", "Machine"}

# SRS §5 process skids that the LLF mechanical checksheet does not list. Added to the BUU gas train.
PROCESS_ASSETS = [
    ("H2S Scrubber Vessel", "Scrubber", "SCRUBBER-H2S-01"),
    ("Gas Filtration Skid", "Filter", "FILTER-SKID-01"),
    ("Membrane Upgrader", "Membrane", "MEMBRANE-01"),
]

SEVERITIES = ["Low", "Medium", "High", "Critical"]


def _sym(id, label, icon, keys, kinds):
    return {"id": id, "label": label, "icon": icon, "keys": keys, "kinds": sorted(kinds)}


# What a field operator can report. `keys` line up with decision-tree cause keys (trees.py) to set the
# diagnostic prior; `kinds` rank which equipment in an area most likely shows the symptom.
SYMPTOMS = [
    _sym("noise", "Abnormal noise", "volume-high", ["sound", "noise", "knock"], ROTATING),
    _sym("vibration", "High vibration", "vibrate", ["vibration"], ROTATING),
    _sym("leak", "Leakage (oil / slurry / water)", "water-alert-outline",
         ["leakage", "leak", "seal", "gland", "oil leakage"], {"Pump", "Agitator", "Compressor", "Decanter"}),
    _sym("overheat", "Overheating", "thermometer-alert", ["temperature", "bearing", "hot"],
         ROTATING | {"Chiller", "HWG"}),
    _sym("gas", "Gas smell / gas leak", "smoke", ["gas", "smell"],
         {"Blower", "Compressor", "Scrubber", "Filter", "Membrane"}),
    _sym("flow", "Low flow / choking", "pipe-disconnected", ["material flow", "flow", "choke", "mesh", "filter"],
         {"WAM", "Shredder", "Pump", "Filter", "Scrubber", "Machine"}),
    _sym("pressure", "Pressure / dP abnormal", "gauge", ["differential", "pressure", "element dp", "permeate"],
         {"Scrubber", "Filter", "Membrane", "Compressor", "Pump"}),
    _sym("quality", "Gas quality off-spec", "molecule", ["methane purity", "breakthrough", "gas outlet", "tail gas"],
         {"Membrane", "Chiller", "Scrubber"}),
    _sym("lube", "Low oil / grease", "oil", ["oil level", "oil", "grease"], {"Compressor", "Decanter", "Agitator", "Machine"}),
    _sym("belt", "Belt / drive problem", "cog-transfer-outline", ["belt", "coupling"], {"HWG", "Blower", "Machine", "Agitator"}),
    _sym("trip", "Trips / won't start", "power-plug-off-outline", ["trip", "current"], ROTATING),
    _sym("dust", "Dust / material spillage", "weather-dust", ["dust", "material flow"], {"Shredder", "Machine"}),
]
SYMPTOM_BY_ID = {s["id"]: s for s in SYMPTOMS}


def symptoms_for(kinds: list[str]) -> set[str]:
    """Symptoms that equipment of these kinds can show; every symptom when there is no equipment to go by."""
    kinds = set(kinds)
    return {s["id"] for s in SYMPTOMS if not kinds or kinds & set(s["kinds"])}


def symptom_labels(ids: list[str]) -> list[str]:
    return [SYMPTOM_BY_ID[i]["label"] for i in ids if i in SYMPTOM_BY_ID]


def report_hint(report: dict) -> str:
    """Free text that the diagnostic engine matches against cause and question keys."""
    parts = []
    for i in report.get("symptoms") or []:
        s = SYMPTOM_BY_ID.get(i)
        if s:
            parts += [s["label"]] + s["keys"]
    parts.append(report.get("description") or "")
    return " ".join(parts).lower()


def report_summary(report: dict) -> str:
    labels = symptom_labels(report.get("symptoms") or [])
    desc = (report.get("description") or "").strip()
    head = ", ".join(labels)
    if head and desc:
        return f"{head}: {desc}"
    return head or desc or "Field-reported issue"


def kind_of(name: str) -> str:
    n = name.upper()
    if "AGITATOR" in n:
        return "Agitator"
    if "PUMP" in n:
        return "Pump"
    if "BLOWER" in n:
        return "Blower"
    if re.match(r"^(LP|HP) \d", n) or "COMP" in n:
        return "Compressor"
    if "DECANTER" in n:
        return "Decanter"
    if "WAM" in n:
        return "WAM"
    if "SHREDDER" in n:
        return "Shredder"
    if n.startswith("HWG"):
        return "HWG"
    if "CHILLER" in n:
        return "Chiller"
    return "Machine"


_UPPER = re.compile(r"^(LP|HP|CDT|PST|SBT|LDT|RC|HWG|WAM|ID|H1|H2|D\d|H2S)$", re.I)


def title_case(s: str) -> str:
    words = [w.upper() if _UPPER.match(w) else w[:1].upper() + w[1:].lower() for w in s.split()]
    return " ".join(words).replace("Comp.", "Compressor")


def parse_checksheet(path: Path) -> list[dict]:
    """Return [{unit, unit_name, name, kind}] for every equipment block in the workbook."""
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    out: list[dict] = []
    for ws in wb.worksheets:
        if ws.title.strip().upper() == "INDEX":
            continue
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        sheet_key = ws.title.strip().upper()
        unit = UNIT_CODES.get(sheet_key, sheet_key)
        unit_name = UNIT_NAMES.get(sheet_key, ws.title.strip())
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                if not (isinstance(v, str) and v.strip().lower().startswith("sr. no") and r > 0):
                    continue
                prev = rows[r - 1]
                name = None
                for cc in range(c, max(-1, c - 4), -1):
                    cand = prev[cc] if cc < len(prev) else None
                    if isinstance(cand, str) and cand.strip() and not re.match(r"^(date|shift)", cand.strip(), re.I):
                        name = cand.strip()
                        break
                # a real equipment block has at least one numbered checkpoint row under the header
                nxt = rows[r + 1] if r + 1 < len(rows) else []
                if name and c < len(nxt) and isinstance(nxt[c], (int, float)):
                    u, un = unit, unit_name
                    if unit == "CDT" and name.strip().upper().startswith("PST"):
                        u, un = "PST", UNIT_NAMES["PST"]  # the CDT & PST sheet holds two areas
                    out.append({"unit": u, "unit_name": un, "name": title_case(name), "kind": kind_of(name)})
    wb.close()
    return out


def augment_with_process_assets(items: list[dict]) -> list[dict]:
    for it in items:
        if it["unit"] == "BUU" and it["kind"] == "Chiller":
            it["tag"] = "CHILLER-01"
    existing = {(i["unit"], i["name"]) for i in items}
    for name, kind, tag in PROCESS_ASSETS:
        if ("BUU", name) not in existing:
            items.insert(0, {"unit": "BUU", "unit_name": UNIT_NAMES["BUU"], "name": name, "kind": kind, "tag": tag})
    return items
