"""Rule-based asset dependency lookup (SRS §8 Hackathon MVP: H2S Vessel → Filter → Compressor).

Two layers: a process-stream graph between process nodes, and a mapping from each equipment
to the node it belongs to. Enterprise would replace this with a graph DB built from P&IDs.
"""
import re

# node id -> (label, stream)
NODES = {
    "FEED": ("Feeding H1 & H2", "slurry"),
    "DIG": ("Digesters D1–D4", "slurry"),
    "HWG": ("Hot Water Generator", "utility"),
    "SCR": ("H2S Scrubber Vessel", "gas"),
    "FLT": ("Gas Filtration Skid", "gas"),
    "BLW": ("Gas Blowers", "gas"),
    "LPC": ("LP Gas Compressors", "gas"),
    "CHL": ("Chiller & Dehydration", "gas"),
    "MEM": ("Membrane Upgrader", "gas"),
    "HPC": ("HP Compressors", "gas"),
    "CBG": ("CBG Pipeline / Cascade", "gas"),
    "FLR": ("Flare / Recycle Loop", "gas"),
    "CW": ("Cooling & Chilled Water", "utility"),
    "SLS": ("Solid-Liquid Separation", "slurry"),
    "CDT": ("CDT & PST", "slurry"),
}

EDGES = [
    ("FEED", "DIG", "slurry"), ("HWG", "DIG", "heat"), ("DIG", "SCR", "raw biogas"),
    ("SCR", "FLT", "sweet gas"), ("FLT", "BLW", "filtered gas"), ("BLW", "LPC", "gas"),
    ("LPC", "CHL", "compressed gas"), ("CW", "CHL", "chilled water"), ("CHL", "MEM", "dry gas"),
    ("MEM", "HPC", "CBG >95% CH4"), ("MEM", "FLR", "off-spec / tail gas"), ("HPC", "CBG", "CBG"),
    ("DIG", "SLS", "digestate"), ("SLS", "CDT", "filtrate"),
]

_RULES = [
    (r"H2S Scrubber", "SCR"), (r"Filtration Skid", "FLT"), (r"Membrane", "MEM"),
    (r"^Gas Blower", "BLW"), (r"^LP \d", "LPC"), (r"^HP \d", "HPC"), (r"^Chiller$", "CHL"),
    (r"Cooling Water Pump|Chiller Pump", "CW"), (r"Flare Blower", "FLR"),
]
_UNIT_NODE = {"D1": "DIG", "D2": "DIG", "D3": "DIG", "D4": "DIG", "FEED": "FEED", "SLS": "SLS",
              "CDT": "CDT", "HWG": "HWG", "BUU": "LPC"}


def node_of(eq: dict) -> str | None:
    """Process node for an equipment ({name, unit}) or a whole area ({name: "", unit}); None if unmapped."""
    for pat, node in _RULES:
        if eq.get("name") and re.search(pat, eq["name"], re.I):
            return node
    return _UNIT_NODE.get(eq.get("unit"))


def upstream(node: str) -> list[str]:
    return [a for a, b, _ in EDGES if b == node]


def downstream(node: str) -> list[str]:
    return [b for a, b, _ in EDGES if a == node]


def context_for(eq: dict) -> dict:
    n = node_of(eq)
    if n is None:  # an area configured in Plant Setup that is not on the process-stream graph
        label = eq.get("unit_name") or eq.get("name") or "Unmapped area"
        return {"node": None, "label": label, "stream": None, "upstream": [], "downstream": [], "path": label}
    return {
        "node": n, "label": NODES[n][0], "stream": NODES[n][1],
        "upstream": [{"node": u, "label": NODES[u][0]} for u in upstream(n)],
        "downstream": [{"node": d, "label": NODES[d][0]} for d in downstream(n)],
        "path": " → ".join(NODES[x][0] for x in upstream(n) + [n] + downstream(n)),
    }


def graph() -> dict:
    return {"nodes": [{"id": k, "label": v[0], "stream": v[1]} for k, v in NODES.items()],
            "edges": [{"from": a, "to": b, "label": l} for a, b, l in EDGES]}
