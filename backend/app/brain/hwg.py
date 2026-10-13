"""Hot water generators: HWG 1 and HWG 2 — biogas-fired hot water generators that heat the digesters (mesophilic,
≈ 37–40 °C). Each has a gas burner train (manual isolation, filter, regulator, low/high gas pressure switches,
double solenoid valves, burner with ignition electrode and flame scanner / ionisation probe), a belt-driven
induced-draught (ID) fan, a fire-tube or water-tube heat exchanger, and circulation pumps on the digester heating loop.

Sources (types): burner-management / gas-train OEM manuals (EN 676 forced-draught burners: lockout codes, gas and air
pressure switches, flame supervision), boiler O&M guides (flue-gas O2 / CO targets, scaling and water treatment),
studies on silica deposition from siloxanes in biogas-fired appliances (silica coats ionisation probes and heat
exchangers → falling ion current and flame-failure lockouts; annual or more frequent cleaning), V-belt drive OEM
guidance (tension by deflection, matched sets, laser alignment, run-in re-tension), plant incident history
(incident_log_gas_movers_hwg.csv), SOP-HWG-01 and SOP-ROT-01 (LOTO) in data/docs.
"""
from .dsl import B, C, K, Q, R, W

TREES = {}

_H = ["belt", "fanbrg", "lowgas", "deposits", "scanner", "airfuel", "circ", "air"]


def _o(strong: dict, rest: float = 1.0) -> dict:
    """Likelihoods: the listed causes, every other HWG cause at `rest`."""
    return {c: strong.get(c, rest) for c in _H}


