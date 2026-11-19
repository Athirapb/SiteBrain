"""Process causes: the machine may be healthy, but what it handles is not.

An abnormal condition on a plant item is not always mechanical or electrical. A pump "fails" because the slurry is
too thick, gassy or the tank ran low; an agitator shakes because the level dropped below its propeller or the
digester is foaming; a blower surges because the gas holder is empty; a burner locks out because the methane is low;
a membrane makes off-spec gas because air got into the raw gas. These causes are on the process side of the
fishbone, and the fix is a process fix (level, feed, gas balance, lab results), not a strip-down.

  SHARED   one process cause added to every equipment type: the process around it is upset (starved upstream or
           held back downstream), with one check that reads the upstream and downstream conditions
  PROCESS  process causes specific to one equipment type, with their own checks and 5-Why trees
  EVIDENCE what the trees' existing checks already say about these causes (first matching rule per option)
  DOMAIN   the trees' own causes that are really process causes (feed quality, gas quality, suction conditions)

Sources: OEM manuals and SOPs in data/docs, the RCA guides, and standard biogas-plant practice (FNR Biogas Guide,
KTBL / DLG operating guidance, Hydraulic Institute pump guidance, membrane-upgrading OEM practice). Numbers are
typical values; site design data wins.
"""
import re

from .dsl import B, C, Q, R, W, is_normal_answer

# Before any check, a process cause is about as likely as an electrical one: less than a typical mechanical cause
PRIOR = 0.35


def _c(id, label, category, keys, steps, why):
    c = C(id, label, category, keys, steps, why=why)
    c.update(domain="process", prior=PRIOR)
    return c


SHARED = _c(
    "p_conn", "Process upset around it — starved by what feeds it, or held back by what it feeds (the machine "
    "itself may be fine)", "Environment",
    ["upstream", "downstream", "level", "starved", "no supply", "tank full", "tank empty", "process"], [
        "Check upstream with the control room: is the tank, holder or machine that feeds it at its normal level, "
        "pressure and flow, and running?",
        "Check downstream: valves open as per the line-up, receiving tank not full, receiving pressure normal",
        "Put the upstream / downstream condition right first, before working on this machine",
        "Watch this machine for 30 minutes once the process is back to normal"],
    W("Why was the process around it upset?", [
        B("Upstream equipment tripped or underperformed", R(
            "Upstream failures are not alarmed to whoever runs the equipment downstream", "Measurement",
            prevent=["Alarm low level / low pressure at the suction of each machine, with an auto-stop to protect it",
                     "Show upstream status on this machine's HMI page"])),
        B("Level or pressure control set wrong", R(
            "Level and pressure setpoints don't match what the machines need", "Method",
            prevent=["Review low / high level and pressure setpoints against each machine's minimum and maximum (MOC)"])),
        B("What it receives changed (feed or gas)", R(
            "Feed and gas quality changes are not passed on to the operators downstream", "Method",
            prevent=["Daily feed-quality log (TS, fibre, grit) shared at shift handover",
                     "Lab results (TS, FOS/TAC, gas composition) shown in the control room"])),
    ]))

SHARED_CHECK = Q("p_conn", "How are things around it right now — the tank, holder or machine before it, and what "
                           "it delivers into?", [
    ("Normal — supply and delivery as usual", {"p_conn": 0.12}),
    ("Starved — upstream level, pressure or supply low", {"p_conn": 8.0}),
    ("Held back — downstream full, closed or high pressure", {"p_conn": 8.0, "o_duty": 1.5}),
    ("Feed changed — thicker, wetter or dirtier than usual", {"p_conn": 3.0}),
], ["upstream", "downstream", "level", "supply", "starved"],
    how="Ask the control room, or read the HMI: the level or pressure of what feeds it, whether that equipment is "
        "running, and the valve line-up and pressure of what it delivers into.",
    purpose="Many 'machine' problems start in the process around it — fix the process first and the machine "
            "often recovers on its own.")

# Kinds whose own tree already has the "upstream process upset" cause: the shared check is asked, but its evidence
# goes to that cause instead of adding a duplicate one
SHARED_AS = {"Decanter": "feed", "Chiller": "load", "Scrubber": "load"}

