"""Pumps: digester recirculation (RC) and transfer pumps, feed-hall pumps, CDT/PST/SBT slurry pumps, decanter feed
pumps (often progressive cavity), and clean-water pumps (cooling water, chiller, service water, LDT).

Sources: centrifugal / slurry pump OEM manuals (mechanical seal flushing, bearing lubrication), Hydraulic Institute
NPSH guidance, plant incident history (incident_log_2026.csv) and SOP-ROT-01 (LOTO).
"""
from .dsl import B, C, K, Q, R, W

TREES = {}

TREES["Pump"] = {
    "causes": [
        C("seal", "Mechanical seal face damage", "Machine", ["seal", "leakage", "leak", "gland"], [
            "Stop the pump, isolate suction and discharge valves and drain the casing (SEAL-01)",
            "Replace the mechanical seal cartridge; check the shaft sleeve for scoring",
            "Restore seal flushing water and confirm flow before restart",
            "Restart and check the seal for drips over the first 30 minutes"],
          why=W("What damaged the seal faces?", [
              B("It ran dry — flush water was off or weak", W("Why was the flushing water missing?", [
                  B("Flush valve left closed after maintenance", R(
                      "No flush-water line-up check in the post-maintenance restart procedure", "Method",
                      prevent=["Add 'flush water open and flowing' to the pump restart checklist",
                               "Fit a flow indicator or flow switch on the flush line, interlocked with pump start"])),
                  B("Flush water pressure too low", R(
                      "Service water header pressure below the seal requirement (about 1 bar above stuffing-box pressure)",
                      "Machine",
                      prevent=["Fit a pressure gauge on the flush line and add it to shift rounds",
                               "Restore the service-water booster pump or add a dedicated seal-water pump"])),
                  B("Flush line choked with scale or solids", R(
                      "Untreated flush water scales the small-bore flush line", "Material",
                      prevent=["Use filtered or softened water for seal flushing",
                               "Add a Y-strainer before the flush inlet and clean it weekly"])),
              ])),
              B("Grit or sand in the slurry wore the faces", W("Why is grit reaching the pump?", [
                  B("Grit / stone trap not cleaned", R(
                      "Grit trap cleaning is not in the PM schedule", "Method",
                      prevent=["Schedule grit-trap cleaning weekly and log the volume removed"])),
                  B("Feedstock carries sand (press mud, unwashed feed)", R(
                      "Feedstock sand content is not checked at reception", "Material",
                      prevent=["Add a sand / inerts check at feedstock reception",
                               "Specify a hard-face (SiC/SiC) seal for abrasive service"])),
              ])),
              B("Seal was past its service life", R(
                  "Seals are replaced only on failure; no condition-based replacement", "Method",
                  prevent=["Track seal running hours and replace at the OEM interval",
                           "Add seal leak-rate to weekly condition monitoring"])),
          ], how="Look at the old seal faces: heat-checking or cracks mean dry running; grooves and polish mean grit."),
          case="KB-0298"),
        C("imp", "Impeller choked with fibres (ragging)", "Material", ["vibration", "flow", "choke"], [
            "Stop and isolate the pump under LOTO; drain the casing",
            "Open the inspection cover or casing and clear fibres from the impeller vanes",
            "Clean the suction strainer and back-flush the line",
            "Restart and confirm discharge pressure and motor current are back to normal"],
          why=W("Why are fibres reaching the impeller?", [
              B("Upstream screen or macerator bypassed or damaged", W("Why was the screen not doing its job?", [
                  B("It blocks often, so the crew bypassed it", R(
                      "Screen is undersized or cleaned too rarely, so bypassing became the workaround", "Method",
                      prevent=["Re-rate the screen for the current feed and set a cleaning frequency",
                               "Lock the bypass valve and make bypassing a permit item"])),
                  B("Screen mesh is torn", R(
                      "Screen mesh condition is not inspected in PM", "Method",
                      prevent=["Add a monthly screen-mesh inspection to PM"])),
              ])),
              B("Long-fibre feed (straw, napier grass) not cut short enough", R(
                  "Shredder cut length too long — worn or blunt blades", "Machine",
                  prevent=["Check shredder blade condition and cut length weekly",
                           "Agree a maximum fibre length with the feeding team"])),
              B("Pump is run throttled at low flow, so solids settle and wrap", R(
                  "Pump operated far below its best efficiency point", "Method",
                  prevent=["Set a minimum flow for the pump and control flow with speed (VFD), not the discharge valve"])),
          ]), case="KB-0455"),
        C("brg", "Bearing wear from lost or contaminated lubrication", "Machine", ["oil", "bearing", "temperature", "vibration"], [
            "Stop the pump under LOTO",
            "Check bearing play; replace the bearing set if rough or noisy",
            "Replace the bearing-housing oil seal",
            "Refill the bearing housing with the correct oil grade to the sight-glass mark"],
          why=W("Why did the bearing lose its lubrication?", [
              B("Oil level was low — it leaked out", W("Why did the oil leak out unnoticed?", [
                  B("Oil seal hardened and leaking", R(
                      "Bearing-housing oil seals are not replaced at overhaul", "Method",
                      prevent=["Replace oil seals at every bearing overhaul",
                               "Add oil-seal condition to the quarterly PM checklist"])),
                  B("Level not checked on rounds", R(
                      "Oil level is not part of the shift lubrication route", "Man",
                      prevent=["Add sight-glass level to the shift rounds with a tick-sheet",
                               "Mark min / max on every sight glass"])),
              ])),
              B("Wrong or contaminated oil was topped up", R(
                  "No lubricant schedule or labelling, so the wrong grade gets used", "Man",
                  prevent=["Label every lube point with the oil grade",
                           "Keep a lubrication schedule and train the crew on it"])),
              B("Water or slurry got into the bearing housing", R(
                  "Seal leakage sprays onto the bearing housing; no deflector or labyrinth seal", "Machine",
                  prevent=["Fit a deflector / labyrinth seal on the bearing housing",
                           "Fix seal leaks promptly"])),
          ]), case="KB-0650"),
        C("cav", "Cavitation from starved suction", "Method", ["flow", "noise", "pressure", "level"], [
            "Raise the suction tank level above the minimum submergence",
            "Open the suction valve fully and clean the suction strainer",
            "Check suction flanges for air ingress",
            "Restart and listen for the gravel-like cavitation noise to stop"],
          why=W("Why was the suction starved?", [
              B("Tank level was run below the minimum", W("Why was the level allowed to fall that low?", [
                  B("Level reading is wrong", R(
                      "Level transmitter fouled or out of calibration", "Measurement",
                      prevent=["Calibrate the level transmitter and clean it monthly",
                               "Cross-check against a local gauge on rounds"])),
                  B("No low-level trip on the pump", R(
                      "Pump has no low-level protection", "Machine",
                      prevent=["Add a low-level trip / dry-run protection interlock to the pump"])),
                  B("Feed into the tank stopped", R(
                      "Upstream transfer was not coordinated with this pump's run schedule", "Method",
                      prevent=["Link pump start/stop to tank level in the control logic",
                               "Agree a transfer schedule between areas"])),
              ])),
              B("Suction strainer or line partly blocked", R(
                  "Suction strainer cleaning is not scheduled", "Method",
                  prevent=["Schedule suction strainer cleaning and add a differential-pressure gauge"])),
              B("Suction valve was not fully open", R(
                  "Valve position not verified at start-up", "Man",
                  prevent=["Add valve line-up to the start-up checklist", "Fit open/close position indicators"])),
          ])),
        C("mis", "Shaft misalignment or loose baseplate", "Method", ["vibration", "coupling", "sound"], [
            "Stop the pump under LOTO",
            "Replace the worn coupling element",
            "Check for soft foot, re-torque the base bolts and laser-align pump to motor",
            "Restart and trend vibration for one shift"],
          why=W("Why is the pump out of alignment?", [
              B("Alignment not done properly after the last maintenance", R(
                  "No laser alignment in the reassembly procedure", "Method",
                  prevent=["Make laser alignment with a recorded result mandatory after any coupling work",
                           "Train fitters on soft-foot checks"])),
              B("Pipe strain pulls the pump out of line", R(
                  "Pipework not independently supported at the pump flanges", "Machine",
                  prevent=["Add pipe supports so flanges bolt up without force"])),
              B("Base bolts work loose from vibration", R(
                  "Base bolts not re-torqued in PM; grout or plinth damaged", "Method",
                  prevent=["Add base-bolt torque check to quarterly PM", "Repair grout / plinth"])),
          ])),
        C("wear", "Worn impeller, wear plate or stator (lost pumping head)", "Material", ["flow", "pressure"], [
            "Plan a pump overhaul: replace the impeller and wear plate (or rotor/stator on a progressive cavity pump)",
            "Set the impeller-to-wear-plate clearance to the OEM value",
            "Confirm shut-off head and flow after rebuild"],
          why=W("Why did the wetted parts wear early?", [
              B("Abrasive solids in the slurry", R(
                  "Grit load in the feed is not controlled", "Material",
                  prevent=["Improve grit removal upstream", "Use hardened or rubber-lined wear parts"])),
              B("Clearance never re-adjusted", R(
                  "Wear-plate clearance adjustment is not in PM", "Method",
                  prevent=["Check and re-set the wear-plate clearance every 6 months"])),
              B("Progressive cavity pump ran dry and burnt the stator", R(
                  "No dry-run protection on the progressive cavity pump", "Machine",
                  prevent=["Fit a stator temperature or dry-run sensor and interlock it"])),
          ])),
        C("elec", "Motor or electrical fault", "Machine", ["trip", "current", "motor"], [
            "Isolate the motor at the MCC and apply LOTO",
            "Have the electrician check insulation resistance, terminal tightness and all three phase currents",
            "Check the overload relay setting against the motor nameplate",
            "Restart and record the running current"],
          why=W("What caused the electrical fault?", [
              B("One phase missing or unbalanced", R(
                  "Loose terminal or failing contactor in the MCC", "Machine",
                  prevent=["Thermographic scan of MCC panels every quarter", "Re-torque terminals in PM"])),
              B("Moisture in the motor terminal box", R(
                  "Terminal box not sealed against washdown water", "Environment",
                  prevent=["Fit proper cable glands and gaskets; avoid hosing near motors"])),
              B("Overload set wrong for the motor", R(
                  "Protection settings not verified after motor replacement", "Measurement",
                  prevent=["Record and verify overload settings in the motor register"])),
          ])),
    ],
    "questions": [
        Q("flush", "Can you look at the seal flushing water at the gland — is it flowing?", [
            ("Flowing normally", {"seal": 0.3, "imp": 1.1, "brg": 1.1, "cav": 1.1, "mis": 1.1, "wear": 1.1, "elec": 1.1}),
            ("Weak or on and off", {"seal": 2.2}),
            ("No flow at all", {"seal": 3.5, "imp": 0.9, "brg": 0.9, "cav": 0.9, "mis": 0.9, "wear": 0.9, "elec": 0.9}),
        ], ["seal", "leakage", "leak"],
          how="Find the small flush line entering the seal housing. Check its rotameter or sight glass, or crack the "
              "vent and feel for flow. Stay clear of the rotating shaft.",
          purpose="Missing flush water is the most common reason a slurry pump seal fails."),
        Q("noise", "Stand by the casing for a moment. What does the pump sound like?", [
            ("Smooth hum", {"seal": 1.3, "imp": 0.5, "brg": 0.5, "cav": 0.4, "mis": 0.6, "wear": 1.2, "elec": 1.1}),
            ("Gravel or crackling", {"seal": 0.8, "imp": 0.9, "brg": 0.7, "cav": 3.5, "mis": 0.8, "wear": 1.3, "elec": 0.8}),
            ("Rhythmic thump", {"seal": 0.8, "imp": 3.0, "brg": 0.9, "cav": 0.9, "mis": 1.5, "wear": 0.9, "elec": 0.8}),
            ("Grinding or whine from the bearing end", {"seal": 0.7, "imp": 0.7, "brg": 3.2, "cav": 0.7, "mis": 1.3, "wear": 0.7, "elec": 0.9}),
            ("Shaking more than noise, felt at the base", {"mis": 3.2, "imp": 1.4, "brg": 1.0, "seal": 0.7, "cav": 0.7, "wear": 0.7, "elec": 0.8}),
            ("Electrical hum or buzz from the motor", {"elec": 3.5, "seal": 0.8, "imp": 0.7, "brg": 0.8, "cav": 0.7, "mis": 0.8, "wear": 0.8}),
        ], ["vibration", "sound", "noise"], {"tag": "vibration_mm_s", "option": 0, "above": 4.5},
          how="Listen at the casing and then at the bearing housing; a screwdriver held to the housing works as a stethoscope.",
          purpose="Each failure has its own sound: cavitation crackles, a ragged impeller thumps, a bad bearing grinds."),
        Q("dp", "What does the discharge pressure gauge read compared with normal?", [
            ("Normal", {"seal": 1.2, "imp": 0.5, "brg": 1.3, "cav": 0.6, "mis": 1.2, "wear": 0.3, "elec": 1.0}),
            ("Low and fluctuating", {"seal": 1.0, "imp": 1.6, "brg": 0.8, "cav": 2.6, "mis": 0.9, "wear": 1.0, "elec": 0.9}),
            ("Low but steady", {"seal": 1.1, "imp": 2.4, "brg": 0.9, "cav": 0.9, "mis": 0.9, "wear": 2.8, "elec": 0.9}),
        ], ["pressure", "flow"],
          how="Read the local gauge on the discharge line. Normal for slurry RC pumps here is about 2.4 bar; use the "
              "value on the gauge tag if marked.",
          purpose="Pressure tells me whether the pump is still making head, and whether the suction is steady."),
        Q("oil", "Check the bearing housing — what are the oil level and colour like?", [
            ("Level OK, oil clean", {"seal": 1.2, "imp": 1.2, "brg": 0.3, "cav": 1.2, "mis": 1.1, "wear": 1.2, "elec": 1.2}),
            ("Low, leaking at the oil seal", {"brg": 3.5, "seal": 0.8, "imp": 0.8, "cav": 0.8, "mis": 0.9, "wear": 0.8, "elec": 0.8}),
            ("Dark, burnt or milky", {"brg": 2.5, "mis": 1.6, "seal": 0.9, "imp": 1.0, "cav": 0.9, "wear": 0.9, "elec": 0.9}),
        ], ["oil", "bearing", "vibration", "temperature"],
          how="Read the sight glass on the bearing housing. Milky oil means water has got in; dark or burnt smell means overheating.",
          purpose="Most bearing failures start with low or contaminated oil."),
        Q("level", "What's the level in the suction tank right now?", [
            ("Well above the minimum", {"cav": 0.3, "seal": 1.05, "imp": 1.05, "brg": 1.05, "mis": 1.05, "wear": 1.05, "elec": 1.05}),
            ("Near or below the minimum", {"cav": 3.0, "seal": 1.3, "imp": 0.9, "brg": 0.95, "mis": 0.95, "wear": 0.95, "elec": 0.95}),
        ], ["flow", "level"],
          how="Read the level on SCADA or the local gauge, and compare with the minimum marked for this pump.",
          purpose="A low tank lets air and vapour into the pump — that's cavitation."),
        Q("align", "With the pump stopped under LOTO, look at the coupling and base bolts. What do you see?", [
            ("Coupling fine, bolts tight", {"mis": 0.2, "seal": 1.1, "imp": 1.1, "brg": 1.0, "cav": 1.1, "wear": 1.1, "elec": 1.1}),
            ("Coupling element worn or cracked", {"mis": 4.0, "brg": 1.1, "seal": 0.8, "imp": 0.8, "cav": 0.8, "wear": 0.8, "elec": 0.8}),
            ("Base bolts loose or visible offset", {"mis": 4.5, "brg": 1.1, "seal": 0.8, "imp": 0.8, "cav": 0.8, "wear": 0.8, "elec": 0.8}),
        ], ["vibration", "coupling"],
          how="Only with the pump isolated and locked out: remove the coupling guard, check the rubber element for cracks "
              "and run a straight edge across both coupling halves. Try each base bolt with a spanner.",
          purpose="Misalignment shows up as vibration and then kills bearings and seals."),
        Q("leak", "Is anything leaking? Where from?", [
            ("From the seal or gland", {"seal": 3.5, "brg": 0.7, "imp": 0.8, "cav": 0.9, "mis": 1.1, "wear": 0.9, "elec": 0.9}),
            ("Oil from the bearing housing", {"brg": 3.2, "seal": 0.8, "imp": 0.8, "cav": 0.8, "mis": 1.2, "wear": 0.8, "elec": 0.8}),
            ("Nothing leaking", {"seal": 0.25, "brg": 0.6, "imp": 1.2, "cav": 1.2, "mis": 1.1, "wear": 1.2, "elec": 1.2}),
        ], ["seal", "leakage", "leak", "oil"],
          how="Walk round the pump and look under it: slurry dripping at the shaft where it enters the casing is the "
              "seal; oil on the bearing housing or baseplate is the oil seal.",
          purpose="Where the leak comes from separates a seal problem from a bearing problem straight away."),
        Q("backflush", "If you back-flush the line, does the pump come back to normal for a while?", [
            ("Yes, recovers for a while", {"imp": 3.5, "wear": 0.4, "cav": 1.2, "seal": 0.9, "brg": 0.8, "mis": 0.8, "elec": 0.8}),
            ("No change", {"imp": 0.35, "wear": 1.8, "cav": 0.9, "seal": 1.0, "brg": 1.0, "mis": 1.0, "elec": 1.0}),
        ], ["flow", "choke", "vibration"],
          how="Follow the area back-flush procedure: stop the pump, open the flushing water connection on the discharge "
              "side for a few minutes, then restart and watch pressure and noise.",
          purpose="Fibres wash out with a back-flush and the pump recovers; a worn impeller doesn't."),
        Q("shutoff", "Can you do a quick shut-off test: close the discharge valve for a few seconds — does pressure reach "
                     "its usual shut-off value?", [
            ("Yes, reaches normal shut-off", {"wear": 0.25, "imp": 0.8, "seal": 1.1, "brg": 1.1, "cav": 1.0, "mis": 1.1, "elec": 1.1}),
            ("No, well below normal", {"wear": 3.5, "imp": 1.6, "seal": 0.9, "brg": 0.9, "cav": 1.0, "mis": 0.9, "elec": 0.9}),
        ], ["flow", "pressure"],
          how="Centrifugal pumps only: close the discharge valve slowly, read the gauge, then reopen within 10 seconds. "
              "Never do this on a progressive cavity pump — check its flow on the flowmeter instead.",
          purpose="If the pump can't reach shut-off head, the impeller or wear plate is worn."),
        Q("current", "Ask the control room or check the MCC: how does the motor current look?", [
            ("Normal and steady", {"elec": 0.25, "seal": 1.1, "imp": 1.0, "brg": 1.0, "cav": 1.0, "mis": 1.0, "wear": 1.1}),
            ("Higher than nameplate", {"elec": 2.0, "mis": 1.6, "brg": 1.6, "imp": 1.2, "seal": 0.9, "cav": 0.8, "wear": 0.8}),
            ("Trips on overload", {"elec": 3.5, "brg": 1.3, "mis": 1.2, "imp": 1.1, "seal": 0.8, "cav": 0.8, "wear": 0.8}),
            ("Unequal between phases", {"elec": 5.0, "seal": 0.8, "imp": 0.8, "brg": 0.8, "cav": 0.8, "mis": 0.8, "wear": 0.8}),
        ], ["trip", "current", "motor"], {"tag": "motor_current_a", "option": 0, "above": 20},
          how="Read the ammeter on the MCC door or the SCADA current trend, and compare with the full-load amps on the motor nameplate.",
          purpose="Current separates electrical problems from mechanical ones."),
    ],
}