TREES["HWG"] = {
    "causes": [
        C("belt", "ID fan belt slippage from low tension and pulley misalignment", "Method",
          ["belt", "squeal", "slip"], [
            "Stop the ID fan and apply LOTO — never adjust a running belt (BELT-01)",
            "Replace the belts as a matched set",
            "Align the pulleys with a straight edge or belt-alignment laser",
            "Tension to the OEM deflection and re-check after 4 running hours and again after 24 h"],
          why=W("Why did the belts slip?", [
              B("Tension too low", W("Why was the tension low?", [
                  B("Not re-tensioned after run-in", R(
                      "Belt job card has no re-tension step after the first hours of running", "Method",
                      prevent=["Add re-tension checks at 4 h and 24 h to the belt job card",
                               "Use a belt tension gauge, not thumb feel"])),
                  B("Motor base slid back", R(
                      "Motor base slide bolts not locked; no jacking screw", "Machine",
                      prevent=["Fit jacking screws and lock nuts on the motor base"])),
              ])),
              B("Pulleys out of line", W("Why were the pulleys misaligned?", [
                  B("Aligned by eye after motor change", R(
                      "No alignment tool or recorded alignment in the procedure", "Method",
                      prevent=["Issue a belt-alignment laser and record the result on the job card"])),
                  B("Fan bearing housing moved", R(
                      "Fan pedestal bolts not checked in PM", "Method",
                      prevent=["Add pedestal bolt torque check to quarterly PM"])),
              ])),
              B("Belts mixed or wrong section", R(
                  "Belts replaced singly / non-matched sets from stores", "Man",
                  prevent=["Stock matched sets only; train crew to replace the full set"])),
          ], how="Glazed shiny sides = slipping on low tension; one-side wear and frayed edges = misalignment."),
          case="KB-0270"),
        C("fanbrg", "ID fan bearing wear", "Machine", ["bearing", "growl", "vibration"], [
            "Stop the ID fan and apply LOTO",
            "Check bearing play and grease condition; replace the bearings if rough",
            "Clean soot / deposits from the fan impeller and check balance",
            "Restart and trend vibration and bearing temperature"],
          why=W("Why did the fan bearing wear out?", [
              B("Lubrication wrong or missed", W("What went wrong with the greasing?", [
                  B("Greasing skipped — point hard to reach", R(
                      "Bearing grease points not on a lube route; no remote grease lines", "Method",
                      prevent=["Put fan bearings on the weekly lube route", "Fit extended grease lines"])),
                  B("Wrong grease for hot fan service", R(
                      "No high-temperature grease specified for the flue-gas fan", "Material",
                      prevent=["Specify and label high-temperature grease at each point"])),
              ])),
              B("Impeller unbalanced by soot / deposits", R(
                  "ID fan impeller not cleaned at boiler service", "Method",
                  prevent=["Clean and inspect the impeller at every HWG service"])),
              B("Belts over-tensioned", R(
                  "Belt tension set without a gauge, overloading the bearing", "Man",
                  prevent=["Train on belt tension by deflection force; use a tension gauge"])),
          ])),
        C("lowgas", "Low or unstable biogas pressure at the burner train", "Material",
          ["gas pressure", "low gas", "lockout", "pulsing"], [
            "Read the gas pressure at the burner train inlet and after the regulator while firing",
            "Clean the gas-train filter; drain the condensate trap on the gas line",
            "Check the gas holder level and the gas blower to the HWG",
            "Reset the burner only after the pressure is stable within the burner's range"],
          why=W("Why is the gas pressure low at the burner?", [
              B("Gas filter / condensate pot blocked", W("Why was it blocked?", [
                  B("Condensate trap not drained", R(
                      "HWG gas-line condensate trap not on the shift round", "Man",
                      prevent=["Add trap drain to the HWG shift round", "Fit a sight glass / auto-drain"])),
                  B("Filter element never changed", R(
                      "Gas-train filter has no dP gauge or change interval", "Method",
                      prevent=["Fit a dP gauge and change the element at the OEM limit"])),
              ])),
              B("Gas holder low / BUU drawing all the gas", R(
                  "No gas priority between upgrading and HWG during low production", "Method",
                  prevent=["Agree a gas priority / minimum holder level for HWG firing",
                           "Alarm on gas holder low level"])),
              B("Regulator set wrong or failing", R(
                  "Regulator not checked at annual burner service", "Measurement",
                  prevent=["Check regulator outlet pressure at every burner service and record it"])),
          ])),
        C("deposits", "Silica / sulphur deposits on burner head, electrode and heat exchanger", "Material",
          ["deposit", "silica", "white powder", "soot", "flame failure"], [
            "Isolate gas and apply LOTO; let the HWG cool",
            "Remove and clean the burner head, ignition electrode and ionisation probe (white silica / yellow sulphur)",
            "Brush and wash the fire-side heat exchanger surfaces",
            "Re-gap the electrode to OEM spec, reassemble and check the flame signal"],
          why=W("Why are deposits building up?", [
              B("Siloxanes in the biogas form silica", W("Why is silica not being controlled?", [
                  B("Siloxane content never measured", R(
                      "No gas quality monitoring for siloxanes at the HWG supply", "Measurement",
                      prevent=["Sample siloxanes quarterly", "Set burner cleaning interval from the result"])),
                  B("Cleaning only after a lockout", R(
                      "Burner cleaning interval not set for biogas service", "Method",
                      prevent=["Clean burner, probe and heat exchanger every 3 months (not yearly)"])),
              ])),
              B("H2S in the fuel gas (sulphur deposits, corrosion)", R(
                  "HWG fed with raw gas without adequate desulphurisation", "Material",
                  prevent=["Feed HWG after the H2S scrubber or check biological desulphurisation O2 dosing",
                           "Keep flue-gas temperature above acid dew point"])),
          ])),
        C("scanner", "Flame scanner / ionisation probe fault (nuisance flame failure)", "Measurement",
          ["flame failure", "scanner", "lockout", "probe"], [
            "Isolate gas and apply LOTO",
            "Clean the flame scanner lens or ionisation probe; check its position and earth connection",
            "Measure the flame signal (µA) against the burner manual minimum",
            "Replace the scanner / probe or its cable if the signal stays low"],
          why=W("Why does the flame supervision drop out?", [
              B("Lens or probe dirty / probe moved", R(
                  "Scanner / probe cleaning and flame-signal reading not in PM", "Method",
                  prevent=["Clean scanner / probe monthly and log the flame signal"])),
              B("Cable or earth connection poor", R(
                  "Burner wiring exposed to heat and vibration without inspection", "Machine",
                  prevent=["Inspect burner wiring and earth at each service; use heat-resistant cable"])),
              B("Scanner overheated", R(
                  "No cooling air / heat shield on the scanner in a hot boiler house", "Environment",
                  prevent=["Fit scanner cooling air or heat shield; improve boiler-house ventilation"])),
          ])),
        C("airfuel", "Air–fuel ratio out of tune (unstable, lifting or sooty flame)", "Method",
          ["flame", "o2", "co", "combustion", "soot"], [
            "Measure flue gas O2 and CO with a portable analyser",
            "Re-tune the air damper / gas-air ratio to OEM targets (O2 ≈ 3–6%, CO < 100 ppm)",
            "Lock the damper linkage and record the settings"],
          why=W("Why is the combustion out of tune?", [
              B("Burner not re-tuned after a change", W("What changed?", [
                  B("Gas methane content changed", R(
                      "Burner tuned for one gas quality; CH4 swings not considered", "Material",
                      prevent=["Re-tune when CH4 changes by more than ~5%", "Check CH4 at the HWG weekly"])),
                  B("Parts replaced without combustion test", R(
                      "No combustion analysis after burner maintenance", "Method",
                      prevent=["Make flue gas analysis mandatory after any burner work"])),
              ])),
              B("Damper linkage slipped", R(
                  "Damper linkage not locked or marked", "Machine",
                  prevent=["Mark and lock the linkage; check it monthly"])),
              B("Settings changed by untrained person", R(
                  "Burner adjustment not restricted to trained staff", "Man",
                  prevent=["Restrict burner tuning to trained technicians; log every change"])),
          ])),
        C("circ", "Low water circulation or scaled heat exchanger (high-limit trips)", "Machine",
          ["circulation", "temperature", "overheat", "scale", "flow"], [
            "Check the circulation pump is running and the loop valves are open",
            "Vent air from the heating loop high points",
            "Check flow vs return ΔT; clean strainers on the loop",
            "Descale the water side if ΔT across the HWG is low with high flue temperature"],
          why=W("Why is the water side not taking the heat?", [
              B("Circulation pump weak or stopped", R(
                  "No flow switch interlock between circulation and burner", "Machine",
                  prevent=["Interlock burner firing with loop flow", "Add standby pump auto-changeover"])),
              B("Scale on the water side", W("Why did scale build up?", [
                  B("Untreated make-up water", R(
                      "Heating loop make-up water not softened / dosed", "Material",
                      prevent=["Soften make-up water; check hardness monthly", "Descale yearly"])),
                  B("Frequent top-ups from leaks", R(
                      "Loop leaks not fixed, so fresh hard water keeps coming in", "Method",
                      prevent=["Meter make-up water and fix leaks when it rises"])),
              ])),
              B("Air lock in the loop", R(
                  "No venting step after loop maintenance", "Method",
                  prevent=["Add venting high points to the loop restart checklist"])),
          ])),
        C("air", "Combustion air or flue draught problem (blocked intake, wind, hot room)", "Environment",
          ["air", "draught", "flue", "louvre"], [
            "Open and clear the boiler-house air intake louvres",
            "Check the flue / stack for blockage and the ID fan damper position",
            "Check the air pressure switch; restart and confirm a stable flame"],
          why=W("Why is the burner short of air or draught?", [
              B("Louvres blocked or closed", R(
                  "Boiler-house louvres closed for rain / dust and not reopened", "Man",
                  prevent=["Fix louvres open with weather hoods; add to daily round"])),
              B("Wind or rain affecting the stack", R(
                  "Stack has no rain cap / draught stabiliser", "Environment",
                  prevent=["Fit a rain cap and draught stabiliser on the stack"])),
              B("Flue passages restricted by soot", R(
                  "Flue and stack cleaning not scheduled", "Method",
                  prevent=["Clean flue passages and stack every 6 months"])),
          ])),
    ],
    "questions": [
        Q("squeal", "Stand near the HWG for a moment. What do you hear, and when is it loudest?", [
            ("At fan start-up — squeal", _o({"belt": 4.0, "fanbrg": 0.6, "lowgas": 0.5, "deposits": 0.5, "scanner": 0.5,
                                            "airfuel": 0.5, "circ": 0.5, "air": 0.6}), ["belt_wear"]),
            ("Constant growl from the fan bearing", _o({"fanbrg": 3.8, "belt": 0.8, "lowgas": 0.5, "deposits": 0.6,
                                                        "scanner": 0.5, "airfuel": 0.5, "circ": 0.5, "air": 0.6},),
             ["rotating_abnormal"]),
            ("Rumble or pulsing from the burner", _o({"airfuel": 2.8, "lowgas": 2.0, "air": 2.5, "deposits": 1.2,
                                                      "belt": 0.4, "fanbrg": 0.5, "scanner": 0.7, "circ": 0.6})),
            ("No unusual sound", _o({"belt": 0.3, "fanbrg": 0.3, "scanner": 1.6, "circ": 1.6, "deposits": 1.3,
                                     "lowgas": 1.0, "airfuel": 0.8, "air": 0.8})),
        ], ["sound", "noise", "belt", "squeal", "vibration"], {"tag": "vibration_mm_s", "option": 3, "above": 4.5},
          how="Listen from the walkway, first at the ID fan and its belt guard, then at the burner front. Don't open "
              "the belt guard while the fan runs.",
          purpose="Belts squeal, bearings growl and a badly tuned or starved burner rumbles."),
        Q("drive", "With the ID fan stopped under LOTO, take a look at the belts and pulleys. What do you see?", [
            ("Belts good, pulleys in line", _o({"belt": 0.15}, 1.05)),
            ("Glazed, cracked or slack belts / pulleys offset", _o({"belt": 4.5, "fanbrg": 1.3}, 0.8), ["belt_wear"]),
        ], ["belt", "squeal"],
          how="Only with the ID fan stopped, isolated and locked out (SOP-ROT-01, BELT-01): remove the guard, press each "
              "belt mid-span (about 15 mm deflection is typical), look for shiny glazed sides and cracks, and lay a "
              "straight edge across both pulley faces.",
          purpose="Slipping belts starve the burner of draught and wear the fan bearings."),
        Q("brgtemp", "Point an IR thermometer at the ID fan bearing housings. How hot are they?", [
            ("Below 70°C", _o({"fanbrg": 0.25, "belt": 0.9}, 1.05)),
            ("Above 70°C", _o({"fanbrg": 3.8, "belt": 1.4}, 0.85)),
        ], ["bearing", "temperature", "vibration"], {"tag": "bearing_temp_c", "option": 0, "above": 75},
          how="Aim the IR gun at bare metal on each bearing housing from about 30 cm, away from the belts and the hot "
              "flue duct, which will mislead the reading.",
          purpose="A hot fan bearing is failing and will seize the fan."),
        Q("lockout", "What does the burner control panel show as the last lockout or fault?", [
            ("Flame failure", _o({"scanner": 2.6, "deposits": 2.4, "lowgas": 1.5, "airfuel": 1.4, "air": 1.0,
                                  "belt": 0.5, "fanbrg": 0.5, "circ": 0.3})),
            ("Low gas pressure", _o({"lowgas": 4.5, "deposits": 0.8}, 0.5)),
            ("Air pressure switch / fan fault", _o({"belt": 2.4, "fanbrg": 1.8, "air": 2.4, "airfuel": 0.8}, 0.4)),
            ("High water temperature limit", _o({"circ": 5.0}, 0.4)),
            ("No lockouts", _o({"belt": 1.3, "fanbrg": 1.5, "airfuel": 1.3, "circ": 0.5, "lowgas": 0.6, "scanner": 0.4,
                                "deposits": 0.7, "air": 0.9})),
        ], ["lockout", "trip", "flame failure", "fault"],
          how="Read the fault code on the burner controller display or the HMI alarm list and look it up in the "
              "burner manual. Note it down before anyone resets it.",
          purpose="The lockout code tells which safety chain stopped the burner — gas, air, flame or water."),
        Q("gasp", "Read the gas pressure gauge at the burner train inlet while the burner fires. How is it?", [
            ("Steady at the normal value", _o({"lowgas": 0.15}, 1.05)),
            ("Low, or drops when the burner lights", _o({"lowgas": 4.5, "deposits": 1.0}, 0.8)),
        ], ["gas pressure", "low gas", "pressure"],
          how="Use the gauge on the burner train inlet (before the regulator) and, if fitted, after the regulator. Normal "
              "is typically 20–50 mbar at the inlet — use the value on the burner data plate. Don't open test points "
              "on a live gas line without a permit and a gas detector.",
          purpose="Too little gas pressure means lean, unstable flames and low-gas lockouts."),
        Q("o2", "If you have the flue gas analyser, what do O2 and CO read at the flue test point?", [
            ("O2 3–6%, CO low", _o({"airfuel": 0.2, "air": 0.4, "lowgas": 0.8}, 1.1)),
            ("O2 high (above 8%)", _o({"airfuel": 3.0, "lowgas": 2.0, "air": 0.6}, 0.8)),
            ("O2 low with high CO / soot", _o({"airfuel": 2.8, "air": 3.0, "deposits": 1.3}, 0.7)),
        ], ["o2", "co", "combustion", "flame"],
          how="Insert the analyser probe into the flue test point after the HWG while firing at normal load and wait "
              "for a steady reading. Keep clear of hot flue surfaces and replace the test-point plug afterwards.",
          purpose="Flue O2 and CO show whether the burner is getting the right air for the gas."),
        Q("intake", "Check the boiler-house air intake louvres, the room temperature and the stack. What do you find?", [
            ("Louvres open, room normal, stack clear", _o({"air": 0.15}, 1.05)),
            ("Louvres blocked, very hot room or stack issue", _o({"air": 4.5, "scanner": 1.2, "airfuel": 1.1}, 0.8)),
        ], ["air", "louvre", "flue", "draught"],
          how="Walk round the boiler house: look at intake louvres (open, not covered by sheets or dust), feel the "
              "room temperature and look at the stack top for a missing rain cap or birds' nests.",
          purpose="A burner short of combustion air or draught burns badly and locks out."),
        Q("probe", "With gas isolated under LOTO and the HWG cooled, pull the ionisation probe / scanner and electrode. "
                   "What do they look like?", [
            ("Clean and correctly positioned", _o({"scanner": 0.3, "deposits": 0.25}, 1.1)),
            ("White powder or yellow crust on them", _o({"deposits": 4.5, "scanner": 0.9}, 0.8)),
            ("Lens dirty or cracked, probe loose or bent", _o({"scanner": 4.5, "deposits": 0.6}, 0.8)),
        ], ["flame failure", "scanner", "deposit", "probe"],
          how="Close and lock the manual gas valve, isolate the burner power, wait for the HWG to cool and check for "
              "gas with your detector. Unclip the probe / scanner and the ignition electrode as per the burner manual.",
          purpose="White silica from siloxanes kills the flame signal; a dirty or loose scanner causes nuisance trips."),
        Q("signal", "On the burner controller, how does the flame signal behave?", [
            ("Steady, well above the minimum", _o({"scanner": 0.25, "deposits": 0.35, "lowgas": 0.8, "airfuel": 0.8}, 1.1)),
            ("Falling slowly over days or weeks", _o({"deposits": 4.0, "scanner": 1.0, "airfuel": 1.1}, 0.8)),
            ("Jumps or drops out suddenly", _o({"scanner": 4.0, "lowgas": 1.6, "air": 1.3, "deposits": 0.6}, 0.8)),
        ], ["flame failure", "scanner", "probe", "lockout"],
          how="Most burner controllers show the flame signal (µA or %) on the display or via a test socket; your "
              "electrician can read it with a multimeter in µA. Compare with the minimum in the burner manual and "
              "with the last logged value.",
          purpose="A slow fall points to deposits building on the probe; sudden drop-outs point to the scanner or "
                  "its wiring."),
        Q("flue", "How has the flue gas temperature trended over the last few weeks?", [
            ("Steady at the usual value", _o({"deposits": 0.3, "circ": 0.7}, 1.05)),
            ("Creeping up week on week", _o({"deposits": 3.5, "circ": 1.8, "airfuel": 1.2}, 0.8)),
        ], ["flue", "deposit", "temperature", "soot"],
          how="Ask the control room for the flue gas temperature trend, or read the flue thermometer at the HWG "
              "outlet at the same firing rate as your last log entry.",
          purpose="A rising flue temperature means the heat exchanger is fouling and not taking the heat."),
        Q("temps", "Look at the HWG flow and return temperatures and the circulation pump. How are they?", [
            ("ΔT normal (about 8–12°C), pump running", _o({"circ": 0.15}, 1.05)),
            ("Flow temp climbing, big ΔT or pump weak", _o({"circ": 4.5, "deposits": 1.1}, 0.8)),
        ], ["circulation", "temperature", "overheat", "flow"],
          how="Read flow and return temperature on the HMI or local thermometers and check the circulation pump is "
              "running with normal pressure. Gurgling in the pipes means air in the loop.",
          purpose="If water doesn't carry the heat away, the HWG trips on its high limit and scales up."),
    ],
}