# Extra evidence for the shared check per kind: which of the kind's own causes the starved / held back / changed
# answers point to
SHARED_CHECK_EXTRA = {
    "Pump": {1: {"cav": 2.0}, 3: {"p_thick": 3.0, "imp": 1.5}},
    "Agitator": {1: {"p_level": 1.4}, 3: {"sed": 2.5, "rag": 1.5}},
    "Blower": {1: {"p_suction": 1.4}, 2: {"backpr": 2.0}},
    "Compressor": {1: {"p_suction": 1.4}, 3: {"liquid": 1.5, "particle": 1.5}},
    "HWG": {1: {"lowgas": 2.5}, 3: {"p_ch4": 2.0}},
    "Decanter": {3: {"feed": 4.0, "polymer": 1.5}},
    "WAM": {2: {"press": 1.5}, 3: {"fibre": 2.5, "overload": 1.5}},
    "Shredder": {3: {"wet": 2.5, "foreign": 1.5}},
    "Machine": {3: {"jam": 2.5}},
    "Chiller": {3: {"load": 4.0}},
    "Scrubber": {3: {"load": 4.0}},
    "Filter": {3: {"liquid": 2.5, "element": 1.5}},
    "Membrane": {1: {"press": 2.0}, 3: {"p_air": 2.0, "moist": 2.0}},
}

