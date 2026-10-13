"""Gas movers: blowers and compressors.

  Blower      BUU Gas Blower 1/2 (raw-biogas boosters after the H2S scrubber / filter skid, feeding the LP compressors),
              digester Dx Blower 1/2 (air dosing for biological desulphurisation / membrane-roof support air),
              HWG-area Flare Blower and LDT Top Blower 1/2. Mostly side-channel (regenerative) or centrifugal,
              some belt-driven roots units.
  Compressor  BUU LP 1–4 (low-pressure reciprocating raw-biogas compressors ahead of the chiller and membranes),
              HP 1–3 (high-pressure CBG compressors to the ~250 bar cascade), SLS Plant Air Compressor 1/2.

Sources (types): reciprocating-compressor OEM operation & maintenance manuals (valve, ring and packing service,
crankcase lubrication, interstage pressure / temperature tables); gas-compressor trade guidance (Compressor Tech2 /
GMRC-style articles on why cylinder valves fail: liquids, debris, wrong valve lift, pulsation; suction knock-out
pot sizing); biogas plant O&M references (raw biogas H2S 50–1000+ ppm, saturation moisture, siloxanes and media
fines raise valve wear 2–3x versus natural gas); ATEX side-channel blower OEM manuals (condensate drains,
sealed-for-life bearings, maximum differential pressure and temperature); CNG station compressor RCA papers;
plant incident history (incident_log_2026.csv, incident_log_gas_movers_hwg.csv), SOP-CMP-03, SOP-ROT-01 (LOTO)
and OEM_HP_CBG_Compressor_Maintenance / OEM_Biogas_Blower_Maintenance in data/docs.
"""
from .dsl import B, C, K, Q, R, W

TREES = {}

