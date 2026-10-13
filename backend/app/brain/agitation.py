"""Agitation: digester agitators (D1–D4 side-entry "Dx Agitator 1–4" with gearbox, and top-entry "Dx Top Agitator
1–2"), feed-hall agitators (H1/H2 side and top agitators, SBT top agitators) and CDT / PST agitators — plus the
normal operating envelope of the mesophilic digesters (DIG profile, areas D1–D4).

Sources: agitator and industrial gearbox OEM manuals (ISO VG 320 gear oil, bearing temperature alert/trip bands,
laser alignment tolerances, braided gland packing practice), biogas-plant mixer predictive-maintenance guidance
(bearing failure visible in vibration trends weeks ahead, shaft seal checks, scum / floating-layer risk during
downtime), German biogas accident / damage investigation reports (broken long-shaft side mixers, floating layers
persisting after repair), Indian CBG industry experience with fibrous substrates (paddy straw, napier grass, press
mud: crusting, sediment build-up, uneven mixing), anaerobic-digestion process literature and biogas association
guidance on FOS/TAC, VFA, pH, OLR, HRT and foaming, plant incident history (incident_log_2026.csv,
incident_log_agitation_feeding.csv), OEM_Agitator_Gearbox_Maintenance.md, SOP-DIG-01 and SOP-ROT-01 (LOTO).
"""
from .dsl import B, C, K, Q, R, W

TREES = {}

_ALL = ["brg", "mis", "gland", "rag", "sed", "lube", "sensor", "elec"]


def _rest(v, **kw):
    """Likelihood dict: every cause gets v, except the ones given explicitly."""
    d = {c: v for c in _ALL}
    d.update(kw)
    return d