PROCESS: dict[str, list[dict]] = {
    "Pump": [
        _c("p_gas", "Gas or air in the suction — foaming / gassy slurry or a vortex at low level (gas lock)",
           "Material", ["foam", "gas lock", "air lock", "bubbles", "loses prime", "airlock"], [
               "Stop the pump before it runs dry",
               "Gas-test, then vent the suction line and casing at the high-point vent (it may be biogas)",
               "Bring the tank level back above the pump's minimum submergence before restarting",
               "If the slurry is foaming, cut recirculation and tell the process engineer — foam is a digester upset",
               "Restart and watch the discharge pressure: it should be steady"],
           W("Why did gas or air get into the suction?", [
               B("Tank level ran down near the suction nozzle", R(
                   "Low-level pump stop missing or set too low for this suction", "Measurement",
                   prevent=["Set the low-level pump stop above the suction nozzle's minimum submergence",
                            "Alarm low tank level in the control room"])),
               B("The digester or tank was foaming", R(
                   "Foaming is not watched or controlled (feed rate, fats, overloading)", "Method",
                   prevent=["Check for foam (sight glass / foam probe) every shift",
                            "Keep loading and fat-rich feed inside the recipe; stock antifoam with a dosing SOP"])),
               B("Gas collects at a high point in the suction line", R(
                   "Suction pipe has a gas trap with no vent", "Machine",
                   prevent=["Fit a vent at the suction high point",
                            "Slope the suction line back toward the tank at the next shutdown"])),
           ])),
        _c("p_thick", "Slurry too thick, sandy or fibrous for the pump — high solids / viscosity, or sand settled in "
                      "the line", "Material", ["thick", "sand", "viscous", "high ts", "solids", "press mud", "grit"], [
               "Stop and isolate; flush the suction and discharge lines with water or liquid digestate",
               "Clear the suction strainer / stone trap",
               "With the shift engineer, bring the slurry back to design solids (dilute with recirculated liquid)",
               "Restart and compare current and discharge pressure with normal"],
           W("Why was the slurry thicker or sandier than the pump can take?", [
               B("Feed recipe changed — more press mud or dung", R(
                   "Feed solids (TS) are not checked against the pumps' design limit", "Material",
                   prevent=["Daily TS test of feed / digestate, with a limit for each pump",
                            "Dilution step in the feeding SOP when TS is high"])),
               B("Sand settled while the line stood idle", R(
                   "Lines are not flushed when the pumps stop", "Method",
                   prevent=["Flush lines after every stop longer than a few hours",
                            "Add an automatic flush on pump stop"])),
               B("Grit keeps building up in the tank", R(
                   "No grit removal or tank desanding plan", "Method",
                   prevent=["Plan periodic desanding of the tanks", "Fit a stone / grit trap ahead of the feed system"])),
           ])),
    ],
    "Agitator": [
        _c("p_level", "Tank level too low — the propeller is near the surface (vortex, splashing, shaking)", "Method",
           ["low level", "level", "vortex", "splashing", "surface"], [
               "Stop the agitator if the propeller is near or breaking the surface",
               "With the control room, bring the level back above the agitator's minimum (stop withdrawal or feed in)",
               "Restart and check vibration and current are back to normal"],
           W("Why did the level drop so low?", [
               B("Drawn off faster than it was fed", R(
                   "Withdrawal is not interlocked with the agitators' minimum level", "Method",
                   prevent=["Interlock: stop the agitators below their minimum submergence level",
                            "Show the minimum agitation level on the HMI"])),
               B("Level transmitter reads wrong", R(
                   "Level transmitter is not checked against a manual dip", "Measurement",
                   prevent=["Monthly dip / radar cross-check of the level transmitter"])),
               B("Level lowered for maintenance, agitators left on", R(
                   "Tank-emptying SOP doesn't say to stop the agitators", "Man",
                   prevent=["Add 'stop agitators before lowering the level' to the tank-emptying SOP"])),
           ])),
        _c("p_foam", "Foaming from a digester process upset (overloading, fats / proteins, high VFA)", "Material",
           ["foam", "foaming", "overflow", "fos", "vfa", "upset"], [
               "With the process engineer, cut the feed rate to the digester",
               "Dose antifoam as per the SOP if you have it; don't run the agitators at a speed that whips foam",
               "Check the gas line, condensate traps and safety valves for foam carry-over",
               "Test FOS/TAC and pH; keep the feed low until they recover"],
           W("What set off the foaming?", [
               B("Feed increased or a new feedstock added", R(
                   "Loading raised faster than the digester can adapt", "Method",
                   prevent=["Raise loading by no more than 10–15 % a week",
                            "Trial new feedstocks in small ratios first"])),
               B("Fat- or protein-rich feed (oil cake, slaughter waste)", R(
                   "No limit on fat- or protein-rich feedstock in the recipe", "Material",
                   prevent=["Set a maximum share for fat- and protein-rich feed",
                            "Stock antifoam with a dosing procedure"])),
               B("FOS/TAC was rising, nobody acted", R(
                   "Lab results have no act-on limits", "Measurement",
                   prevent=["Act-on limits for FOS/TAC (0.3 watch, 0.4 cut the feed)",
                            "Weekly review of lab trends by the process engineer"])),
           ])),
    ],
    "Blower": [
        _c("p_suction", "Not enough gas — gas holder low or suction pressure low, so the blower starves or surges",
           "Environment", ["holder", "low gas", "suction", "surge", "no gas", "gas production"], [
               "Check the gas holder level and today's gas production with the control room",
               "Cut the blower speed or gas offtake (or unload a compressor) until the holder recovers",
               "Check the suction valves and the condensate trap are not restricting the suction",
               "Restart at normal speed once the holder is back above its low level"],
           W("Why was there not enough gas at the suction?", [
               B("Gas production dropped — digester upset or less feed", R(
                   "Gas offtake is not matched to gas production", "Method",
                   prevent=["Link blower / compressor capacity to the gas holder level (auto-unload at low level)",
                            "Daily gas balance review"])),
               B("Holder low-level stop set too low", R(
                   "Gas holder low-level protection set below what the blower needs", "Measurement",
                   prevent=["Set the low-level unload / stop above the blower's minimum suction pressure"])),
               B("A suction valve was part-closed", R(
                   "Suction valves are not on the start-up line-up sheet", "Method",
                   prevent=["Add the suction valves to the start-up line-up sheet"])),
           ])),
    ],
    "Compressor": [
        _c("p_suction", "Not enough gas at the suction — low suction pressure from the blowers / gas holders "
                        "(unloading, cycling or low-suction trips)", "Environment",
           ["suction", "low suction", "holder", "unloading", "no gas", "gas production"], [
               "Check suction pressure, gas holder level and blower status with the control room",
               "Run fewer compressors (or unload) to match the gas available",
               "Check the suction strainer and valves are not restricting the flow",
               "Load again once the suction pressure is back in its normal band"],
           W("Why was the suction pressure low?", [
               B("Blowers or the gas train limited the flow", R(
                   "Compressor loading is not linked to the gas available", "Method",
                   prevent=["Capacity control on suction pressure (auto-unload)",
                            "Alarm low suction pressure before the trip point"])),
               B("Gas production dropped", R(
                   "Gas offtake is not planned against gas production", "Method",
                   prevent=["Daily gas balance; run compressors to match the gas made"])),
               B("Suction strainer or filter restricting", R(
                   "Suction strainer dP is not monitored", "Measurement",
                   prevent=["Fit a dP gauge on the suction strainer with a cleaning limit"])),
           ])),
    ],
    "HWG": [
        _c("p_ch4", "Poor biogas quality — low methane, or high O2 / moisture (weak flame, flame failures)",
           "Material", ["methane", "ch4", "gas quality", "weak flame", "o2"], [
               "Read raw-gas CH4, O2 and H2S on the gas analyser",
               "If CH4 is low, tell the process engineer — it's a digester or air-dosing problem",
               "Drain the condensate traps on the HWG gas line",
               "Re-tune the air–fuel ratio for the gas quality you actually have"],
           W("Why was the gas quality poor?", [
               B("Digester upset — methane dropped", R(
                   "Gas quality changes are not alarmed to the HWG operators", "Measurement",
                   prevent=["Alarm low CH4 (below 50 %) at the HWG and in the control room"])),
               B("Too much air dosed for H2S control", R(
                   "Air dosing is not trimmed to the gas flow", "Method",
                   prevent=["Control air dosing to keep O2 below 0.5–1 %"])),
               B("Water in the gas line", R(
                   "Gas line condensate traps are not drained on the rounds", "Method",
                   prevent=["Add the HWG gas-line traps to the daily round"])),
           ])),
    ],
    "Membrane": [
        _c("p_air", "Air (N2 / O2) in the raw gas — from air dosing or a suction-side leak; membranes can't remove "
                    "nitrogen", "Material", ["oxygen", "o2", "nitrogen", "n2", "air ingress", "air"], [
               "Read O2 (and N2 if you can) in the raw gas and the product gas",
               "Cut the scrubber air dosing to the minimum that still holds H2S",
               "Leak-test the suction side of the blowers / LP compressors (joints under vacuum draw air in)",
               "Watch product CH4 recover over the next few hours"],
           W("Why did air get into the gas?", [
               B("Air dosing set too high", R(
                   "Air dosing is not controlled on O2", "Method",
                   prevent=["O2-controlled air dosing with a high-O2 alarm at 1 %"])),
               B("Air drawn in at a leak under vacuum", R(
                   "Suction-side joints are not leak-tested", "Machine",
                   prevent=["Quarterly leak test of the gas-train suction under vacuum"])),
               B("Air in the digester gas itself", R(
                   "Raw-gas O2 is not monitored", "Measurement",
                   prevent=["Monitor raw-gas O2 continuously; alarm at 1 %"])),
           ])),
    ],
}