MAINTENANCE = {
    "HWG": {
        "summary": "HWG 1 and HWG 2 burn biogas to make hot water (≈ 60–80 °C) for digester heating. Burner and "
                   "flame supervision, gas pressure, ID fan belts and bearings, combustion tuning and the water "
                   "side (circulation, scaling) are the main maintenance items. Siloxanes and H2S in biogas deposit "
                   "silica and sulphur on probes and heat exchangers, so cleaning intervals are shorter than on "
                   "natural gas.",
        "pm": [
            ("Every shift", "Check flow / return temperatures, gas pressure at burner train, lockout history, ID fan "
                            "noise; drain gas-line condensate trap"),
            ("Weekly", "Inspect ID fan belts (stopped, LOTO); grease ID fan bearings per OEM; check louvres"),
            ("Monthly", "Clean flame scanner / ionisation probe and log flame signal; flue gas O2 / CO check; "
                        "gas-train filter dP; vibration and bearing temperature of ID fan"),
            ("Quarterly", "Clean burner head, electrode and fire-side surfaces (biogas silica); test gas pressure "
                          "switches, air pressure switch and high-limit thermostat; laser-check belt alignment"),
            ("Yearly", "Full burner service and combustion tuning; water-side descaling; flue and stack cleaning; "
                       "valve-proving / solenoid leak test"),
        ],
        "failure_modes": ["ID fan belt slip / wear", "ID fan bearing failure", "Low or unstable gas pressure",
                          "Silica / sulphur deposits on probe, burner and heat exchanger",
                          "Flame scanner / ionisation nuisance trips", "Air–fuel ratio drift",
                          "Low circulation or scale → high-limit trips", "Combustion air / draught problems"],
        "operating_limits": [("Flow / return temperature", "≈ 70–80 °C / 60–70 °C (ΔT ≈ 8–12 °C)"),
                             ("Gas pressure at burner train inlet", "≈ 20–50 mbar (burner data plate)"),
                             ("Flue gas O2", "≈ 3–6%"), ("Flue gas CO", "< 100 ppm"),
                             ("Flue gas temperature", "≈ 160–220 °C (rising = fouling)"),
                             ("ID fan vibration", "< 4.5 mm/s"), ("ID fan bearing temperature", "< 80 °C"),
                             ("Belt deflection", "≈ 15 mm per metre of span (OEM)")],
    },
}