TREES["Agitator"] = {
    "causes": [
        C("brg", "Gearbox output bearing wear", "Machine", ["vibration", "sound", "bearing", "temperature", "hot"], [
            "Stop the agitator and apply LOTO (SOP-ROT-01) — lock the MCC isolator and try-start to prove dead",
            "Drain and inspect the gearbox oil for metal fines; keep a sample for analysis",
            "Replace the output shaft bearing set (and the output oil seal while it is open)",
            "Flush and refill the gearbox with the OEM grade (ISO VG 320 synthetic) to the mid sight-glass mark",
            "Check the coupling and laser-align motor to gearbox (≤ 0.05 mm offset)",
            "Restart and trend vibration and bearing temperature hourly for one shift"],
          why=W("Why did the output bearing wear out early?", [
              B("Lubrication failed — oil low, old or contaminated", W("Why was the oil not in good condition?", [
                  B("Oil change overdue — no hour-based schedule", R(
                      "Gearbox oil is changed by calendar guesswork, not running hours or oil condition", "Method",
                      prevent=["Put every agitator gearbox on an 8,000 h oil-change schedule in the CMMS",
                               "Take a quarterly oil sample (colour, water, metal fines) and trend it"])),
                  B("Water got in through the breather", R(
                      "Open breathers let humid air and rain into the gearbox (no desiccant breather)", "Environment",
                      prevent=["Fit desiccant breathers and a rain hood on every agitator gearbox",
                               "Check breather colour on weekly rounds and change before saturation"])),
              ])),
              B("Bearing overloaded by misalignment or impeller imbalance", W("Where did the extra load come from?", [
                  B("Coupling not aligned after the last job", R(
                      "No laser alignment and sign-off after drive maintenance", "Method",
                      prevent=["Make recorded laser alignment mandatory after any motor / coupling / gearbox work",
                               "Train fitters on soft-foot and thermal-growth allowance"])),
                  B("Impeller ragged or blade damaged", R(
                      "Fibrous feed and sediment load the impeller unevenly; no inspection at tank outages", "Material",
                      prevent=["Inspect impellers at every digester or tank outage",
                               "Control shredder cut length so long fibres do not reach the digester"])),
              ])),
              B("No early warning — vibration trend not watched", R(
                  "Vibration and bearing temperature are not trended, so wear is found only at failure", "Measurement",
                  prevent=["Monthly handheld vibration route on every agitator gearbox; alarm on a 50 % rise",
                           "Set SCADA alerts at 70 °C bearing temperature and 4.5 mm/s vibration"])),
          ], how="Look at the old bearing: brown varnish or rust means lubrication / water; one-sided wear tracks mean "
                 "misalignment or overload; flaking all round means it reached its fatigue life."),
          case="KB-0412"),
        C("mis", "Coupling misalignment / worn coupling element", "Method", ["vibration", "coupling", "alignment"], [
            "Stop the agitator and apply LOTO",
            "Remove the coupling guard; replace the elastomer element if cracked, hardened or powdering",
            "Check for soft foot and re-torque the motor and gearbox base bolts",
            "Laser-align motor to gearbox: offset ≤ 0.05 mm, angularity ≤ 0.05 mm/100 mm; record the result",
            "Refit the guard, restart and trend vibration for one shift"],
          why=W("Why is the drive out of alignment?", [
              B("Not aligned properly after the last maintenance", W("Why was alignment skipped or poor?", [
                  B("Done by eye / straight edge only", R(
                      "No laser alignment tool or procedure in the reassembly work order", "Method",
                      prevent=["Add laser alignment with a recorded result to the agitator reassembly work order",
                               "Keep a laser alignment kit at site and calibrate it yearly"])),
                  B("Fitter not trained on the tool", R(
                      "Fitters are not trained or certified on laser alignment", "Man",
                      prevent=["Train and sign off all mechanical fitters on laser alignment",
                               "Supervisor countersigns the alignment record before restart"])),
              ])),
              B("Base or mounting has moved", W("Why did the base move?", [
                  B("Base bolts loose from vibration", R(
                      "Base-bolt torque check is not in the PM", "Method",
                      prevent=["Add a quarterly base-bolt torque check with torque values on the PM sheet"])),
                  B("Mounting flange / nozzle flexes with tank movement", R(
                      "Side-entry nozzle and drive bracket not stiff enough for the agitator thrust", "Machine",
                      prevent=["Have the OEM review the bracket stiffness; add gussets or a support leg"])),
              ])),
              B("Coupling element past its life", R(
                  "Coupling elements are replaced only after they fail", "Method",
                  prevent=["Replace elastomer elements every 2 years and inspect them every 3 months"])),
          ], how="Check the alignment record from the last job and the condition of the base bolts and shims."),
          case="KB-0405"),
        C("gland", "Worn gland packing / shaft sleeve scoring", "Machine", ["leakage", "leak", "gland", "seal", "packing"], [
            "Lower the digester level below the agitator nozzle if the design needs it, or close the isolation gate",
            "Stop the agitator and isolate under LOTO",
            "Remove all old packing rings; check the shaft sleeve for grooves and run-out",
            "Replace the sleeve if scored; repack with 5 rings PTFE-graphite, joints staggered 90°",
            "Tighten the gland follower evenly, finger-tight plus a quarter turn; allow 10–20 drops/min on start",
            "Clean the spill area and restore the gearbox oil level if slurry contaminated it"],
          why=W("Why did the packing wear out or the sleeve score?", [
              B("Packing over-tightened to stop a weep", W("Why was it over-tightened?", [
                  B("Crew think any drip is a fault", R(
                      "Operators not trained that a slight weep is needed to cool the packing", "Man",
                      prevent=["Train operators on gland adjustment and the 10–20 drops/min rule",
                               "Post a gland adjustment card at each agitator nozzle"])),
                  B("No gland adjustment procedure", R(
                      "Gland adjustment is done ad hoc with no written method", "Method",
                      prevent=["Write a gland adjustment SOP with torque / turns and a weep target"])),
              ])),
              B("Grit in the slurry ground the sleeve", R(
                  "Sand and grit from feed (press mud, dung) not removed before the digester", "Material",
                  prevent=["Add grit removal / settling at the feed hall and track sand content",
                           "Use a hard-coated (ceramic / tungsten carbide) shaft sleeve"])),
              B("Shaft runs out and hammers the packing", R(
                  "Shaft run-out and bearing condition not checked at repacking", "Method",
                  prevent=["Measure shaft run-out with a dial gauge at every repack; limit 0.1 mm"])),
          ], how="Look at the sleeve under the packing: a polished groove means grit or over-tight packing; uneven "
                 "wear on one side means shaft run-out."),
          case="KB-0377"),
        C("rag", "Impeller ragging / imbalance from fibrous build-up", "Material", ["vibration", "fibre", "rag", "knock"], [
            "Try a short reverse run if the drive and VFD allow it — it often sheds the rag",
            "If not, stop the agitator under LOTO; lower the tank level or use the service hatch to reach the impeller",
            "Clear fibre and plastic wrap from the blades and hub; check blade bolts and blade angle",
            "Restart and confirm vibration and current are back to normal",
            "Check the shredder cut length and feed composition upstream"],
          why=W("Why is fibre wrapping on the impeller?", [
              B("Long fibres are reaching the tank", W("Why are fibres not cut short enough?", [
                  B("Shredder blades blunt or cut length too long", R(
                      "Shredder blade condition and cut length are not checked routinely", "Machine",
                      prevent=["Weekly shredder blade check; sharpen / rotate at OEM interval",
                               "Agree a maximum cut length (≈ 20–40 mm) for straw and napier grass"])),
                  B("Bale twine and plastic not removed", R(
                      "No foreign-matter picking at feedstock reception", "Material",
                      prevent=["Add a picking step for twine, plastic and sacks at reception",
                               "Feedstock acceptance criteria in the supplier agreement"])),
              ])),
              B("Agitator runs too slow or too rarely", R(
                  "Mixing schedule (on/off cycle, speed) not adjusted when the feed got more fibrous", "Method",
                  prevent=["Review the mixing interval and VFD speed with the OEM when feed recipe changes",
                           "Add a short daily reverse cycle where the drive allows it"])),
          ], how="Pull a handful of the wrap: twine or plastic points to reception; long grass stems point to the shredder."),
          case="KB-0401"),
        C("sed", "Overload from sediment, floating crust or thick (high-TS) contents", "Material",
          ["current", "trip", "overload", "crust", "foam", "sediment"], [
            "Reduce feeding to the digester and check its total solids (TS) and level",
            "Run the agitators in sequence at full speed to break the crust; do not start all at once",
            "If the motor is tripping on overload, do not keep resetting — investigate under LOTO",
            "Dilute with recirculated digestate / liquid fraction to bring TS back below about 10–12 %",
            "If foam is involved, add antifoam per SOP-DIG-01 and check FOS/TAC",
            "Plan a sediment removal if the tank volume has dropped (check with a level/volume test)"],
          why=W("Why are the contents too thick or layered for the agitator?", [
              B("Feed too thick or too sandy", W("Why did the feed get thicker?", [
                  B("More press mud / dry feed without dilution", R(
                      "Feed recipe has no total-solids limit or dilution rule", "Method",
                      prevent=["Set a feed TS target (≈ 10–12 %) and a daily TS test at the feed hall",
                               "Add dilution water / recirculate liquid fraction when TS rises"])),
                  B("Sand and grit settling at the bottom", R(
                      "Feedstock sand content is not tested or controlled", "Material",
                      prevent=["Test sand / ash content of press mud and dung loads weekly",
                               "Add a sand trap or settling step before the digester"])),
              ])),
              B("Agitators were stopped for a long time", W("Why were the agitators off?", [
                  B("Breakdown with no standby plan", R(
                      "No contingency mixing plan when one agitator is down", "Method",
                      prevent=["When an agitator is down, run the others longer and cut feed rate",
                               "Keep a critical spares kit (bearings, seal, coupling) for agitators"])),
                  B("Power-saving mixing schedule", R(
                      "Mixing on/off cycle set to save power without checking for crust", "Man",
                      prevent=["Check the digester surface through the sight glass every shift",
                               "Agree minimum mixing hours per day with process engineering"])),
              ])),
          ], how="Check the digester sight glass and the TS lab results for the last week."),
          case="KB-0402"),
        C("lube", "Gearbox oil low, wrong grade or water-contaminated", "Man", ["oil", "lube", "grease", "oil level"], [
            "Stop the agitator and apply LOTO",
            "Check level at the sight glass; look for leaks at the input / output oil seals and drain plug",
            "If milky, drain, flush and refill with ISO VG 320 synthetic gear oil; replace the breather",
            "Fix the leak source (oil seal, gasket) before refilling",
            "Restart, then check bearing temperature after 1 h and oil level after 24 h"],
          why=W("Why was the gearbox oil not right?", [
              B("Level dropped and nobody noticed", W("Why was the low level missed?", [
                  B("Sight glass not on the round", R(
                      "Gearbox oil level is not on the shift lubrication round", "Man",
                      prevent=["Add sight-glass level to the shift round with a tick-sheet",
                               "Mark min / max on every sight glass"])),
                  B("Slow leak at the output seal", R(
                      "Gearbox oil seals are not replaced at overhaul", "Method",
                      prevent=["Replace input / output oil seals at every gearbox overhaul"])),
              ])),
              B("Wrong oil grade topped up", R(
                  "Lube points not labelled and no lubrication schedule", "Man",
                  prevent=["Colour-code and label every lube point with the oil grade",
                           "Keep one lubrication schedule and train the crew on it"])),
              B("Water got into the oil", R(
                  "Breather and seals exposed to rain and hose-down water", "Environment",
                  prevent=["Fit desiccant breathers and rain hoods; no hosing near gearboxes",
                           "Check oil for water after the monsoon and after heavy washdown"])),
          ], how="Compare the oil in the gearbox with a fresh sample of the specified grade, and check the lubrication log."),
          case="KB-0403"),
        C("sensor", "Vibration / temperature sensor fault (false alarm)", "Measurement", ["vibration", "alarm", "false"], [
            "Take a handheld vibration and IR temperature reading at the same point as the fixed sensor",
            "If they disagree, check the sensor mounting (stud / magnet), cable and connector",
            "Re-fix or replace the sensor and verify the SCADA scaling and alarm limits",
            "Keep the agitator in service only if handheld readings are normal; log the event"],
          why=W("Why is the sensor reading wrong?", [
              B("Sensor loose or badly mounted", R(
                  "Sensors mounted with magnets / adhesive instead of studs; not checked in PM", "Measurement",
                  prevent=["Stud-mount vibration sensors on a spot-faced surface",
                           "Add a sensor mounting and cable check to the quarterly PM"])),
              B("Cable or connector damaged / wet", R(
                  "Field cables unprotected from rain, washdown and rodents", "Environment",
                  prevent=["Run sensor cables in conduit with sealed glands",
                           "Inspect connectors after the monsoon"])),
              B("Wrong scaling or alarm limit in SCADA", R(
                  "Instrument settings not verified after replacement or SCADA change", "Measurement",
                  prevent=["Keep an instrument register with scaling and limits; verify after any change",
                           "Yearly calibration check against a handheld reference"])),
          ], how="Compare the handheld reading with the SCADA value at the same moment."),
          case="KB-0404"),
        C("elec", "Motor or VFD electrical fault", "Machine", ["trip", "current", "motor", "hum"], [
            "Isolate the motor at the MCC and apply LOTO",
            "Have the electrician check insulation resistance, terminal tightness and all three phase currents",
            "Read the VFD fault log; check the overload setting against the motor nameplate",
            "Restart and record running current; compare with the commissioning value"],
          why=W("What caused the electrical fault?", [
              B("Moisture in the motor or terminal box", R(
                  "Motor terminal boxes and glands not sealed against rain and washdown", "Environment",
                  prevent=["Fit proper cable glands and gaskets; add rain canopies on outdoor motors",
                           "Megger test outdoor agitator motors before and after the monsoon"])),
              B("Loose terminal / failing contactor", R(
                  "No thermographic scan of MCC and VFD panels", "Machine",
                  prevent=["Thermographic scan of MCC / VFD panels every quarter", "Re-torque terminals in PM"])),
              B("Overload or VFD setting wrong", R(
                  "Protection settings not verified after motor or VFD replacement", "Measurement",
                  prevent=["Record and verify overload / VFD parameters in the motor register"])),
          ]),
          case="KB-0406"),
    ],
    "questions": [
        Q("temp", "Can you put the IR gun on the gearbox output bearing housing — what does it read?", [
            ("Below 70°C", _rest(1.2, brg=0.3, lube=0.5, mis=1.0, sensor=1.6)),
            ("70–85°C", _rest(0.9, brg=2.0, lube=1.6, mis=1.4, sed=1.2, sensor=0.6, gland=0.8)),
            ("Above 85°C", _rest(0.6, brg=3.5, lube=1.8, mis=1.2, sed=0.8, gland=0.4, sensor=0.3),
             ["rotating_critical"]),
        ], ["vibration", "sound", "temperature", "bearing", "hot"],
          {"tag": "bearing_temp_c", "option": 0, "above": 80},
          how="Stand on the platform clear of the coupling guard and aim the IR gun at the bearing housing where the "
              "output shaft leaves the gearbox (painted metal, not shiny). Don't touch it — it can be very hot.",
          purpose="A hot output bearing is the clearest sign that the bearing itself is failing."),
        Q("oil", "Check the gearbox oil sight glass and, if you can, drain a small sample. What does it look like?", [
            ("Clean amber, level OK", _rest(1.2, brg=0.3, lube=0.15, sensor=1.3)),
            ("Dark with metal fines", _rest(0.6, brg=4.0, lube=1.0, mis=1.0)),
            ("Milky / water ingress", _rest(0.7, lube=3.5, brg=1.5, gland=1.3)),
            ("Low level or oil leaking", _rest(0.7, lube=4.0, brg=1.3, gland=1.1)),
        ], ["oil", "lube", "bearing", "vibration", "sound"],
          how="Read the sight glass with the agitator running. For a sample, stop under LOTO, put a clean jar under the "
              "drain plug and take about 100 ml; wear gloves, the oil may be hot.",
          purpose="Metal fines mean something inside is wearing; milky oil means water got in; low oil starves the "
                  "bearings."),
        Q("coupling", "With the agitator stopped under LOTO, take the coupling guard off. How does the coupling look?", [
            ("Intact, no play", _rest(1.1, brg=1.2, mis=0.25)),
            ("Cracked / worn element", _rest(0.8, mis=3.5)),
            ("Visible offset or loose base bolts", _rest(0.8, mis=3.5, brg=1.0)),
        ], ["vibration", "coupling"],
          how="Only after LOTO and a try-start: remove the guard, look at the rubber element for cracks or black dust, "
              "rock the shafts by hand for play, and try the base bolts with a spanner. Refit the guard before restart.",
          purpose="A worn or misaligned coupling shakes the drive and then destroys the gearbox bearings."),
        Q("leak", "Walk round the drive and the tank nozzle — is anything leaking?", [
            ("Slurry pouring from the shaft gland", _rest(0.7, gland=4.5)),
            ("Oil from the gearbox seals or plug", _rest(0.8, lube=3.0, brg=1.3, gland=1.0)),
            ("Nothing beyond a slight weep", _rest(1.1, gland=0.25, lube=0.6)),
        ], ["leakage", "leak", "gland", "seal", "oil"],
          how="Look under the gland where the shaft enters the tank and under the gearbox. Slurry at the shaft is the "
              "gland; oil on the gearbox or bracket is an oil seal. Keep hands away from the turning shaft.",
          purpose="Where the leak comes from separates a gland problem from a gearbox oil problem straight away."),
        Q("drip", "Look at the gland where the shaft goes into the tank. How much is dripping?", [
            ("Slight weep, 10–20 drops/min", _rest(1.05, gland=0.3)),
            ("Steady stream of slurry", _rest(0.8, gland=4.0)),
            ("Bone dry and hot at the gland", _rest(0.9, gland=2.5)),
        ], ["leakage", "leak", "gland", "seal", "packing"],
          how="Watch the gland follower for a minute with a torch and count drips. You can feel for heat with the back "
              "of your hand near (not on) the gland housing — never reach past the guard to the turning shaft.",
          purpose="A packed gland should weep slightly to stay cool; a stream means worn packing, a dry hot gland "
                  "means it is over-tightened and scoring the sleeve."),
        Q("noise", "Stand by the drive for a minute. What does it sound like?", [
            ("Smooth, normal hum", _rest(0.7, sensor=3.0, brg=0.3, mis=0.5, rag=0.5, gland=1.2, sed=1.0, elec=0.8)),
            ("Growl or grinding from the gearbox", _rest(0.7, brg=3.0, lube=2.0)),
            ("Rhythmic knock once per turn", _rest(0.7, rag=3.0, mis=1.5, sed=1.3, brg=1.0)),
            ("Clunk from the coupling at start", _rest(0.8, mis=3.0)),
            ("Electrical buzz from the motor", _rest(0.7, elec=3.5)),
        ], ["vibration", "sound", "noise", "knock"], {"tag": "vibration_mm_s", "option": 0, "above": 4.5},
          how="Listen at the motor, the coupling guard and the gearbox in turn. A long screwdriver held on the gearbox "
              "housing works as a stethoscope. Stay outside the guard.",
          purpose="Each fault has its own sound: a bearing growls, a ragged impeller knocks once per turn, a "
                  "coupling clunks, a motor fault buzzes."),
        Q("current", "Ask the control room or look at the MCC ammeter: how does the motor current look?", [
            ("Normal and steady", _rest(1.0, elec=0.3, sed=0.3, rag=0.6, gland=1.1, sensor=1.4)),
            ("High, creeping up over days", _rest(0.9, sed=3.5, rag=1.8, brg=1.3, lube=1.2, elec=1.0)),
            ("Swings up and down every turn", _rest(0.8, rag=3.5, sed=1.2, mis=1.4, brg=1.0)),
            ("Trips or phases unequal", _rest(0.7, elec=4.0, sed=1.5, brg=1.1)),
        ], ["trip", "current", "motor", "overload"], {"tag": "motor_current_a", "option": 0, "above": 20},
          how="Read the ammeter on the MCC door or the SCADA current trend for the last week, and compare with the "
              "full-load amps on the motor nameplate.",
          purpose="Current tells me whether the agitator is fighting thick contents, a wrapped impeller or an "
                  "electrical fault."),
        Q("handheld", "If you have the handheld vibration meter, take a reading next to the fixed sensor. Does it agree "
                      "with SCADA?", [
            ("Yes, both read high", _rest(1.1, sensor=0.2)),
            ("Handheld normal, SCADA high", _rest(0.4, sensor=4.0)),
            ("Sensor loose or cable damaged", _rest(0.7, sensor=4.0)),
        ], ["vibration", "alarm"],
          how="Hold the handheld probe on the bearing housing right next to the fixed sensor and read mm/s. Then check "
              "the fixed sensor is screwed down tight and its cable is not cut or wet.",
          purpose="Before we stop a digester agitator, make sure the alarm is real and not a loose sensor."),
        Q("surface", "Look through the digester or tank sight glass. What does the surface look like?", [
            ("Moving evenly, no crust", _rest(1.1, sed=0.3, rag=1.0)),
            ("Thick crust / floating layer", _rest(0.9, sed=3.5, rag=1.3)),
            ("Foam up to the sight glass", _rest(0.9, sed=2.5)),
            ("Surface still — not mixing", _rest(0.9, sed=2.0, elec=1.5, mis=1.3, rag=1.3)),
        ], ["crust", "foam", "current", "overload"],
          how="Use the sight glass on the digester roof or wall with the agitators running. Do not open any hatch on a "
              "digester — it is a gas-filled space. Use a torch if the glass is dirty.",
          purpose="A crust, foam or a still surface tells me the contents are fighting the agitator."),
        Q("feed", "Has the feed to this tank changed in the last week or two?", [
            ("No change", _rest(1.1, rag=0.5, sed=0.5)),
            ("More long fibre (straw, napier)", _rest(0.8, rag=4.0, sed=1.3)),
            ("Thicker — more press mud or sand", _rest(0.9, sed=3.5, rag=1.2)),
        ], ["fibre", "crust", "current", "overload"],
          how="Ask the feed-hall operator or check the feeding log: feedstock mix, tonnes per day and the last TS result.",
          purpose="Most ragging and overload problems start with a change in what we feed."),
        Q("work", "Has anyone worked on this agitator drive recently?", [
            ("No work in the last month", _rest(1.05, mis=0.4, lube=0.8)),
            ("Motor, coupling or gearbox refitted", _rest(0.9, mis=3.5, lube=1.3)),
            ("Oil changed or topped up", _rest(0.9, lube=2.5, brg=1.2)),
        ], ["coupling", "alignment", "oil"],
          how="Check the maintenance log or work-order history for this agitator, or ask the shift fitter.",
          purpose="Many faults start right after maintenance — a missed alignment or the wrong oil."),
    ],
}