# ---------------------------------------------------------------------------------------------------------------------
# Blower
# ---------------------------------------------------------------------------------------------------------------------
TREES["Blower"] = {
    "causes": [
        C("gasket", "Failed discharge flange gasket — gas leaking from the joint", "Machine",
          ["gas", "smell", "flange", "leak"], [
            "Raise the alarm, keep people and ignition sources away and confirm the leak with a portable gas detector (GAS-01)",
            "Stop the blower, isolate suction and discharge valves and vent / purge the section to flare with nitrogen",
            "Replace the discharge flange gasket with the specified biogas-rated gasket; torque bolts in a cross pattern",
            "Leak test with soap solution at operating pressure and re-sweep with the gas detector before handing back"],
          why=W("Why did the gasket fail?", [
              B("Wrong gasket material for wet, H2S-laden gas", W("Why was the wrong gasket fitted?", [
                  B("Store issued whatever gasket fitted", R(
                      "No gasket specification per line in the stores / maintenance system", "Material",
                      prevent=["Create a line-class gasket list (e.g. EPDM/graphite, H2S-resistant) and stock it",
                               "Tag each flange spool with its gasket spec"])),
                  B("Fitter not aware of the service", R(
                      "Fitters not trained on biogas-service gasket and bolting requirements", "Man",
                      prevent=["Toolbox talk on gasket selection and torque for gas lines",
                               "Add gasket spec check to the permit close-out"])),
              ])),
              B("Bolts loosened by vibration and heat cycles", W("Why did the bolts lose their load?", [
                  B("Never re-torqued after start-up", R(
                      "No hot re-torque step after flange work", "Method",
                      prevent=["Add a re-torque check 24 h after any flange remake",
                               "Record torque values on the job card"])),
                  B("Blower vibration above limit for weeks", R(
                      "Vibration trend not acted on until something breaks", "Method",
                      prevent=["Set a vibration alarm at 4.5 mm/s with a defined response",
                               "Add flange bolt check to the monthly blower round"])),
              ])),
              B("Pipe strain on the blower flange", R(
                  "Discharge pipework not supported independently of the blower", "Machine",
                  prevent=["Add pipe supports / a flexible bellows so the flange bolts up without force"])),
          ], how="Look at the old gasket: hardened, cracked or swollen material points to the wrong grade; an even "
                 "but thin, crushed gasket with loose bolts points to lost bolt load."),
          case="KB-0501"),
        C("brg", "Bearing wear from lost or wrong lubrication", "Machine", ["bearing", "vibration", "grease", "rumble"], [
            "Stop the blower and apply LOTO (SOP-ROT-01)",
            "Check bearing play and noise by hand; replace both bearings if rough",
            "Clean the housing and lubricate with the OEM grease grade and quantity (no over-greasing)",
            "Restart and trend vibration and bearing temperature for one shift"],
          why=W("Why did the bearing run short of good lubrication?", [
              B("Wrong grease or over-greased", W("Why was the lubrication wrong?", [
                  B("No grease grade marked at the nipple", R(
                      "Lubrication points not labelled; no lubrication schedule", "Man",
                      prevent=["Label each grease point with grade and shots", "Issue a lube route card per blower"])),
                  B("Greased 'by feel' until it purges", R(
                      "Crew not trained on grease quantity; over-greasing overheats bearings", "Man",
                      prevent=["Train on grease quantity per OEM", "Use a metered grease gun"])),
              ])),
              B("Bearing past its life (sealed-for-life unit)", R(
                  "Sealed bearings run to failure — no running-hour based replacement", "Method",
                  prevent=["Replace sealed bearings at the OEM running-hour interval",
                           "Add monthly vibration / bearing-temperature readings to PM"])),
              B("Condensate or gas got into the bearing", R(
                  "Shaft seal worn so wet gas reaches the bearing", "Machine",
                  prevent=["Replace shaft seals at bearing overhaul", "Drain casing condensate on every round"])),
          ]), case="KB-0650"),
        C("cond", "Condensate or sulphur deposits in the casing (impeller fouling / imbalance)", "Material",
          ["condensate", "water", "vibration", "deposit"], [
            "Stop the blower under LOTO and open the casing low-point drain to a closed drain",
            "Open the casing, clean water, sludge and sulphur crust from the impeller and side channel",
            "Check impeller for erosion and clearance; balance if material was lost",
            "Check the upstream knock-out pot / condensate trap drains before restart"],
          why=W("Why is liquid or deposit getting into the blower?", [
              B("Upstream condensate trap not draining", W("Why is the trap not draining?", [
                  B("Trap blocked with sludge", R(
                      "Condensate traps have no cleaning interval", "Method",
                      prevent=["Clean condensate traps monthly; check daily by opening the test cock"])),
                  B("Auto-drain valve failed and nobody noticed", R(
                      "No alarm or round check on condensate pot level", "Measurement",
                      prevent=["Fit a high-level switch on the knock-out pot", "Add pot level to shift rounds"])),
              ])),
              B("Gas line falls back toward the blower", R(
                  "Gas line has no continuous slope to a drain point; condensate pools at the blower", "Machine",
                  prevent=["Re-slope the line (≥1%) to a drain point upstream of the blower"])),
              B("Sulphur from biological desulphurisation carried over", R(
                  "Air dosing for desulphurisation not controlled, elemental sulphur forms in the gas path", "Method",
                  prevent=["Control air dosing to O2 target (typically < 0.5–1% in biogas)", "Inspect blower casing quarterly"])),
          ])),
        C("belt", "Drive belt slack or pulley misalignment (belt-driven units)", "Method", ["belt", "squeal", "slip"], [
            "Stop the blower and apply LOTO — never adjust a running belt",
            "Replace worn belts as a matched set",
            "Align pulleys with a straight edge or laser",
            "Tension to OEM deflection and re-check after 4 running hours"],
          why=W("Why did the belts slip?", [
              B("Tension never re-checked after fitting", R(
                  "No run-in re-tension step after belt replacement", "Method",
                  prevent=["Add a 4-hour and 24-hour re-tension check to the belt job card"])),
              B("Pulleys out of line", W("Why are the pulleys misaligned?", [
                  B("Aligned by eye after motor change", R(
                      "No alignment tool or recorded alignment in the procedure", "Method",
                      prevent=["Issue a belt-alignment laser and record the result on the job card"])),
                  B("Motor base slid on its slots", R(
                      "Motor base adjusting bolts not locked", "Machine",
                      prevent=["Fit lock nuts / jacking screws to the motor base"])),
              ])),
              B("Odd belts mixed from different batches", R(
                  "Belts replaced singly instead of as matched sets", "Man",
                  prevent=["Stock matched sets only and train the crew to replace the full set"])),
          ])),
        C("backpr", "Running against high back-pressure (closed valve, stuck NRV)", "Method",
          ["pressure", "overheat", "current", "throttle"], [
            "Check the discharge line-up: discharge valve, non-return valve and downstream isolation fully open",
            "Check the pressure relief / bypass valve setting",
            "Restart and confirm differential pressure and motor current are inside the OEM curve"],
          why=W("Why was the blower pushing against a restriction?", [
              B("Valve left part-closed after maintenance", R(
                  "No valve line-up check in the blower start-up procedure", "Method",
                  prevent=["Add a valve line-up checklist to the start-up procedure",
                           "Fit position indicators on manual valves"])),
              B("Downstream filter / scrubber choked", R(
                  "Downstream dP not trended, so a choking filter loads the blower", "Measurement",
                  prevent=["Trend downstream filter dP with an alarm", "Change filter element at a set dP"])),
              B("Non-return valve sticking", R(
                  "NRV not in the PM plan; sulphur and sludge make it stick", "Method",
                  prevent=["Inspect and clean the NRV every 6 months"])),
          ])),
        C("heat", "Overheating from poor enclosure ventilation / high ambient", "Environment",
          ["hot", "temperature", "ambient", "trip"], [
            "Open the enclosure louvres / restore the ventilation fan",
            "Clean the motor cooling fins and fan cowl",
            "Check the discharge temperature against the OEM maximum before restart"],
          why=W("Why is the blower running so hot?", [
              B("Ventilation fan or louvres not working", R(
                  "Enclosure ventilation not part of the PM rounds", "Method",
                  prevent=["Add enclosure fan / louvre check to the daily round", "Fit an enclosure high-temperature alarm"])),
              B("Summer ambient above the design value", R(
                  "Enclosure designed without margin for site summer temperatures", "Environment",
                  prevent=["Add forced ventilation or shading", "Review blower rating at peak ambient"])),
              B("Dust and debris covering the motor", R(
                  "Housekeeping around the blower skid not scheduled", "Man",
                  prevent=["Weekly housekeeping of the skid", "Cover dust sources near the enclosure"])),
          ])),
        C("sensor", "Faulty pressure switch or transmitter (false trip / wrong reading)", "Measurement",
          ["alarm", "reading", "transmitter", "false"], [
            "Compare the local gauge with the SCADA reading",
            "Check the impulse line for condensate or blockage; drain and blow through",
            "Calibrate or replace the transmitter / pressure switch"],
          why=W("Why is the instrument reading wrong?", [
              B("Impulse line full of condensate", R(
                  "Impulse lines not sloped / no drain pots on wet-gas service", "Machine",
                  prevent=["Re-route impulse lines with slope and drain pots", "Drain impulse lines monthly"])),
              B("Transmitter out of calibration", R(
                  "Gas-train instruments not in the calibration schedule", "Measurement",
                  prevent=["Put all BUU pressure instruments on a 6-monthly calibration plan"])),
              B("Wrong set-point after a panel change", R(
                  "No management of change for trip set-points", "Method",
                  prevent=["Keep a trip set-point register and verify after any panel work"])),
          ])),
    ],
    "questions": [
        Q("gasdet", "Please sweep around the casing, shaft seal and flanges with your portable gas detector. What does it read?", [
            ("0% LEL everywhere", {"gasket": 0.15}),
            ("Detected at a flange joint", {"gasket": 4.5, "brg": 0.8, "cond": 0.8, "belt": 0.8, "backpr": 0.8,
                                             "heat": 0.8, "sensor": 0.8}, ["gas_leak"]),
            ("Detected at the shaft seal", {"gasket": 2.5, "brg": 1.4, "cond": 1.2, "belt": 0.7, "backpr": 0.8,
                                             "heat": 0.7, "sensor": 0.7}, ["gas_leak"]),
        ], ["gas", "smell", "leak"],
          how="Wear your personal H2S/LEL monitor. Zero the portable detector in fresh air, then hold it slowly 2–5 cm "
              "from each flange, the shaft seal and drain points. Approach from upwind. If it alarms (10% LEL or "
              "10 ppm H2S), back off, keep ignition sources away and call the control room.",
          purpose="A gas leak is a fire and toxic hazard; it has to be found and isolated before anything else."),
        Q("sound", "Stand near the blower for a moment. What does it sound like?", [
            ("Squeal at start-up", {"belt": 4.0, "brg": 0.8, "gasket": 0.5, "cond": 0.6, "backpr": 0.7, "heat": 0.7,
                                    "sensor": 0.5}),
            ("Continuous rumble or growl", {"brg": 3.5, "cond": 1.3, "belt": 0.7, "gasket": 0.6, "backpr": 0.8,
                                            "heat": 0.8, "sensor": 0.5}, ["rotating_abnormal"]),
            ("Whoosh or hiss", {"gasket": 3.0, "brg": 0.6, "cond": 0.8, "belt": 0.6, "backpr": 1.2, "heat": 0.7,
                                "sensor": 0.6}),
            ("Normal running sound", {"brg": 0.4, "belt": 0.4, "cond": 0.7, "gasket": 0.9, "backpr": 1.1, "heat": 1.6,
                                      "sensor": 2.2}),
            ("Pulsing, rising whine as flow drops", {"backpr": 3.5, "cond": 1.6, "brg": 0.8, "belt": 0.7, "gasket": 0.6,
                                                     "heat": 0.9, "sensor": 0.6}),
        ], ["sound", "noise", "vibration", "squeal"], {"tag": "vibration_mm_s", "option": 3, "above": 4.5},
          how="Listen from the walkway first, then at each bearing housing. Don't touch or lean over the coupling or "
              "belt guard while it runs.",
          purpose="Belts squeal, bearings growl, leaks hiss and a blower fighting back-pressure pulses — the sound "
                  "narrows it down fast."),
        Q("bearing", "Point an IR thermometer at the bearing housings. How hot are they?", [
            ("Below 70°C", {"brg": 0.3, "heat": 0.6, "backpr": 0.8}),
            ("Above 70°C", {"brg": 3.0, "heat": 2.0, "backpr": 1.5, "gasket": 0.8, "belt": 1.1, "sensor": 0.6, "cond": 1.0}),
        ], ["bearing", "temperature", "hot"], {"tag": "bearing_temp_c", "option": 0, "above": 75},
          how="Aim the IR gun at the bare metal of each bearing housing from about 30 cm, away from the belt or "
              "coupling. Painted surfaces read a little low.",
          purpose="Hot bearings mean they are failing or the whole machine is overheating."),
        Q("drain", "Open the casing low-point drain into the closed drain. What comes out?", [
            ("Dry, or just a few drops", {"cond": 0.25}),
            ("Water or sludge runs out", {"cond": 4.5, "brg": 0.9, "gasket": 0.9, "belt": 0.8, "backpr": 0.9, "heat": 0.8,
                                          "sensor": 1.1}),
            ("Yellow sulphur crust or paste", {"cond": 3.5, "backpr": 1.4, "brg": 1.0, "gasket": 0.9, "belt": 0.8,
                                               "heat": 0.8, "sensor": 0.9}),
        ], ["condensate", "water", "vibration"],
          how="Wear gloves and goggles and keep your gas monitor on — drained liquid can release H2S. Open the drain "
              "slowly to the closed drain or a bucket, never toward your face.",
          purpose="Water or sulphur in the casing unbalances the impeller and corrodes it."),
        Q("trap", "Check the condensate trap / knock-out pot just upstream of the blower. Is it draining?", [
            ("Yes — pot empty, drain working", {"cond": 0.3}),
            ("Pot full, or water spurts from the test cock", {"cond": 4.0, "backpr": 1.2, "sensor": 1.2, "gasket": 0.9,
                                                              "brg": 0.9, "belt": 0.8, "heat": 0.8}),
        ], ["condensate", "water", "drain"],
          how="Keep your gas monitor on. Read the pot level glass if there is one, or crack the test cock briefly "
              "into the closed drain and see whether gas or water comes out. Close it again straight away.",
          purpose="A full condensate pot sends water straight into the blower casing."),
        Q("belts", "With the blower stopped under LOTO, take a look at the drive. What do you see?", [
            ("Belts tight and pulleys in line", {"belt": 0.2}),
            ("Glazed, cracked or slack belts / pulleys offset", {"belt": 4.5, "brg": 1.2, "gasket": 0.8, "cond": 0.8,
                                                                 "backpr": 0.8, "heat": 0.8, "sensor": 0.8}),
            ("Direct drive — no belts", {"belt": 0.1}),
        ], ["belt", "squeal"],
          how="Only with the blower stopped, isolated and locked out (SOP-ROT-01): remove the belt guard, press each "
              "belt mid-span (about 15 mm deflection is typical), look for shiny glazed sides and cracks, and lay a "
              "straight edge across both pulley faces.",
          purpose="Slipping belts wear out fast, overheat and cut the blower's flow."),
        Q("lineup", "Walk the discharge line. Are the valves lined up as per the start-up sheet?", [
            ("All open as per line-up", {"backpr": 0.25}),
            ("A valve part-closed, or NRV stuck", {"backpr": 4.5, "heat": 1.2, "gasket": 0.8, "brg": 0.9, "cond": 0.9,
                                                    "belt": 0.8, "sensor": 0.9}),
        ], ["pressure", "flow", "current"],
          how="Follow the pipe from the blower outlet to the next unit. Check each manual valve handle position and "
              "listen at the non-return valve for chatter. Do not operate valves without the control room's OK.",
          purpose="A blower pushing against a closed or stuck valve overheats and loses flow."),
        Q("enclosure", "How does it feel around the blower and motor — is the enclosure ventilation working?", [
            ("Normal, fan and louvres working", {"heat": 0.25}),
            ("Very hot, louvres blocked or fan off", {"heat": 4.5, "brg": 1.2, "backpr": 1.0, "gasket": 0.8, "cond": 0.8,
                                                      "belt": 0.9, "sensor": 0.9}),
        ], ["hot", "temperature", "ambient"],
          how="Check the enclosure fan is running and louvres are open and clear. Feel the air at the outlet. Note the "
              "room temperature if there is a thermometer.",
          purpose="Blowers and their motors derate fast when the enclosure gets too hot."),
        Q("gauge", "Compare the local pressure gauge on the blower with the SCADA reading. Do they agree?", [
            ("Both agree", {"sensor": 0.2}),
            ("They disagree, or SCADA jumps", {"sensor": 4.5, "cond": 1.3, "gasket": 0.8, "brg": 0.8, "belt": 0.8,
                                               "backpr": 0.9, "heat": 0.8}),
        ], ["alarm", "reading", "pressure", "trip"],
          how="Read the local gauge at the blower discharge and ask the control room for the same tag at the same "
              "moment. A difference of more than about 10% matters.",
          purpose="If the instrument is wrong, the 'fault' may only be a false trip."),
        Q("current", "Ask the control room or check the MCC: how does the motor current look?", [
            ("Normal and steady", {"backpr": 0.5, "brg": 0.8, "heat": 0.9, "sensor": 1.4, "gasket": 1.2, "cond": 0.9,
                                   "belt": 0.9}),
            ("Higher than usual", {"backpr": 2.5, "brg": 1.6, "cond": 1.5, "heat": 1.2, "gasket": 0.9, "belt": 0.8,
                                   "sensor": 0.6}),
            ("Trips on overload", {"heat": 2.2, "backpr": 2.0, "brg": 1.3, "cond": 1.2, "gasket": 0.6, "belt": 0.8,
                                   "sensor": 1.0}),
        ], ["trip", "current", "motor"], {"tag": "motor_current_a", "option": 0, "above": 20},
          how="Read the ammeter on the MCC door or the SCADA current trend and compare with the motor nameplate "
              "full-load amps.",
          purpose="Current shows whether the blower is mechanically loaded or the problem is elsewhere."),
    ],
}