CHECKS: dict[str, list[dict]] = {
    "Pump": [Q("p_slurry", "Take a sample at the suction drain or from the tank (gas test first). What is the slurry "
                           "like compared with normal?", [
        ("Normal — flows like it usually does", {"p_gas": 0.3, "p_thick": 0.2, "p_conn": 0.8}),
        ("Thick, heavy or sandy", {"p_thick": 6.0, "wear": 1.5, "cav": 1.5, "p_conn": 1.2}),
        ("Foamy or full of gas bubbles", {"p_gas": 7.0, "cav": 0.8, "p_conn": 1.2}),
        ("Lots of long fibre, rags or plastic", {"imp": 4.0, "p_thick": 1.5}),
    ], ["thick", "sand", "foam", "gas", "slurry", "solids"],
        how="Open the sample or drain valve on the suction side into a bucket — gas test first, gloves and goggles. "
            "Compare thickness, grit and bubbles with a normal sample.",
        purpose="A pump only handles the slurry it was designed for: thick, sandy or gassy slurry looks like a pump "
                "fault but it's the process.")],
    "Agitator": [
        Q("p_tanklevel", "What's the tank or digester level now, compared with its normal operating level?", [
            ("Normal operating level", {"p_level": 0.15}),
            ("Low — propeller near or at the surface", {"p_level": 8.0, "p_conn": 1.2}),
            ("High — near the overflow, or foam in the gas line", {"p_foam": 3.0, "p_conn": 1.2}),
        ], ["level", "low level", "vortex", "overflow"],
            how="Read the level on the HMI and, if you can, check it against the local gauge or a dip. Ask the control "
                "room for this agitator's minimum level.",
            purpose="An agitator near the surface sucks in gas and shakes — it looks mechanical, but it's the level."),
        Q("p_lab", "What do the latest digester lab results show — FOS/TAC, pH and gas production?", [
            ("Normal — FOS/TAC below 0.4, pH 7–8", {"p_foam": 0.3}),
            ("FOS/TAC above 0.4, pH falling or gas dropping", {"p_foam": 5.0, "sed": 1.5}),
            ("Not tested in the last week", {"p_foam": 1.3}),
        ], ["foam", "fos", "vfa", "ph", "gas production"],
            how="Ask the lab or process engineer for the last FOS/TAC, pH and daily gas production, and compare with "
                "last week.",
            purpose="A stressed digester foams and forms crust, and that overloads the agitator."),
    ],
    "Blower": [Q("p_holder", "What do the gas holder level and the blower suction pressure show now?", [
        ("Normal — holder level and suction pressure", {"p_suction": 0.15}),
        ("Holder low, suction pressure low or negative", {"p_suction": 7.0, "p_conn": 1.2}),
        ("Holder full and the flare running", {"p_suction": 0.3, "backpr": 1.5, "p_conn": 1.2}),
    ], ["holder", "suction", "gas production", "surge"],
        how="Read the gas holder level and the blower suction pressure on the HMI, or the local gauge on the suction "
            "line.",
        purpose="A blower short of gas surges, heats up and trips — it looks like a blower fault, but the gas isn't "
                "there.")],
    "Compressor": [Q("p_supply", "What are the compressor suction pressure and the gas holder level doing?", [
        ("Steady at the usual values", {"p_suction": 0.15}),
        ("Suction pressure low or falling, holder low", {"p_suction": 7.0, "p_conn": 1.2}),
        ("Suction swings as other units load and unload", {"p_suction": 3.0, "o_cycling": 1.5}),
    ], ["suction", "holder", "unloading", "gas production"],
        how="Read the suction pressure trend and the gas holder level on the HMI, and ask which blowers and "
            "compressors are running.",
        purpose="A compressor short of gas unloads, cycles and trips on low suction — the cure is the gas balance.")],
    "HWG": [Q("p_gasq", "What does the gas analyser show for the raw biogas now — CH4 and O2?", [
        ("Normal — CH4 50 % or more, O2 below 1 %", {"p_ch4": 0.15}),
        ("CH4 below 48 %, or O2 above 1 %", {"p_ch4": 7.0, "airfuel": 1.3}),
        ("Analyser not working or not read", {"p_ch4": 1.2}),
    ], ["methane", "ch4", "gas quality", "o2"],
        how="Read CH4 and O2 on the raw-gas analyser (control room or the BUU analyser panel); a portable analyser at "
            "the HWG gas train also works.",
        purpose="A burner tuned for 55 % methane loses its flame on weak gas — the burner may be fine.")],
    "Membrane": [Q("p_o2", "What do the raw-gas O2 and N2 read on the gas analyser?", [
        ("Normal — O2 below 0.5 %, N2 low", {"p_air": 0.15}),
        ("O2 above 1 %, or N2 above 3 %", {"p_air": 8.0}),
    ], ["oxygen", "o2", "nitrogen", "air"],
        how="Read raw-gas O2 (and N2 if measured) on the gas analyser, and compare with the product gas.",
        purpose="Nitrogen passes the membranes with the methane, so air in the raw gas caps the purity whatever the "
                "membranes do.")],
}