MAINTENANCE = {
    "Agitator": {
        "summary": "Digester and tank agitators (side-entry with gearbox, top-entry long-shaft) keep the contents mixed, "
                   "stop crust and sediment forming and spread heat. Gearbox lubrication, output bearings, coupling "
                   "alignment, the shaft gland and impeller condition are the main maintenance items; process "
                   "conditions (TS, fibre, crust, foam) drive much of the load.",
        "pm": [
            ("Every shift", "Listen for abnormal noise; check gland weep, gearbox oil level and digester surface via sight glass"),
            ("Weekly", "IR temperature on gearbox output bearing; check breather colour; check motor current trend"),
            ("Monthly", "Handheld vibration route (gearbox and motor bearings); adjust gland packing; grease motor bearings"),
            ("Quarterly", "Gearbox oil sample (colour, water, fines); coupling element inspection; base-bolt torque check"),
            ("8,000 h / yearly", "Gearbox oil change (ISO VG 320 synthetic); laser alignment check; sensor mounting check"),
            ("Tank outage", "Inspect impeller blades and hub for wear, wrap and loose bolts; inspect shaft and sleeve"),
        ],
        "failure_modes": ["Gearbox output bearing wear", "Coupling misalignment / worn element",
                          "Gland packing wear and sleeve scoring", "Impeller ragging by fibres",
                          "Overload from crust, sediment or high-TS contents", "Water-contaminated or low gearbox oil",
                          "False vibration alarm from a loose sensor", "Motor / VFD electrical faults"],
        "operating_limits": [("Gearbox output bearing temperature", "55–70 °C normal; 70–85 °C alert; > 85 °C trip"),
                             ("Vibration (ISO 10816, class II)", "< 4.5 mm/s; stop and inspect > 7.1 mm/s"),
                             ("Gearbox oil level", "Mid sight glass (60–80 %)"),
                             ("Gland weep", "10–20 drops/min"),
                             ("Coupling alignment", "≤ 0.05 mm offset, ≤ 0.05 mm/100 mm angularity"),
                             ("Motor current", "≤ nameplate FLA; alert on +15 % over the commissioning value")],
    },
}