# ---------------------------------------------------------------------------------------------------------------------
# Compressor
# ---------------------------------------------------------------------------------------------------------------------
_CMP = ["oilleak", "valve", "particle", "gasket", "liquid", "rings", "cooling", "sensor"]


def _o(strong: dict, rest: float = 1.0) -> dict:
    """Likelihoods: the listed causes, every other compressor cause at `rest`."""
    return {c: strong.get(c, rest) for c in _CMP}


TREES["Compressor"] = {
    "causes": [
        C("oilleak", "Crankcase oil leak starving the big-end bearings", "Machine",
          ["oil level", "oil leakage", "oil", "knock"], [
            "Stop the compressor and keep it locked out — OIL-01 blocks restart below 60% oil level",
            "Trace and fix the leak (drain plug gasket, crankcase cover, crankshaft oil seal, oil cooler fittings)",
            "Inspect big-end and main bearings and the oil pump strainer before restart",
            "Top up crankcase oil to 60–80% of the sight glass with the specified grade",
            "Restart unloaded; confirm oil pressure within 10 s and that the knock has gone"],
          why=W("Why did the crankcase lose oil without anyone stopping the machine?", [
              B("Drain plug or cover gasket leaking", W("Why was the gasket leaking?", [
                  B("Old gasket reused at the last oil change", R(
                      "Oil-change procedure does not require a new drain-plug washer / gasket", "Method",
                      prevent=["Add 'new drain-plug washer and cover gasket' to the oil-change job card",
                               "Stock gasket kits per compressor model"])),
                  B("Plug over-tightened and gasket crushed", R(
                      "Torque values not given to fitters", "Man",
                      prevent=["Post torque values at the compressor and use a torque wrench"])),
              ])),
              B("Low level not noticed in time", W("Why was the falling level missed?", [
                  B("Level not logged on the shift round", R(
                      "Oil level is not a logged item on the BUU shift checksheet", "Man",
                      prevent=["Log sight-glass level each shift with min/max marked",
                               "Trend oil_level_pct on SCADA with alarm at 65%"])),
                  B("Low-oil switch bypassed or faulty", R(
                      "Low oil level / pressure trips not proof-tested", "Measurement",
                      prevent=["Proof-test low oil level and low oil pressure trips every 3 months"])),
              ])),
              B("Crankshaft oil seal worn", R(
                  "Crankshaft seals not replaced at overhaul", "Method",
                  prevent=["Replace crankshaft oil seals at every major overhaul"])),
          ], how="Clean the crankcase, run the oil pump (or turn by hand) and dust with talc — the leak path shows up."),
          case="KB-0389"),
        C("valve", "Suction / discharge valve plate or spring failure", "Machine",
          ["valve", "clatter", "sound", "vibration"], [
            "Stop and isolate the compressor; vent to flare and purge with nitrogen",
            "Remove the valve covers and inspect plates, springs and seats",
            "Replace broken plates and springs as a set; lap scored seats; fit new cover gaskets",
            "Check the suction strainer for valve fragments and debris",
            "Torque covers per OEM chart, leak test, restart and compare interstage pressures with the baseline"],
          why=W("What broke the valve plate?", [
              B("Fatigue — plates past their service life", R(
                  "Valves serviced only on failure; no running-hour based valve overhaul", "Method",
                  prevent=["Overhaul valves at the OEM interval (typically 4,000–8,000 h on biogas)",
                           "Trend valve-cover temperatures weekly to catch leaking valves early"])),
              B("Wrong parts or poor assembly", W("What went wrong at assembly?", [
                  B("Non-OEM plates or wrong spring set", R(
                      "Spare parts bought without OEM part numbers / valve lift specification", "Material",
                      prevent=["Buy valve kits by OEM part number only", "Record valve lift and spring set in the job card"])),
                  B("Valve fitted the wrong way round", R(
                      "No suction/discharge identification check in the valve procedure", "Man",
                      prevent=["Mark valve pockets and train fitters; second-person check before cover closing"])),
              ])),
              B("Liquid or debris hit the plates", R(
                  "Suction knock-out pot and strainer not maintained", "Method",
                  prevent=["Drain the suction knock-out pot each shift", "Clean the suction strainer at a set dP"])),
          ], how="Look at the broken plate: a clean fatigue crack from a port edge = age; impact marks = liquid or "
                 "debris; uneven seat wear = wrong lift or spring."),
          case="KB-0502"),
        C("particle", "Solid particle ingress at suction from the upstream scrubber / filter", "Material",
          ["particle", "powder", "strainer", "media"], [
            "Trip the compressor load line and keep it isolated (CMP-01)",
            "Inspect the suction vessel strainer and valve assemblies for particles",
            "Trace upstream: H2S scrubber media carryover and filter element integrity",
            "Clean the suction vessel, replace damaged valves, re-seat or replace the filter element",
            "Release the interlock only after the upstream fix is verified"],
          why=W("Why are particles reaching the compressor?", [
              B("Scrubber media carried over", W("Why did the media escape the scrubber?", [
                  B("Outlet mesh / distributor seal failed", R(
                      "Scrubber internals not inspected at media change", "Method",
                      prevent=["Inspect outlet mesh and perimeter seal at every media change (SOP-SCR-02)"])),
                  B("Gas velocity too high through the bed", R(
                      "Scrubber run above design flow when gas production peaks", "Method",
                      prevent=["Limit gas flow per vessel; run vessels in parallel at peaks"])),
              ])),
              B("Filter element ruptured or bypassed", R(
                  "Filter element changed only on failure; bypass used without a guard filter", "Method",
                  prevent=["Change elements at a set dP", "Lock the bypass and require a guard filter (FLT-01)"])),
              B("Pipe scale / iron sulphide from corroded carbon-steel pipe", R(
                  "Carbon-steel piping in wet, H2S-laden gas service corrodes and sheds scale", "Material",
                  prevent=["Replace with stainless steel / HDPE on the wet-gas section", "Fit a fine suction strainer"])),
          ])),
        C("gasket", "Failed flange gasket on the discharge line", "Machine", ["gas", "smell", "flange", "hiss"], [
            "Isolate the compressor and confirm the leak with a portable gas detector (GAS-01)",
            "Depressurise and purge the section to flare; no hot work",
            "Replace the discharge flange gasket (spiral-wound / ring joint on HP service)",
            "Leak test with soap solution at operating pressure; re-sweep with the gas detector"],
          why=W("Why did the discharge gasket fail?", [
              B("Pulsation and vibration loosened the joint", W("Why was there so much pulsation?", [
                  B("Pipe supports or clamps missing", R(
                      "Discharge piping supports not inspected after maintenance", "Machine",
                      prevent=["Restore and inspect pipe clamps quarterly", "Add a vibration survey of discharge piping"])),
                  B("No re-torque after start-up", R(
                      "No hot re-torque step after flange work", "Method",
                      prevent=["Re-torque flanges 24 h after start-up and record it"])),
              ])),
              B("Gasket not rated for the temperature / pressure", R(
                  "No gasket specification per line class", "Material",
                  prevent=["Create a line-class gasket schedule and stock the right gaskets"])),
              B("Gasket reused after a joint was opened", R(
                  "Fitters reuse gaskets to save time", "Man",
                  prevent=["Make 'new gasket every time' a permit close-out item"])),
          ]), case="KB-0501"),
        C("liquid", "Liquid / condensate carryover into the cylinder", "Material",
          ["water", "condensate", "liquid", "slug"], [
            "Stop the compressor; drain the suction knock-out pot and cylinder drains to the closed drain",
            "Check the oil for milky emulsion and change it if contaminated",
            "Inspect valves and pistons for impact damage before restart",
            "Restore the knock-out pot auto-drain and the gas pre-cooler / dryer"],
          why=W("Why did liquid reach the cylinder?", [
              B("Knock-out pot not draining", W("Why didn't the pot drain?", [
                  B("Auto-drain valve stuck", R(
                      "Auto-drain valves not in the PM plan", "Method",
                      prevent=["Test and clean auto-drains monthly", "Add a high-level alarm on the knock-out pot"])),
                  B("Manual drain skipped on the round", R(
                      "Manual drain points not on the shift checksheet", "Man",
                      prevent=["Add each drain point to the shift checksheet with a tick box"])),
              ])),
              B("Gas condensing in a cold suction line", R(
                  "Suction line not insulated / traced; saturated biogas condenses on cold nights", "Environment",
                  prevent=["Insulate and slope the suction line to a drain", "Keep suction gas above its dew point"])),
              B("Start-up without draining after a long stop", R(
                  "Start-up procedure has no 'drain cylinders and pot' step", "Method",
                  prevent=["Add draining and barring-over by hand to the start-up procedure"])),
          ])),
        C("rings", "Piston ring or rod packing wear (blow-by, gas at the packing vent)", "Machine",
          ["blow-by", "ring", "packing", "capacity"], [
            "Measure blow-by at the crankcase breather / packing vent and compare with the baseline",
            "Plan a cylinder overhaul: replace piston rings and rider bands; renew rod packing",
            "Check the cylinder liner and piston rod for scoring and wear",
            "Check cylinder lubrication rate on lubricated cylinders"],
          why=W("Why did the rings / packing wear early?", [
              B("Abrasive deposits in the gas", W("What is the abrasive?", [
                  B("Silica from siloxanes", R(
                      "Siloxanes not removed upstream of the compressors", "Material",
                      prevent=["Check siloxane content quarterly", "Shorten ring change interval if silica is found"])),
                  B("Iron sulphide / scrubber fines", R(
                      "Upstream filtration not fine enough for compressor suction", "Material",
                      prevent=["Fit a fine suction filter and monitor its dP"])),
              ])),
              B("Cylinder lubrication wrong", R(
                  "Cylinder lube rate and oil grade not set to OEM for wet sour gas", "Method",
                  prevent=["Set and record lubricator feed rate; use the OEM sour-gas oil grade"])),
              B("Overdue overhaul", R(
                  "Ring / packing life not tracked by running hours", "Method",
                  prevent=["Track running hours per cylinder and overhaul at OEM interval"])),
          ])),
        C("cooling", "Inadequate inter/after-cooling — high discharge temperature", "Environment",
          ["temperature", "hot", "overheat", "cooling"], [
            "Check cooling water flow and temperature, or the air-cooler fan and fins",
            "Clean fouled cooler fins / tubes and restore fan belts",
            "Compare stage discharge temperatures with the OEM table before reloading"],
          why=W("Why is cooling not keeping up?", [
              B("Cooler fins or tubes fouled", W("What fouled the cooler?", [
                  B("Dust and fibres from the site", R(
                      "Air-cooler cleaning not scheduled despite dusty site", "Environment",
                      prevent=["Clean air-cooler fins monthly (more in dry season)", "Fit insect / dust screens"])),
                  B("Scale in the water side", R(
                      "Cooling water not treated", "Material",
                      prevent=["Treat cooling water; check hardness monthly", "Descale exchanger yearly"])),
              ])),
              B("Cooling water pump / fan not running", R(
                  "No interlock between cooling flow and compressor start", "Machine",
                  prevent=["Interlock compressor start with cooling-water flow / fan running"])),
              B("Peak summer ambient", R(
                  "Coolers sized without margin for site peak ambient", "Environment",
                  prevent=["Review cooler sizing; add shading or water mist at peaks"])),
          ])),
        C("sensor", "Faulty pressure / temperature transmitter (false trip or wrong reading)", "Measurement",
          ["trip", "alarm", "reading", "transmitter"], [
            "Compare the local gauge with the SCADA reading",
            "Drain and blow through the impulse line; check for a closed root valve",
            "Calibrate or replace the transmitter / switch and verify the trip set-point"],
          why=W("Why is the instrument wrong?", [
              B("Impulse line wet or blocked", R(
                  "Impulse lines on wet gas have no slope / drain pots", "Machine",
                  prevent=["Re-route impulse lines with slope and drain pots", "Drain monthly"])),
              B("Out of calibration", R(
                  "BUU instruments not on a calibration schedule", "Measurement",
                  prevent=["6-monthly calibration of all compressor trip instruments with records"])),
              B("Set-point changed without review", R(
                  "No management of change for trip set-points", "Method",
                  prevent=["Keep a trip set-point register, verify after panel work"])),
          ])),
    ],
    "questions": [
        Q("knock", "With the compressor running, listen at the crankcase and the cylinders. What do you hear?", [
            ("Yes, rhythmic knock", _o({"oilleak": 3.2, "liquid": 1.5, "rings": 1.2, "valve": 0.9, "particle": 0.9,
                                        "gasket": 0.3, "cooling": 0.6, "sensor": 0.4})),
            ("Clatter / fluttering at valve covers", _o({"valve": 3.2, "particle": 1.6, "oilleak": 0.6, "gasket": 0.3,
                                                         "liquid": 1.0, "rings": 0.8, "cooling": 0.7, "sensor": 0.4})),
            ("Hissing", _o({"gasket": 3.5, "rings": 1.4, "oilleak": 0.3, "valve": 0.7, "particle": 0.5, "liquid": 0.5,
                            "cooling": 0.6, "sensor": 0.6})),
            ("No unusual noise", _o({"oilleak": 0.6, "valve": 0.5, "particle": 0.8, "gasket": 1.0, "liquid": 0.6,
                                     "rings": 1.0, "cooling": 1.6, "sensor": 2.0})),
            ("Heavy thud or bang, worst just after start", _o({"liquid": 3.8, "oilleak": 1.0, "valve": 1.0,
                                                               "particle": 0.8, "gasket": 0.3, "rings": 0.7,
                                                               "cooling": 0.5, "sensor": 0.4})),
        ], ["sound", "vibration", "noise", "knock"], {"tag": "vibration_mm_s", "option": 3, "above": 4.5},
          how="Stay on the walkway, out of the line of the flywheel and belt guard. Use a screwdriver or stethoscope "
              "on the crankcase, then on each valve cover. A knock once per turn from low down is a bearing; a "
              "clatter at the covers is a valve.",
          purpose="Where and how it knocks tells bearings, valves, leaks and liquid apart."),
        Q("oil", "Check the crankcase sight glass and look around the crankcase. What do you see?", [
            ("Level 60–80%, dry crankcase", _o({"oilleak": 0.2, "liquid": 0.9}, 1.1)),
            ("Level low with oil wetting / drips", _o({"oilleak": 3.8, "rings": 0.9}, 0.8), ["low_oil"]),
            ("Level low, no visible leak", _o({"oilleak": 1.8, "rings": 1.8, "valve": 1.0, "sensor": 0.8}, 0.9),
             ["low_oil"]),
            ("Level rising, or oil looks milky", _o({"liquid": 3.5, "oilleak": 0.4, "rings": 1.3}, 0.8)),
        ], ["oil level", "oil leakage", "oil"], {"tag": "oil_level_pct", "option": 0, "below": 60},
          how="Read the sight glass with the compressor stopped for a few minutes (or as the OEM says). Normal is "
              "60–80%. Look under the crankcase, at the drain plug, covers and shaft seal for wet oil. Milky oil "
              "means water.",
          purpose="Low oil starves the bearings — the compressor must not restart below 60% (OIL-01)."),
        Q("strainer", "With the compressor isolated and purged, check the suction vessel strainer. What's in it?", [
            ("Clean", _o({"particle": 0.15, "liquid": 0.8}, 1.1)),
            ("Fine black powder / media granules", _o({"particle": 4.5, "valve": 1.1, "rings": 1.2}, 0.7),
             ["particles"]),
            ("Wet sludge or standing water", _o({"liquid": 3.5, "particle": 1.2, "valve": 1.1}, 0.8)),
        ], ["particle", "powder", "strainer"],
          how="Needs a permit: compressor stopped, suction and discharge isolated, depressurised to flare, purged "
              "with nitrogen and gas-tested before opening. Wear gloves — black iron sulphide powder can glow or "
              "self-heat in air, so wet it down.",
          purpose="Powder or granules here mean the scrubber or filter upstream is letting solids through."),
        Q("gasdet", "Sweep the flanges, valve covers and packing vent with your portable gas detector. What does it read?", [
            ("0% LEL everywhere", _o({"gasket": 0.15, "rings": 0.6}, 1.1)),
            ("Above 10% LEL near a flange", _o({"gasket": 4.5, "rings": 0.8}, 0.8), ["gas_leak"]),
            ("Reading at the rod packing vent / distance piece", _o({"rings": 3.8, "gasket": 1.0}, 0.8), ["gas_leak"]),
        ], ["gas", "smell", "flange"],
          how="Wear your personal monitor. Zero the detector in fresh air, approach from upwind and hold the probe "
              "2–5 cm from each joint. On alarm (10% LEL / 10 ppm H2S) back off, keep ignition sources away and call "
              "the control room.",
          purpose="Leaking gas is a fire and H2S hazard; the location also tells a gasket from worn packing."),
        Q("valvetemp", "Use the IR gun on the valve covers. Is one hotter than the others?", [
            ("Uniform temperature", _o({"valve": 0.25, "particle": 0.8, "cooling": 0.9}, 1.1)),
            ("One valve hotter by >15°C", _o({"valve": 3.6, "particle": 1.8, "rings": 1.1}, 0.8)),
            ("All covers hotter than usual", _o({"cooling": 3.0, "rings": 1.5, "valve": 0.8}, 0.8)),
        ], ["valve", "temperature"],
          how="Aim the IR gun at each suction and discharge valve cover of the same stage, from about 30 cm. Compare "
              "like with like (suction to suction).",
          purpose="A leaking valve re-compresses hot gas, so its cover runs hotter than the rest."),
        Q("dischtemp", "Read each stage's discharge temperature on the panel. How do they compare with normal?", [
            ("All normal", _o({"cooling": 0.2, "valve": 0.8, "rings": 0.8, "sensor": 1.2})),
            ("High on one stage only", _o({"valve": 2.2, "rings": 2.2, "cooling": 0.8, "particle": 1.3}, 0.8)),
            ("High on all stages", _o({"cooling": 4.0, "rings": 1.0, "valve": 0.7, "sensor": 1.0}, 0.7)),
        ], ["temperature", "hot", "overheat"],
          how="Read the stage discharge temperatures on the local panel or HMI and compare with the normal values on "
              "the compressor data sheet (typically below ~150 °C per stage).",
          purpose="One hot stage points to a valve or ring problem in it; all hot points to cooling."),
        Q("cooler", "Check the cooling: is cooling water flowing and is the cooler fan running and clean?", [
            ("Flow good, fan running, fins clean", _o({"cooling": 0.2}, 1.1)),
            ("Weak flow, warm return or fouled fins", _o({"cooling": 4.5}, 0.8)),
        ], ["cooling", "temperature", "hot"],
          how="Look at the cooling water flow indicator or feel supply vs return lines (return should be only a few "
              "degrees warmer). On air coolers, check the fan runs and the fins are not packed with dust. Keep "
              "hands clear of the fan.",
          purpose="Without cooling, discharge temperature climbs, oil cokes and valves fail."),
        Q("interstage", "Look at the interstage and discharge pressure trends. What are they doing?", [
            ("Steady at the usual values", _o({"valve": 0.4, "rings": 0.4, "sensor": 1.4, "particle": 0.8}, 1.1)),
            ("Interstage drifted away from normal", _o({"valve": 2.6, "rings": 2.6, "particle": 1.4, "sensor": 0.7}, 0.8)),
            ("Erratic or jumping trends", _o({"sensor": 2.8, "liquid": 1.8, "valve": 1.2}, 0.8)),
        ], ["pressure", "capacity", "trip"],
          how="On the HMI, pull up suction, interstage and final discharge pressure for the last 8 hours and compare "
              "with the normal values on the data sheet (LP: ~1.2 bar(g) in, ~6 bar out; HP: ~6 bar in, ~250 bar out).",
          purpose="A leaking valve or worn rings in one stage shifts the interstage pressures."),
        Q("breather", "Look at the crankcase breather / packing vent. Is gas or oil mist blowing out?", [
            ("Nothing, or a gentle breath", _o({"rings": 0.25}, 1.1)),
            ("Strong blow-by and oil mist", _o({"rings": 4.0, "oilleak": 1.3}, 0.8)),
        ], ["blow-by", "ring", "packing"],
          how="Hold a clean rag or your hand (with glove) near — not over — the breather outlet for a few seconds. "
              "Keep your gas monitor on; blow-by is raw gas.",
          purpose="Heavy blow-by means gas is getting past the piston rings or rod packing."),
        Q("upstream", "Ask the control room: how has the H2S scrubber / filter skid dP behaved over the last day?", [
            ("Steady as usual", _o({"particle": 0.3}, 1.05)),
            ("Sudden drop, spike or filter bypass opened", _o({"particle": 4.5, "valve": 1.1}, 0.85)),
        ], ["particle", "powder", "media", "strainer"],
          how="Ask the control room to show the differential-pressure trend of the H2S scrubber and the gas filter "
              "skid, and whether the filter bypass valve was opened. You don't need to go to the skid for this.",
          purpose="A sudden dP drop or an open bypass is how scrubber media and filter debris get to the compressors."),
        Q("gauge", "Compare the local pressure gauge with the SCADA reading for the same point. Do they agree?", [
            ("Both agree", _o({"sensor": 0.15}, 1.05)),
            ("They disagree, or SCADA jumps around", _o({"sensor": 4.5, "liquid": 1.2}, 0.8)),
        ], ["reading", "alarm", "trip", "transmitter"],
          how="Read the local gauge and ask the control room to read the same tag at the same moment. More than about "
              "10% difference means one of them is wrong.",
          purpose="A faulty transmitter can cause false trips that look like a compressor fault."),
    ],
}