# What the trees' existing checks already say about the process causes: (question id, option label regex) → evidence
EVIDENCE = {
    "Pump": [("dp", r"low and fluctuating", {"p_gas": 3.0, "p_thick": 1.5}),
             ("dp", r"low but steady", {"p_thick": 1.5}),
             ("level", r"near or below", {"p_gas": 1.3, "p_conn": 1.4}),
             ("noise", r"gravel|crackling", {"p_gas": 2.0, "p_thick": 1.3}),
             ("backflush", r"recovers", {"p_thick": 3.0}),
             ("current", r"higher than", {"p_thick": 2.5}),
             ("shutoff", r"well below", {"p_gas": 2.0})],
    "Agitator": [("surface", r"foam", {"p_foam": 6.0}),
                 ("surface", r"still", {"p_level": 1.5}),
                 ("surface", r"crust", {"p_foam": 1.5}),
                 ("current", r"swings", {"p_level": 2.5}),
                 ("noise", r"knock", {"p_level": 1.5})],
    "Blower": [("sound", r"pulsing", {"p_suction": 3.0})],
    "Compressor": [("dischtemp", r"high on all", {"p_suction": 1.5})],
    "HWG": [("lockout", r"flame failure", {"p_ch4": 2.5}),
            ("lockout", r"low gas", {"p_ch4": 1.3}),
            ("signal", r"jumps|drops out", {"p_ch4": 2.0}),
            ("o2", r"o2 high", {"p_ch4": 1.3})],
    "Membrane": [("purity", r"below 90|90–95", {"p_air": 1.8})],
}