CONDITIONS = [
    {"id": "HWG", "title": "Hot Water Generator area (HWG)", "areas": ["HWG"],
     "params": [
         ("HWG flow temperature", "≈ 70–80 °C",
          "Delivers heat to the digester heat exchangers; too hot risks high-limit trips and scaling.",
          "Check set-point and circulation; reduce firing if flow temperature climbs."),
         ("HWG return temperature", "≈ 60–70 °C (ΔT 8–12 °C)",
          "Low return means high heat demand; very high ΔT means low circulation.",
          "Check loop pump, valves and air locks."),
         ("Digester temperature", "≈ 37–40 °C, change < 1 °C/day",
          "Methanogens are sensitive to temperature swings; gas production drops fast.",
          "Keep HWG available; switch to standby HWG before maintenance."),
         ("Gas pressure at burner train inlet", "≈ 20–50 mbar (data plate)",
          "Low pressure gives lean, unstable flames and lockouts.",
          "Drain condensate trap, clean filter, check holder level and regulator."),
         ("Gas pressure after regulator", "Steady at burner setting, no dip on ignition",
          "Dips at ignition cause flame failure.",
          "Check regulator and filter dP."),
         ("Flue gas O2", "≈ 3–6%",
          "High O2 wastes fuel; low O2 makes CO and soot.",
          "Re-tune air damper; check intake louvres."),
         ("Flue gas CO", "< 100 ppm",
          "CO means incomplete combustion — fouling and a toxic hazard in the boiler house.",
          "Re-tune; check air supply and burner head deposits."),
         ("Flue gas temperature", "≈ 160–220 °C",
          "A steady rise means fouling or scaling of the heat exchanger.",
          "Plan fire-side cleaning / water-side descaling."),
         ("Flame signal (ionisation / scanner)", "Above burner manual minimum, stable",
          "A falling signal predicts flame-failure lockouts (silica on the probe).",
          "Clean probe / scanner; check position and earth."),
         ("ID fan vibration", "< 4.5 mm/s (SCADA ≈ 2.2)",
          "Rising vibration means belt, bearing or impeller problems.",
          "Inspect belts and bearings under LOTO; stop at Critical."),
         ("ID fan bearing temperature", "< 80 °C (SCADA ≈ 62)",
          "Hot bearings fail and seize the fan.",
          "Grease per OEM; check belt tension; replace bearings if rough."),
         ("Loop pressure / circulation", "Pump running, loop pressure ≈ 1.5–3 bar, flow switch healthy",
          "No flow means the HWG overheats.",
          "Vent air, check pump and strainer; check make-up water."),
         ("Make-up water hardness", "Softened (< 1–2 °dH) per water-treatment spec",
          "Hard water scales the heat exchanger.",
          "Check softener; dose inhibitor."),
         ("Gas at burner train / boiler house", "0% LEL",
          "Gas build-up in the boiler house is an explosion risk.",
          "Isolate gas, ventilate, confirm with detector (GAS-01)."),
     ],
     "notes": [
         'Always pre-purge before ignition and never repeatedly reset a lockout — after two lockouts find the cause.',
         'Biogas burners need more frequent probe and burner cleaning than natural-gas burners because of silica (siloxanes) and sulphur.',
         'Switch to the standby HWG before work so digester temperature stays steady.',
     ]},
]