# ---------------------------------------------------------------------------------------------------------------------
MAINTENANCE = {
    "Blower": {
        "summary": "Side-channel / centrifugal blowers boost raw biogas from the scrubber to the LP compressors, dose "
                   "air into digesters for biological desulphurisation and support membrane roofs; flare and LDT "
                   "blowers serve the HWG area. Wet, H2S-laden gas means condensate, sulphur deposits, corrosion "
                   "and flange leaks are the main issues, plus bearings and belts on belt-driven units.",
        "pm": [
            ("Every shift", "Listen for abnormal noise; check discharge pressure, motor current, enclosure ventilation; "
                            "drain casing / knock-out pot condensate"),
            ("Weekly", "Gas-detector sweep of flanges and shaft seal; check belt condition (belt-driven units)"),
            ("Monthly", "Vibration and bearing temperature readings; clean inlet filter (air blowers); "
                        "clean condensate traps; re-grease per OEM (not sealed-for-life units)"),
            ("Quarterly", "Inspect casing and impeller for sulphur deposits and corrosion; check NRV and relief valve; "
                          "calibrate pressure switches / transmitters (6-monthly at least)"),
            ("Yearly / OEM hours", "Replace bearings and shaft seals; renew flange gaskets opened; laser-align"),
        ],
        "failure_modes": ["Flange gasket / shaft seal gas leak", "Bearing failure (sealed-for-life end of life, wrong grease)",
                          "Condensate and sulphur fouling of impeller", "Belt slip and pulley misalignment",
                          "Overheating against back-pressure or in a hot enclosure", "False trips from wet impulse lines"],
        "operating_limits": [("Vibration (ISO 10816)", "< 4.5 mm/s"), ("Bearing housing temperature", "< 80 °C"),
                             ("Gas blower differential pressure", "≈ 80–250 mbar (OEM curve; max per nameplate)"),
                             ("Gas discharge temperature", "< 60–70 °C typical; OEM max"),
                             ("Gas leak at joints", "0% LEL; alarm at 10% LEL / 10 ppm H2S")],
    },
    "Compressor": {
        "summary": "LP 1–4 are reciprocating raw-biogas compressors feeding the chiller and membranes; HP 1–3 compress "
                   "upgraded CBG to the ~250 bar cascade; plant air compressors supply instrument and service air. "
                   "Biogas service (H2S, moisture, siloxanes, scrubber fines) wears valves, rings and packing 2–3x "
                   "faster than natural gas; crankcase lubrication and clean, dry suction gas are critical.",
        "pm": [
            ("Every shift", "Log oil level (60–80%), oil pressure, suction / interstage / discharge pressures and "
                            "temperatures, cooling water; drain knock-out pot and separators; listen for knock"),
            ("Weekly", "IR valve-cover temperatures; gas-detector sweep of flanges and packing vents; check breather "
                       "blow-by; clean air-cooler fins in dusty season"),
            ("Monthly", "Suction strainer inspection / dP; test auto-drains; vibration readings; check lubricator rate"),
            ("Quarterly", "Proof-test low oil, high temperature and pressure trips; re-torque flanges and valve covers"),
            ("4,000–8,000 h", "Valve overhaul (plates, springs, seats); oil and filter change per OEM"),
            ("8,000–16,000 h", "Piston rings, rider bands, rod packing; bearing inspection; crankshaft seals"),
        ],
        "failure_modes": ["Crankcase oil leak → big-end bearing starvation", "Valve plate / spring fatigue or impact",
                          "Solid particle ingress from scrubber media / filter rupture", "Discharge flange gasket leak",
                          "Liquid carryover into cylinders", "Piston ring / rod packing wear (blow-by)",
                          "High discharge temperature from poor cooling", "False trips from faulty transmitters"],
        "operating_limits": [("Crankcase oil level", "60–80% of sight glass (OIL-01 blocks restart below 60%)"),
                             ("Oil pressure", "≈ 2–4 bar (OEM)"),
                             ("LP suction / discharge", "≈ 1.2 bar(g) / ≈ 6 bar(g)"),
                             ("HP suction / discharge", "≈ 6 bar(g) / ≤ 250 bar(g)"),
                             ("Stage discharge temperature", "< 150 °C (OEM trip typically 160–170 °C)"),
                             ("Valve cover temperature spread", "< 15 °C between like valves"),
                             ("Vibration", "< 4.5 mm/s (frame)")],
    },
}