MAINTENANCE = {
    "Pump": {
        "summary": "Slurry pumps (RC, transfer, feed, CDT/PST) handle abrasive, fibrous digestate; water pumps handle "
                   "cooling and service water. Seals, bearings and wet-end wear are the main maintenance items.",
        "pm": [
            ("Every shift", "Check seal flush flow, seal leakage, bearing oil level, abnormal noise and discharge pressure"),
            ("Weekly", "Clean suction strainers; check coupling guard and base bolts"),
            ("Monthly", "Vibration and bearing temperature readings; grease motor bearings per OEM"),
            ("6-monthly", "Check and reset impeller / wear-plate clearance; change bearing-housing oil"),
            ("Yearly", "Overhaul: bearings, oil seals, mechanical seal, laser alignment"),
        ],
        "failure_modes": ["Seal failure from dry running or grit", "Impeller ragging by fibres", "Cavitation at low tank level",
                          "Bearing failure from lost lubrication", "Wet-end wear from abrasive solids", "Misalignment after maintenance"],
        "operating_limits": [("Bearing housing temperature", "< 80 °C"), ("Vibration (ISO 10816, class II)", "< 4.5 mm/s"),
                             ("Seal flush pressure", "≈ 1 bar above stuffing-box pressure"),
                             ("Discharge pressure, RC pump", "≈ 2.4 bar")],
    },
}