CONDITIONS = [
    {"id": "DIG", "title": "Digesters (mesophilic)", "areas": ["D1", "D2", "D3", "D4"],
     "params": [
         ("Temperature", "37–40 °C (mesophilic); change < 1 °C per day",
          "Methanogens are sensitive to temperature swings; a fast change cuts gas yield and lets acids build up",
          "Check the hot water generator and heating-coil flow; feed smaller amounts until stable; never change "
          "the setpoint more than 0.5–1 °C per day"),
         ("pH", "7.0–8.0",
          "Below about 6.8 the methanogens slow down and the digester can sour",
          "Check FOS/TAC and VFA; cut feeding; add alkalinity (sodium bicarbonate / lime) only on process engineer advice"),
         ("FOS/TAC", "0.2–0.4 (stable); 0.4–0.5 watch; > 0.5 act",
          "Ratio of volatile acids to buffer — the earliest warning of overfeeding, before pH drops",
          "Above 0.4: hold the feed rate; above 0.5: cut feed by 20–50 % and re-test daily; > 0.6 stop feeding"),
         ("Volatile fatty acids (VFA / FOS)", "< 3,000 mg/L acetic-acid equivalent; rising trend is the alarm",
          "Acids build up when bacteria cannot keep up with the feed",
          "Reduce feed, check temperature and mixing, check for inhibitors (ammonia, H2S, salts)"),
         ("Alkalinity (TAC)", "> 8,000 mg/L CaCO3",
          "The buffer that holds pH steady when acids rise",
          "If it falls, reduce feed; recirculate digestate; consider bicarbonate dosing"),
         ("Organic loading rate (OLR)", "2–4 kg VS/m³·day (do not raise > 10–15 % per week)",
          "Overloading is the most common cause of acidification and foaming",
          "Follow the feeding plan; increase slowly; recheck FOS/TAC after each step"),
         ("Hydraulic retention time (HRT)", "≥ 30–40 days for agri residue / press mud",
          "Too short a retention washes bacteria out and leaves fibre undigested",
          "Reduce the daily feed volume or dilution water; check the digester volume is not lost to sediment"),
         ("Total solids in digester", "6–10 % (keep below about 12 %)",
          "Thick contents overload agitators, form crust and sediment, and cause hot spots",
          "Dilute with liquid fraction / water; increase mixing; check feed TS"),
         ("Ammonium-N (NH4-N)", "< 3,000 mg/L",
          "High ammonia (from manure / poultry litter) inhibits methanogens, worse at high pH and temperature",
          "Reduce nitrogen-rich feed (poultry litter); dilute; balance C:N with crop residue"),
         ("Foam / scum", "No foam at the sight glass; thin mobile surface layer",
          "Foam blocks gas lines and pressure-relief valves and can push slurry into the gas system",
          "Reduce feed; check FOS/TAC; run agitators; dose antifoam per SOP-DIG-01; check gas line condensate traps"),
         ("H2S in raw biogas", "< 2,000 ppm at digester outlet (typical with biological desulphurisation)",
          "High H2S corrodes gas equipment and overloads the H2S scrubber",
          "Check air / micro-aeration dosing for desulphurisation; reduce sulphur-rich feed; dose iron salts if advised"),
         ("Methane content in raw gas", "50–60 % CH4; CO2 40–50 %",
          "Falling CH4 is a sign of process stress or air ingress",
          "Check FOS/TAC; check micro-aeration air dose (O2 < 1 %); check for leaks"),
         ("Gas holder / digester pressure", "Within the design band (typically 2–5 mbar on a double-membrane roof)",
          "High pressure lifts the pressure-relief valve and vents gas; low pressure can draw in air",
          "Check gas take-off (BUU running), condensate traps and PRV seal liquid; never work on the roof alone"),
         ("Agitator run hours", "As per mixing schedule; no tank with all agitators off > 2 h",
          "Without mixing, crust forms on top and sand settles at the bottom within hours",
          "Restart agitators in sequence; if one is down, run the others longer and cut feed"),
     ],
     "notes": ["Trend FOS/TAC daily and look at the direction, not just the value — a steady rise over 3–4 days is the alarm.",
               "Never open a digester hatch or enter the roof area without a gas test and a permit; digesters contain H2S and methane.",
               "After any agitator outage, check the surface for crust before restarting feed at full rate.",
               "Change one thing at a time (feed rate, recipe, temperature) and wait a few days to see its effect."]},
]