CASES = [
    K("KB-0270", ["HWG"], ["belt", "squeal", "sound"], "Worn ID fan belts and squealing sound on HWG",
      "Belt slippage from low tension and pulley misalignment",
      "Stopped the ID fan under LOTO, replaced the belt set as a matched set, laser-aligned the pulleys, tensioned to "
      "OEM deflection and re-checked after 4 h",
      why=["Why the squeal? Belts slipping on the pulleys at start-up",
           "Why slipping? Tension low and pulleys 3 mm out of line",
           "Why? After the last motor change the pulleys were aligned by eye and never re-tensioned after run-in",
           "Why? Belt job card has no alignment tool or re-tension step"],
      category="Method", prevent="Belt-alignment laser issued; re-tension at 4 h and 24 h added to the job card"),
    K("KB-0510", ["HWG"], ["flame failure", "lockout", "deposit", "silica"],
      "HWG 2 repeated flame-failure lockouts every few hours",
      "White silica deposits on the ionisation probe from siloxanes in biogas",
      "Cleaned probe, electrode and burner head; flame signal back from 2 µA to 9 µA",
      why=["Why the lockouts? Flame signal below minimum", "Why low signal? Probe coated in white silica",
           "Why silica? Siloxanes in biogas; burner cleaned only yearly"],
      category="Material", prevent="Quarterly probe / burner cleaning and monthly flame-signal log; siloxane sampling"),
    K("KB-0511", ["HWG"], ["low gas", "gas pressure", "lockout"], "HWG 1 low gas pressure lockouts on cold mornings",
      "Gas-line condensate trap full, restricting flow to the burner train",
      "Drained the trap, cleaned the gas filter, fitted an auto-drain",
      why=["Why low gas? Pressure fell from 35 to 12 mbar on ignition", "Why? Condensate trap full",
           "Why? Trap not on the shift round"],
      category="Man", prevent="Trap drain added to HWG shift checksheet; auto-drain fitted"),
    K("KB-0512", ["HWG"], ["temperature", "circulation", "overheat"], "HWG 2 tripping on high water temperature",
      "Circulation pump strainer choked and air lock in the loop",
      "Cleaned strainer, vented loop high points, confirmed ΔT 10 °C",
      why=["Why the high-limit trip? Low water flow", "Why? Strainer choked and air in the loop",
           "Why? No venting step after loop maintenance"],
      category="Method", prevent="Venting and strainer check added to loop restart checklist; flow switch interlock"),
    K("KB-0513", ["HWG"], ["bearing", "growl", "vibration"], "ID fan growl and hot bearing on HWG 1",
      "ID fan bearing failure from missed greasing",
      "Replaced both bearings, cleaned impeller, fitted extended grease lines",
      why=["Why the growl? Bearing raceway damage", "Why? Bearing ran dry",
           "Why? Grease point behind the duct was hard to reach and skipped"],
      category="Method", prevent="Extended grease lines; fan bearings added to weekly lube route"),
    K("KB-0514", ["HWG"], ["flame", "co", "soot", "combustion"], "Sooty, pulsing flame on HWG 1 after burner service",
      "Air damper linkage slipped; no combustion test after service",
      "Re-tuned to O2 4.5%, CO 40 ppm; marked and locked the linkage",
      why=["Why the soot? Too little combustion air", "Why? Damper linkage slipped",
           "Why unnoticed? No flue gas analysis after burner work"],
      category="Method", prevent="Flue gas analysis mandatory after burner work; linkage marked and locked"),
    K("KB-0515", ["HWG"], ["air", "louvre", "lockout"], "HWG air-pressure-switch lockouts during monsoon",
      "Boiler-house louvres closed against rain and left closed",
      "Opened louvres, fitted weather hoods, restored combustion air",
      why=["Why the lockouts? Air pressure switch not making", "Why? Combustion air starved",
           "Why? Louvres closed for rain and not reopened"],
      category="Environment", prevent="Weather hoods fitted so louvres stay open; louvres on the daily round"),
]