CASES = [
    K("KB-0298", ["Pump"], ["seal", "leakage"], "Major slurry leakage through pump mechanical seal",
      "Seal face damage from dry running and abrasive grit",
      "Isolated and drained pump, replaced mechanical seal, restored flushing water supply",
      why=["Why did the seal leak? Seal faces cracked and grooved",
           "Why were the faces damaged? The seal ran without flush water",
           "Why was there no flush water? Flush valve left closed after maintenance",
           "Why was it left closed? Restart checklist has no flush line-up step"],
      category="Method", prevent="Flush-water line-up added to restart checklist; flow switch on flush line"),
    K("KB-0455", ["Pump"], ["vibration", "flow"], "Slurry pump vibration rising over two shifts with low discharge pressure",
      "Impeller choked with fibres causing imbalance",
      "Back-flushed, opened casing and cleaned impeller, cleaned suction strainer",
      why=["Why the vibration? Impeller wrapped with fibres",
           "Why fibres at the pump? Upstream screen bypassed",
           "Why bypassed? Screen blocked every few hours and crew bypassed it to keep feeding"],
      category="Method", prevent="Screen cleaning frequency doubled; bypass valve locked and made a permit item"),
    K("KB-0650", ["Pump", "Blower"], ["oil leakage", "oil", "bearing"], "Oil leakage from pump bearing housing",
      "Hardened bearing-housing oil seal",
      "Replaced oil seal, refilled to the sight-glass mark, checked bearing condition",
      why=["Why the oil leak? Lip seal hardened and cracked",
           "Why hardened? Not replaced at the last bearing overhaul",
           "Why not replaced? Overhaul task list did not include oil seals"],
      category="Method", prevent="Oil seals added to the bearing overhaul task list"),
]