# ---------------------------------------------------------------------------------------------------------------------
CONDITIONS = [
    {"id": "BUU-COMP", "title": "Gas compression (BUU)", "areas": ["BUU"],
     "params": [
         ("Gas blower suction pressure", "≈ 5–20 mbar(g), never negative",
          "Negative suction can pull air into the gas line — oxygen in biogas is an explosion and membrane risk.",
          "Check gas holder level and upstream valves; stop the blower if suction goes negative."),
         ("Gas blower discharge / differential pressure", "≈ 80–250 mbar (OEM curve)",
          "High dP overheats the blower; low dP means slipping belts, leaks or a worn impeller.",
          "Check discharge valve line-up, NRV and filter dP; check belts."),
         ("LP compressor suction pressure", "≈ 1.0–1.3 bar(g) (SCADA ≈ 1.2)",
          "Low suction raises compression ratio and discharge temperature and can draw in air.",
          "Check the gas blower, suction strainer dP and upstream filter."),
         ("LP compressor discharge pressure", "≈ 5.8–6.5 bar(g)",
          "Sets the feed pressure to the chiller and membranes.",
          "If high, check downstream valves; if low with normal suction, suspect valves or rings."),
         ("HP compressor suction / discharge", "≈ 6 bar(g) in / up to 250 bar(g) out",
          "Cascade filling needs ~250 bar; over-pressure lifts relief valves.",
          "Check interstage pressures stage by stage; verify the cascade priority panel."),
         ("Interstage pressures", "Within ±10% of the data-sheet value",
          "A shift tells which stage has a leaking valve or worn rings.",
          "Compare with baseline; IR the valve covers of the affected stage."),
         ("Stage discharge temperature", "< 150 °C (trip ≈ 160–170 °C)",
          "Hot gas cokes oil on valves and kills plates and rings.",
          "Check cooling water / fan, cooler fouling and valve condition."),
         ("Crankcase oil level", "60–80% of sight glass (SCADA ≈ 70%)",
          "Low oil starves big-end bearings — knock then seizure.",
          "Stop, find the leak, top up; restart blocked below 60% (OIL-01)."),
         ("Oil pressure", "≈ 2–4 bar, up within 10 s of start",
          "Shows the oil pump and bearings are getting oil.",
          "Low pressure: check level, strainer, pump and relief valve before restart."),
         ("Cooling water supply / return", "Supply ≤ 35 °C, ΔT ≈ 5–10 °C, flow switch healthy",
          "Removes compression heat in cylinder jackets and intercoolers.",
          "Clean coolers, check pump and treatment; don't run without flow."),
         ("Suction strainer dP", "< 0.1 bar (clean ≈ 0.02–0.05 bar)",
          "Rising dP means particles or sludge are arriving from upstream.",
          "Inspect strainer under permit; trace scrubber / filter carryover (CMP-01)."),
         ("Gas inlet H2S after scrubber", "< 50 ppm (target < 10 ppm)",
          "H2S corrodes valves, packing and oil; forms iron sulphide powder.",
          "Check scrubber media and O2 dosing; increase oil change frequency."),
         ("Frame vibration", "< 4.5 mm/s (SCADA ≈ 2.2)",
          "Rising vibration shows knock, looseness or valve problems.",
          "Listen for knock, check foundation bolts; stop at Critical (ROT-01)."),
         ("Gas at joints / packing vents", "0% LEL",
          "Any reading is a fire / H2S hazard.",
          "Isolate, ventilate, confirm with portable detector (GAS-01)."),
     ],
     "notes": [
         'Compression ratio per stage of a reciprocating compressor is normally 2.5–4; higher ratios mean high discharge temperature.',
         'Raw biogas is saturated and sour — drain every knock-out pot each shift and keep suction gas above its dew point.',
         'Plant air compressors: 7–8 bar(g), drain receivers daily, dew point per dryer spec.',
     ]},
]