# The trees' own causes that are process causes: what the equipment handles, not the equipment
DOMAIN = {("Pump", "cav"), ("Pump", "imp"), ("Agitator", "rag"), ("Agitator", "sed"), ("Shredder", "wet"),
          ("Machine", "jam"), ("Decanter", "polymer"), ("Decanter", "feed"), ("WAM", "fibre"), ("Blower", "cond"),
          ("Compressor", "particle"), ("Compressor", "liquid"), ("HWG", "lowgas"), ("HWG", "deposits"),
          ("Chiller", "load")}


def extend(trees: dict[str, dict]) -> None:
    """Add the process causes and checks to every tree, in place (after common.extend)."""
    for kind, tree in trees.items():
        if "category" not in tree["causes"][0]:
            continue
        for c in tree["causes"]:
            if (kind, c["id"]) in DOMAIN:
                c["domain"] = "process"
        same = SHARED_AS.get(kind)
        new = ([] if same else [dict(SHARED)]) + [dict(c) for c in PROCESS.get(kind, [])]
        tree["causes"] += new
        ids = [c["id"] for c in new]
        rules = EVIDENCE.get(kind, [])
        for q in tree["questions"]:
            for o in q["options"]:
                hit = next((lik for qid, pat, lik in rules if qid == q["id"] and re.search(pat, o["label"], re.I)),
                           None)
                for cid in ids:
                    if hit and cid in hit:
                        o["lik"][cid] = hit[cid]
                    elif cid not in o["lik"]:
                        # a reading about the machine itself: healthy is a little more likely when the fault is in
                        # the process around it
                        o["lik"][cid] = 1.3 if is_normal_answer(o["label"]) else 0.7
        all_ids = {c["id"] for c in tree["causes"]}
        extra = SHARED_CHECK_EXTRA.get(kind, {})
        def lik(o: dict, i: int) -> dict:
            own = {(same if same and c == "p_conn" else c): v for c, v in o["lik"].items()}
            return {c: v for c, v in {**own, **extra.get(i, {})}.items() if c in all_ids}
        shared = {**SHARED_CHECK, "options": [{**o, "lik": lik(o, i)} for i, o in enumerate(SHARED_CHECK["options"])]}
        tree["questions"] += [shared] + [
            {**q, "options": [{**o, "lik": {c: v for c, v in o["lik"].items() if c in all_ids}} for o in q["options"]]}
            for q in CHECKS.get(kind, [])]