CASES = [
    K("KB-0412", ["Agitator"], ["vibration", "sound", "bearing", "temperature"],
      "High body vibration with abnormal sound and hot gearbox bearing on digester agitator",
      "Gearbox output bearing wear, accelerated by coupling misalignment and overdue oil change",
      "Stopped agitator under LOTO, drained oil (dark with fines), replaced output bearing set and oil seal, "
      "refilled ISO VG 320, laser-aligned coupling, trended vibration for one shift",
      why=["Why the vibration and noise? Output bearing outer race spalled",
           "Why did the bearing fail early? Oil was dark with metal fines and 3,000 h past its change",
           "Why was the oil not changed? Oil changes were calendar-based and the agitator was missed",
           "Why was it missed? No running-hour based lubrication schedule in the CMMS"],
      category="Method",
      prevent="Hour-based oil change schedule in CMMS; quarterly oil sampling; monthly vibration route"),
    K("KB-0377", ["Agitator"], ["leakage", "leak", "gland", "seal"], "Slurry leakage at agitator shaft gland",
      "Worn gland packing and shaft sleeve scoring",
      "Lowered level, isolated under LOTO, replaced scored sleeve, repacked 5 rings staggered 90°, set 10–20 drops/min",
      why=["Why the leak? Packing worn and sleeve had a deep groove",
           "Why the groove? Packing was over-tightened to stop every drip and ran hot, and grit ground the sleeve",
           "Why over-tightened? Operators were not trained that the gland needs a slight weep",
           "Why no training? No gland adjustment procedure existed"],
      category="Man", prevent="Gland adjustment SOP and training; hard-coated sleeve; grit check on feed"),
    K("KB-0401", ["Agitator"], ["vibration", "fibre", "rag", "current", "knock"],
      "Rhythmic knock and swinging current on digester side agitator",
      "Impeller wrapped with long napier grass fibre and bale twine",
      "Reverse run did not clear it; lowered level, cleared wrap under LOTO, checked blade bolts",
      why=["Why the knock? Impeller out of balance with a fibre wrap on two blades",
           "Why fibre on the impeller? Long napier stems up to 150 mm were in the feed",
           "Why so long? Shredder blades were blunt and cut length was never checked",
           "Why never checked? Shredder blade inspection was not in the weekly PM"],
      category="Material", prevent="Weekly shredder blade check and cut-length target; twine picking at reception"),
    K("KB-0402", ["Agitator"], ["current", "trip", "overload", "crust", "sediment"],
      "Digester agitators tripping on overload with thick crust on the surface",
      "High total solids (14 %) and sand from press mud with reduced mixing hours",
      "Cut feed by 30 %, diluted with liquid fraction, ran agitators in sequence to break crust, TS back to 9 %",
      why=["Why the trips? Motor current above FLA fighting a crust and thick contents",
           "Why thick contents? Feed switched to more press mud without extra dilution",
           "Why no dilution? Feed recipe had no TS limit and TS was tested only weekly"],
      category="Method", prevent="Feed TS target ≤ 12 % with daily TS test; dilution rule in feeding SOP"),
    K("KB-0403", ["Agitator"], ["oil", "lube", "temperature", "bearing"],
      "Milky gearbox oil and rising bearing temperature on top agitator after the monsoon",
      "Water ingress through an open breather and washdown spray",
      "Drained and flushed gearbox, refilled ISO VG 320, fitted desiccant breather and rain hood",
      why=["Why the hot bearing? Oil emulsified with water lost its film strength",
           "Why water in the oil? Open breather on the roof drew in humid air and rain",
           "Why an open breather? Original breather never upgraded; no post-monsoon oil check"],
      category="Environment", prevent="Desiccant breathers on all gearboxes; post-monsoon oil water check"),
    K("KB-0404", ["Agitator"], ["vibration", "alarm", "false"],
      "SCADA high-vibration alarm on agitator with smooth running drive",
      "Vibration sensor magnet mount loose on a painted surface",
      "Handheld reading 2.1 mm/s vs SCADA 9 mm/s; stud-mounted the sensor on a spot-faced pad; verified scaling",
      why=["Why the alarm? Sensor rattled on its magnet mount",
           "Why loose? Magnet mounted on thick paint, no stud",
           "Why not caught? Sensor mounting not in any PM checklist"],
      category="Measurement", prevent="Stud-mount all fixed vibration sensors; quarterly sensor check"),
    K("KB-0405", ["Agitator"], ["vibration", "coupling", "alignment"],
      "Vibration rising after gearbox replacement on feed-hall side agitator",
      "Motor-to-gearbox misalignment; coupling element cracking",
      "Replaced coupling element, corrected soft foot, laser-aligned to 0.03 mm, recorded result",
      why=["Why the vibration? 0.4 mm offset at the coupling",
           "Why misaligned? Gearbox refitted and aligned by straight edge",
           "Why straight edge? Laser kit was at another site and the work order did not require laser alignment"],
      category="Method", prevent="Laser alignment with recorded result made mandatory in the reassembly work order"),
    K("KB-0406", ["Agitator"], ["trip", "current", "motor"],
      "Agitator motor tripping after heavy rain",
      "Moisture in the motor terminal box lowered insulation resistance",
      "Dried terminal box, replaced gland and gasket, megger tested > 100 MΩ, added rain canopy",
      why=["Why the trip? Earth fault on the motor supply",
           "Why an earth fault? Water in the terminal box",
           "Why water? Cable gland unsealed and motor exposed to rain without a canopy"],
      category="Environment", prevent="Sealed glands and rain canopies; pre-monsoon megger testing"),
]