# ---------------------------------------------------------------------------------------------------------------------
CASES = [
    K("KB-0389", ["Compressor"], ["oil level", "knock", "sound", "vibration"],
      "Low oil level with knocking sound on LP compressor",
      "Crankcase oil leak at the drain-plug gasket starving the big-end bearings",
      "Stopped and locked out, replaced drain-plug gasket, inspected big-end bearings (light scoring, shells replaced), "
      "topped up to 70%, restarted unloaded and confirmed oil pressure",
      why=["Why the knock? Big-end bearing running with too little oil",
           "Why too little oil? Crankcase level fell to 50%",
           "Why did it fall? Oil weeping from the drain-plug gasket",
           "Why the gasket? Old washer reused at the last oil change",
           "Why reused? Oil-change job card did not call for a new washer and the level was not logged on rounds"],
      category="Method",
      prevent="New drain-plug washer added to the oil-change job card; oil level logged every shift and SCADA alarm at 65%"),
    K("KB-0501", ["Blower", "Compressor"], ["gas", "smell", "flange"], "Gas smell near blower casing",
      "Failed flange gasket on the discharge line",
      "Isolated the blower, confirmed 25% LEL at the discharge flange with a portable detector, purged, replaced the "
      "gasket with the specified grade, leak tested with soap solution",
      why=["Why the gas smell? Biogas escaping at the discharge flange",
           "Why leaking? Gasket hardened and cracked; bolts below torque",
           "Why hardened? Non-specified rubber gasket fitted at the last job",
           "Why non-specified? No line-class gasket list in stores; no re-torque after start-up"],
      category="Material",
      prevent="Line-class gasket list created and stocked; 24 h re-torque added to flange job cards"),
    K("KB-0502", ["Compressor"], ["valve", "clatter", "temperature"], "Valve-cover clatter and hot suction valve on HP 2",
      "Fatigue-cracked suction valve plate on stage 2",
      "Isolated and purged, replaced the valve plate and springs as a set, lapped the seat, torqued covers, leak tested",
      why=["Why the clatter? Broken suction valve plate fluttering",
           "Why broken? Fatigue crack from the port edge after ~11,000 h",
           "Why so long? Valves are overhauled only on failure"],
      category="Method", prevent="Valve overhaul every 6,000 h; weekly IR of valve covers with a 15 °C alarm rule"),
    K("KB-0503", ["Compressor"], ["particle", "powder", "strainer", "vibration"],
      "Black powder in LP 3 suction strainer with rising vibration",
      "Iron-oxide scrubber media carried over after the outlet mesh seal failed",
      "CMP-01 tripped LP load line; cleaned suction vessel, replaced two suction valves, re-seated scrubber media and "
      "renewed the perimeter seal before releasing the interlock",
      why=["Why the vibration? Damaged suction valves from particles",
           "Why particles? Scrubber media granules in the suction",
           "Why carryover? Outlet mesh perimeter seal had a gap",
           "Why missed? Internals not inspected at the last media change"],
      category="Material", prevent="Mesh and seal inspection added to every media change (SOP-SCR-02)"),
    K("KB-0504", ["Compressor"], ["water", "condensate", "knock"], "Heavy knock on LP 1 at start-up after a long stop",
      "Condensate in the cylinder — suction knock-out pot auto-drain stuck",
      "Stopped, drained pot and cylinders, changed milky oil, inspected valves (one cracked plate replaced), cleaned the "
      "auto-drain",
      why=["Why the knock? Liquid slug in the cylinder", "Why liquid? Knock-out pot full",
           "Why full? Auto-drain valve stuck with sludge", "Why unnoticed? No level alarm and drain not on checksheet"],
      category="Method", prevent="Knock-out pot high-level alarm; manual drain on every shift checksheet; drain step in start-up SOP"),
    K("KB-0505", ["Compressor"], ["temperature", "hot", "cooling", "trip"],
      "HP 1 trips on high stage-3 discharge temperature in the afternoons",
      "Air-cooler fins packed with dust and fibres",
      "Cleaned cooler fins with low-pressure air and water, replaced slack fan belt, trended temperature",
      why=["Why the trip? Stage 3 discharge above 165 °C", "Why hot? Intercooler not removing heat",
           "Why? Fins blocked by dust from the feed hall", "Why? No cooler cleaning interval for the dry season"],
      category="Environment", prevent="Monthly fin cleaning (fortnightly in dry season); dust screen fitted"),
    K("KB-0506", ["Compressor"], ["blow-by", "ring", "packing", "gas"], "Gas at HP 3 packing vent and falling capacity",
      "Worn rod packing and piston rings from silica deposits",
      "Replaced rod packing, piston rings and rider bands; polished the rod; set lubricator rate",
      why=["Why gas at the vent? Rod packing worn", "Why worn early? Abrasive silica deposits",
           "Why silica? Siloxanes in the gas not monitored"],
      category="Material", prevent="Quarterly siloxane test; ring/packing interval set by running hours"),
    K("KB-0507", ["Blower"], ["condensate", "vibration", "water"], "Gas Blower 2 vibration rising, water at the casing drain",
      "Condensate and sulphur crust in the side channel unbalancing the impeller",
      "Drained and cleaned the casing, cleaned the impeller, cleared the upstream condensate trap",
      why=["Why the vibration? Impeller unbalanced by deposits", "Why deposits? Condensate standing in the casing",
           "Why? Upstream condensate trap blocked", "Why? Trap had no cleaning interval"],
      category="Method", prevent="Monthly trap cleaning; daily test-cock check; casing drain on shift round"),
    K("KB-0508", ["Blower"], ["belt", "squeal", "temperature"], "Flare Blower belt squeal and low flow",
      "Glazed belts slipping after the motor was changed and aligned by eye",
      "Replaced belt set, laser-aligned pulleys, tensioned and re-checked after 4 h",
      why=["Why the squeal? Belts slipping", "Why slipping? Pulleys out of line and tension low",
           "Why? Motor change aligned by eye, no re-tension after run-in"],
      category="Method", prevent="Belt alignment laser issued; re-tension check at 4 h and 24 h on job card"),
]
