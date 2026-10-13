"""Synthetic SCADA historian.

The hackathon MVP has no live MQTT/OPC-UA feed (SRS §8), so this module produces a deterministic
30-minute telemetry window per equipment. Values track the condition of the open issue on that equipment
(reported symptoms, severity and hazards found during diagnosis), and stay at baseline when there is none.
Swap `snapshot()` for a historian query in production; the escalation payload format stays the same.
"""
import hashlib
import random
import time

SAMPLES = 10          # one sample every 3 minutes across the 30-minute window
STEP_MIN = 3


def _rng(eq_id: str) -> random.Random:
    window = int(time.time() // 1800)
    seed = int(hashlib.sha1(f"{eq_id}:{window}".encode()).hexdigest()[:8], 16)
    return random.Random(seed)


def condition(report: dict | None, flags=()) -> dict:
    """Reduce an issue report plus hazard flags to the signals the historian simulates."""
    report = report or {}
    sy = set(report.get("symptoms") or [])
    sev = report.get("severity") or "Medium"
    f = set(flags or [])
    mech = "ok"
    if sy & {"noise", "vibration", "overheat"} or "rotating_abnormal" in f:
        mech = "warn"
    if (sev == "Critical" and sy & {"noise", "vibration"}) or "rotating_critical" in f:
        mech = "crit"
    return {"mech": mech, "symptoms": sy, "severity": sev, "flags": f}


def _series(rng: random.Random, base: float, noise: float, end: float | None = None, nd: int = 2) -> list[float]:
    end = base if end is None else end
    out = []
    for k in range(SAMPLES):
        # abnormal values ramp in over the last third of the window
        t = max(0.0, (k - SAMPLES * 0.55) / (SAMPLES * 0.45))
        v = base + (end - base) * min(1.0, t) + rng.uniform(-noise, noise)
        out.append(round(v, nd))
    return out


def snapshot(eq: dict, cond: dict | None = None) -> dict:
    cond = cond or condition(None)
    rng = _rng(eq["id"])
    kind = eq["kind"]
    sy, f, high = cond["symptoms"], cond["flags"], cond["severity"] in ("High", "Critical")
    mech = cond["mech"]
    vib_end = {"ok": 2.2, "warn": 6.8, "crit": 11.5}[mech]
    temp_end = {"ok": 62, "warn": 78, "crit": 92}[mech]
    tags: dict = {}

    if kind == "Scrubber":
        dp = "Sudden drop" if "channeling" in f else "Spike" if "pressure" in sy else None
        h2s = "High" if "h2s_breakthrough" in f else "Detected" if "quality" in sy else None
        tags["inlet_pressure_bar"] = _series(rng, 1.21, 0.01, 1.45 if dp == "Spike" else 1.22)
        tags["differential_pressure_dp"] = _series(rng, 0.05, 0.004, {"Spike": 0.14, "Sudden drop": 0.012}.get(dp, 0.05), 3)
        tags["h2s_outlet_ppm"] = _series(rng, 4, 1.5, {"Detected": 65, "High": 310}.get(h2s, 4), 0)
    elif kind == "Filter":
        el = ("Very high" if high else "High") if "pressure" in sy else None
        tags["element_dp_bar"] = _series(rng, 0.08, 0.005, {"High": 0.21, "Very high": 0.36}.get(el, 0.08), 3)
        tags["filter_bypass_valve_state"] = "OPEN" if "bypass_open" in f else "CLOSED"
        tags["secondary_guard_filter"] = "INACTIVE" if "guard_inactive" in f else "ACTIVE"
    elif kind == "Chiller":
        gt = ">8°C" if "water_carryover" in f else "5-8°C" if sy & {"quality", "overheat"} else None
        tags["gas_outlet_temp_c"] = _series(rng, 3.6, 0.3, {"5-8°C": 6.6, ">8°C": 9.4}.get(gt, 3.6), 1)
        tags["dew_point_c"] = _series(rng, 3.0, 0.3, {"5-8°C": 6.0, ">8°C": 8.8}.get(gt, 3.0), 1)
        tags["condensate_drain_cycles_h"] = _series(rng, 6, 0.5, 0 if "water_carryover" in f else 6, 0)
    elif kind == "Membrane":
        off = "quality" in sy or "offspec_gas" in f
        tags["ch4_purity_pct"] = _series(rng, 96.6, 0.2, (88.4 if high else 93.2) if off else 96.6, 1)
        tags["permeate_dp_bar"] = _series(rng, 0.9, 0.03, 1.3 if "pressure" in sy else 0.9)
        tags["tail_gas_flow_nm3h"] = _series(rng, 42, 1.5, 42, 0)
    else:
        tags["vibration_mm_s"] = _series(rng, 2.1, 0.25, vib_end)
        tags["bearing_temp_c"] = _series(rng, 58, 1.2, temp_end, 1)
        tags["motor_current_a"] = _series(rng, 18 if kind != "Compressor" else 42, 0.6,
                                          (18 if kind != "Compressor" else 42) * (1.15 if mech == "crit" else 1.0), 1)
        if kind == "Compressor":
            low = "lube" in sy or "low_oil" in f
            tags["oil_level_pct"] = _series(rng, 70, 0.6, 52 if low else 70, 0)
            hp = eq["name"].upper().startswith("HP")
            tags["suction_pressure_bar"] = _series(rng, 6.0 if hp else 1.2, 0.03)
            tags["discharge_pressure_bar"] = _series(rng, 248 if hp else 6.1, 2 if hp else 0.08)
        if kind == "Pump":
            leak = "leak" in sy and high
            tags["discharge_pressure_bar"] = _series(rng, 2.4, 0.05, 1.9 if leak else 2.4)
    return {
        "window_minutes": SAMPLES * STEP_MIN,
        "interval_minutes": STEP_MIN,
        "source": "simulated-historian",
        "tags": tags,
    }


def latest(snap: dict, tag: str):
    v = snap["tags"].get(tag)
    if isinstance(v, list):
        return v[-1] if v else None
    return v
