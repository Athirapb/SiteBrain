"""Solid-liquid separation (SLS): decanter centrifuges (Decanter 1-3) and screw-press / screen separators (WAM 1-5),
plus the operating-condition profiles for the SLS area and the CDT & PST storage area.

Sources: decanter centrifuge OEM operation & maintenance manuals (Alfa Laval, Flottweg, GEA - main bearing
regreasing, back-drive / differential speed and torque control, scroll hard-facing and tile renewal, bowl flushing
on shutdown, ISO 10816-3 vibration zones), screw-press separator OEM literature (WAMGROUP / Sepcom: SINT screw,
self-cleaning screen basket, counter-pressure outlet, ~25-35 % DM solids), American Biogas Council operator training
on coarse / fine solids separation (feed 3-8 % TS, polymer 4-10 kg/t DS, capture 85-95 %), wastewater biosolids
dewatering guidance (polymer make-up and ageing, centrate TSS), reliability / RCA articles on decanter failure modes,
plant incident history (incident_log_separation.csv) and SOP-ROT-01 (LOTO) / SOP-SLS-01 (polymer dosing).
"""
from .dsl import B, C, K, Q, R, W

TREES = {}

# ----------------------------------------------------------------------------------------------------------------------
# Decanter centrifuge
# ----------------------------------------------------------------------------------------------------------------------
TREES["Decanter"] = {
    "causes": [
        C("lube", "Main bearing lubrication starvation", "Machine", ["grease", "bearing", "temperature", "lube", "vibration"], [
            "If a main bearing is above 85 °C or vibration is in the alarm zone, stop the decanter and let it run down "
            "fully (it can coast for 10-20 minutes) - never open guards on a turning bowl",
            "Regrease both main bearings with the OEM grease grade and quantity (no over-packing - it runs hot)",
            "Check the auto-lubricator: reservoir level, pump stroke, and that grease reaches each bearing point",
            "Restart at reduced feed; trend bearing temperature and vibration every 30 min for the shift",
            "If temperature or vibration does not settle within 2 hours, plan a main bearing change"],
          why=W("Why did the main bearing run short of grease?", [
              B("Auto-lubricator empty or not pumping", W("Why was the lubricator not delivering?", [
                  B("Reservoir ran empty and nobody noticed", R(
                      "Lubricator reservoir level is not on the shift round and has no low-level alarm", "Man",
                      prevent=["Add lubricator reservoir level to the SLS shift checklist with a tick-sheet",
                               "Wire the lubricator low-level / fault contact to SCADA as an alarm"])),
                  B("Grease line blocked or broken", R(
                      "Grease lines and fittings are not inspected in PM; hardened grease plugs the line", "Method",
                      prevent=["Monthly check that grease emerges at each bearing point (disconnect and pump)",
                               "Replace grease lines every 2 years; use the OEM grease only"])),
              ])),
              B("Manual regreasing interval missed", R(
                  "Regreasing interval is not tied to running hours in the PM system", "Method",
                  prevent=["Schedule regreasing by running hours from the OEM table (bowl speed / bearing size)",
                           "Record grease quantity per bearing in the lube log"])),
              B("Wrong or mixed grease used", R(
                  "Lube points are not labelled and the store issues a general-purpose grease", "Material",
                  prevent=["Label each decanter bearing with grease grade and shot count",
                           "Stock only the OEM high-speed bearing grease for decanters"])),
          ], how="Check the lube log, the lubricator reservoir and whether fresh grease appears at the bearing purge."),
          case="KB-0333"),
        C("solids", "Uneven solids build-up in the bowl (stopped without flushing)", "Method",
          ["vibration", "cleaning", "flush", "stop", "power"], [
            "Do not run up to full speed with a large imbalance - keep the decanter stopped if vibration trips at start",
            "Run the OEM flush / CIP sequence at low bowl speed with hot water until vibration settles",
            "If vibration stays high, stop under LOTO, let the bowl run down fully, open and dig out the bowl",
            "Restart empty, confirm vibration below 4.5 mm/s, then restore feed and polymer slowly"],
          why=W("Why did solids stay in the bowl?", [
              B("Machine tripped on a power cut or E-stop", W("Why was the bowl not flushed after the trip?", [
                  B("No flush procedure after an uncontrolled stop", R(
                      "Restart procedure does not require a flush after a trip or power failure", "Method",
                      prevent=["Add 'flush at low speed before restart after any trip' to SOP-SLS-01",
                               "Program an automatic flush step into the decanter PLC on trip recovery"])),
                  B("No flush water available during the outage", R(
                      "Flush water supply depends on a pump that is not on backup power", "Environment",
                      prevent=["Put the decanter flush-water supply on the DG / UPS-backed board",
                               "Provide a gravity flush tank for power-failure shutdowns"])),
              ])),
              B("Normal stop done without the flush step", W("Why was the flush step skipped?", [
                  B("Operator not trained on the shutdown sequence", R(
                      "Decanter shutdown sequence is not part of operator training", "Man",
                      prevent=["Train and sign off all SLS operators on the stop / flush sequence",
                               "Post the shutdown sequence at the decanter panel"])),
                  B("Flush skipped to save time or water", R(
                      "Shutdown is run manually with no interlock to enforce the flush", "Method",
                      prevent=["Use the PLC auto-shutdown that includes the flush; block manual stop except E-stop"])),
              ])),
          ], how="Look at the trip and stop log in the decanter PLC / SCADA for the last stop before the vibration."),
          case="KB-0201"),
        C("scroll", "Worn scroll flights / tiles (imbalance and poor conveying)", "Machine",
          ["wear", "scroll", "torque", "cake", "tile", "vibration"], [
            "Stop the decanter, let it run down fully and apply LOTO before opening",
            "Inspect scroll flight tips and wear tiles; measure flight-to-bowl clearance against OEM limits",
            "Send the rotating assembly for re-tiling / hard-facing and dynamic balancing at an approved workshop",
            "Inspect feed zone and solids discharge ports for erosion at the same time",
            "After reassembly, verify vibration below 4.5 mm/s and torque back to baseline"],
          why=W("Why did the scroll wear faster than expected?", [
              B("Sand and grit in the digestate", W("Why is so much grit reaching the decanter?", [
                  B("Feedstock carries sand (press mud, soiled feed)", R(
                      "Feedstock grit content is not measured or limited at reception", "Material",
                      prevent=["Add a sand / inerts test at feedstock reception with an acceptance limit",
                               "Blend high-grit feedstock with clean substrate"])),
                  B("Grit not removed upstream", R(
                      "Grit trap / hydrocyclone ahead of SLS is not cleaned on schedule", "Method",
                      prevent=["Schedule grit removal and log volumes removed weekly"])),
              ])),
              B("Wear not caught early", R(
                  "Scroll wear is not tracked by torque trend or periodic inspection", "Method",
                  prevent=["Trend torque at constant feed weekly - a slow creep means worn flights",
                           "Inspect flights and tiles every 4,000 h or per OEM and record tip wear"])),
          ], how="Compare torque at the same feed rate today with a month ago, and check the last scroll inspection report."),
          case="KB-0202"),
        C("gbox", "Gearbox / back-drive fault (differential speed unstable)", "Machine",
          ["gearbox", "back-drive", "torque", "trip", "noise", "vibration"], [
            "Stop the decanter, let it run down fully and apply LOTO",
            "Check gearbox oil level and condition; take an oil sample for wear metals and water",
            "Check the back-drive motor / VFD fault log and the torque sensor",
            "Turn the scroll by hand (if OEM allows) and feel for rough or tight spots",
            "Send the gearbox to the OEM for overhaul if metal is found or noise persists"],
          why=W("Why did the gearbox / back-drive fail?", [
              B("Gearbox oil low, old or contaminated", W("Why was the gearbox oil not right?", [
                  B("Oil changes overdue", R(
                      "Gearbox oil change and oil sampling are not in the PM plan", "Method",
                      prevent=["Change gearbox oil at OEM hours and sample every 3 months for wear metals"])),
                  B("Leaking oil seal on the gearbox", R(
                      "Gearbox seal leaks are not reported or fixed promptly", "Man",
                      prevent=["Add gearbox leak check to the shift round; raise a work order the same day"])),
              ])),
              B("Repeated torque overloads from plugging", R(
                  "Feed and differential settings let the machine run at the torque limit for long periods", "Method",
                  prevent=["Set the torque control to keep load at 50-70 % of maximum",
                           "Alarm on the number of high-torque events per shift"])),
              B("Back-drive VFD or encoder fault", R(
                  "VFD and speed encoders are not checked in electrical PM", "Machine",
                  prevent=["Include back-drive VFD, encoder and cabling in the quarterly electrical PM",
                           "Keep a spare encoder in stores"])),
          ], how="Read the gearbox oil sight glass and the back-drive fault history before deciding."),
          case=None),
        C("diff", "Wrong differential speed / pond depth setting", "Method",
          ["differential", "setting", "torque", "wet cake", "plug"], [
            "Return differential speed and pond (weir) setting to the last good recipe from the settings log",
            "Reduce feed rate while adjusting; change differential in small steps (0.5-1 rpm) and wait 15 min",
            "If the bowl plugged, stop feed, flush at low speed and restart",
            "Record the new setpoints and the resulting cake dryness / centrate quality"],
          why=W("Why was the setting wrong?", [
              B("Changed by someone without a procedure", W("Why could it be changed without control?", [
                  B("No recipe / setpoint log for the decanters", R(
                      "Decanter setpoints are not recorded or controlled", "Method",
                      prevent=["Keep a setpoint log (feed, polymer, differential, pond) and approve changes via MOC",
                               "Password-protect differential and pond settings on the HMI"])),
                  B("Operator tuning by trial and error", R(
                      "Operators are not trained on how differential speed affects torque and cake", "Man",
                      prevent=["Train operators: lower differential = drier cake but higher torque; higher = wetter"])),
              ])),
              B("Setting not adapted when feed changed", R(
                  "No procedure to retune when digestate TS or feedstock mix changes", "Method",
                  prevent=["Add a retune step to SOP-SLS-01 when feed TS changes by more than 1 %",
                           "Use automatic torque control (differential follows torque) where available"])),
          ], how="Compare current differential and pond settings with the setpoint log and the date of the change."),
          case="KB-0204"),
        C("polymer", "Poor flocculation - polymer dosing or make-up problem", "Material",
          ["polymer", "centrate", "wet", "floc", "dosing"], [
            "Check the polymer make-up: concentration (usually 0.1-0.3 %), age (use within 24 h) and no fish-eyes",
            "Check the polymer dosing pump is running and flow matches the setpoint (calibrate with a drawdown test)",
            "Jar test the feed with fresh polymer to find the right dose",
            "Adjust dose; aim for clear centrate and a firm cake, then record the dose in kg per tonne dry solids"],
          why=W("Why was the polymer not working?", [
              B("Polymer solution old, lumpy or wrong strength", W("Why was the make-up wrong?", [
                  B("Make-up unit not mixing / wetting properly", R(
                      "Polymer make-up unit is not cleaned or checked in PM", "Machine",
                      prevent=["Clean the polymer wetting head and mixer monthly",
                               "Check the make-up concentration daily with a simple dry-weight test"])),
                  B("Manual batch made up wrongly", R(
                      "No written make-up recipe or training for polymer batches", "Man",
                      prevent=["Post the make-up recipe at the unit; train and sign off operators",
                               "Log every batch: time, kg powder, litres water"])),
                  B("Powder caked by damp storage", R(
                      "Polymer powder stored open in a humid area", "Environment",
                      prevent=["Store polymer sealed, off the floor, in a dry room; first-in first-out"])),
              ])),
              B("Dose too low for the feed", R(
                  "Polymer dose is not adjusted to feed solids load (kg/t DS)", "Method",
                  prevent=["Set dose from feed flow x feed TS; repeat jar tests weekly and when feedstock changes"])),
              B("Polymer grade changed by purchasing", R(
                  "Polymer grade changed without a trial", "Material",
                  prevent=["Make polymer grade changes a controlled change with jar test and plant trial"])),
          ], how="Look at the make-up tank, the batch log and the dosing pump flow before blaming the decanter."),
          case="KB-0205"),
        C("feed", "Feed solids or flow variation from upstream", "Material",
          ["feed", "consistency", "surge", "solids", "flow"], [
            "Steady the feed: run the decanter feed pump on flow control and avoid start/stop surges",
            "Check feed TS (grab sample) and adjust feed rate and polymer dose to the solids load",
            "Check the feed tank (CDT/PST) agitator is running so the feed does not stratify",
            "Clear fibres or debris from the feed line / feed tube if flow is erratic"],
          why=W("Why did the feed change?", [
              B("Feed tank not mixed - feed thick then thin", W("Why was the feed tank stratified?", [
                  B("Agitator stopped or undersized", R(
                      "CDT/PST agitator availability is not linked to decanter operation", "Machine",
                      prevent=["Interlock decanter feed with feed-tank agitator running",
                               "Repair or re-rate the feed-tank agitator"])),
                  B("Tank run at very low level", R(
                      "Feed tank level band is not defined, so the pump sucks sludge from the bottom", "Method",
                      prevent=["Set a minimum operating level for the feed tank and a low-level stop for the feed pump"])),
              ])),
              B("Digester / feedstock change not communicated", R(
                  "No handover between digester feeding and SLS when feedstock or digestate TS changes", "Man",
                  prevent=["Add feedstock / TS changes to the shift handover sheet",
                           "Measure feed TS every shift and post on SCADA"])),
              B("Feed flowmeter reading wrong", R(
                  "Decanter feed flowmeter not calibrated", "Measurement",
                  prevent=["Verify the feed flowmeter yearly against a tank drawdown"])),
          ], how="Look at the feed flow and feed TS trends and the feed tank level for the last 24 h."),
          case=None),
        C("sensor", "False vibration / torque alarm (sensor or reading fault)", "Measurement",
          ["alarm", "sensor", "reading", "false", "vibration"], [
            "Confirm with a handheld vibration meter at both main bearing housings",
            "Check the vibration sensor mounting (stud tight, magnet clean) and its cable and connector",
            "Compare the SCADA value with the local panel / monitor reading",
            "Replace or recalibrate the sensor; keep the machine on hourly local readings until fixed"],
          why=W("Why is the reading wrong?", [
              B("Sensor loose or cable damaged", R(
                  "Sensor mounting and cabling are not inspected after machine maintenance", "Method",
                  prevent=["Add sensor torque-check and cable inspection to the decanter reassembly checklist",
                           "Route sensor cables in conduit away from washdown"])),
              B("Sensor out of calibration", R(
                  "Vibration and torque instruments have no calibration schedule", "Measurement",
                  prevent=["Calibrate vibration transmitters yearly and record in the instrument register"])),
              B("Water in the connector after washdown", R(
                  "Connectors not protected from washdown water", "Environment",
                  prevent=["Use IP67 connectors with boots; do not hose directly at sensors"])),
          ], how="Compare SCADA with a handheld meter and inspect the sensor and cable."),
          case=None),
    ],
    "questions": [
        Q("grease", "Have a look at the main bearing grease points and the auto-lubricator. What do you find?", [
            ("Fresh grease, lubricator full and pumping",
             {"lube": 0.25, "solids": 1.1, "scroll": 1.1, "gbox": 1.1, "diff": 1.1, "polymer": 1.1, "feed": 1.1, "sensor": 1.2}),
            ("Dry points or lubricator empty / not pumping",
             {"lube": 4.0, "solids": 0.8, "scroll": 0.8, "gbox": 0.9, "diff": 0.8, "polymer": 0.8, "feed": 0.8, "sensor": 0.8},
             ["rotating_abnormal"]),
            ("Grease dark, burnt or watery",
             {"lube": 2.8, "gbox": 1.2, "solids": 0.9, "scroll": 0.9, "diff": 0.8, "polymer": 0.8, "feed": 0.8, "sensor": 0.8}),
        ], ["grease", "bearing", "lube"],
          how="Do this from outside the guards while running, or with the machine stopped. Check the lubricator "
              "reservoir level and its pump indicator, and look for fresh grease at the bearing purge / relief points.",
          purpose="Lost lubrication is the most common reason decanter main bearings heat up and start to vibrate."),
        Q("btemp", "Point an IR thermometer at both main bearing housings. What temperatures do you get?", [
            ("Both below 75 °C",
             {"lube": 0.3, "gbox": 1.25, "solids": 1.2, "scroll": 1.2, "diff": 1.2, "polymer": 1.2, "feed": 1.2, "sensor": 1.3}),
            ("One end 75-85 °C and creeping up",
             {"lube": 2.6, "gbox": 1.2, "solids": 0.9, "scroll": 1.0, "diff": 0.8, "polymer": 0.8, "feed": 0.8, "sensor": 0.7},
             ["rotating_abnormal"]),
            ("Above 85 °C",
             {"lube": 3.5, "gbox": 1.2, "solids": 0.9, "scroll": 0.9, "diff": 0.7, "polymer": 0.7, "feed": 0.7, "sensor": 0.6},
             ["rotating_critical"]),
        ], ["bearing", "temperature", "vibration"], {"tag": "bearing_temp_c", "option": 0, "above": 78},
          how="Aim at the bearing housing (not the guard) from a safe distance with the machine running; take both "
              "the feed end and the drive end.",
          purpose="A hot main bearing means lubrication trouble and is the signal to stop before the bearing fails."),
        Q("trend", "Think back - how did the vibration or problem start?", [
            ("Suddenly, right after a trip, power cut or stop",
             {"solids": 4.0, "lube": 0.6, "scroll": 0.5, "gbox": 0.8, "diff": 0.8, "polymer": 0.7, "feed": 0.8, "sensor": 0.8}),
            ("Slowly over days or weeks",
             {"scroll": 3.0, "lube": 1.1, "gbox": 1.3, "solids": 0.3, "diff": 0.7, "polymer": 0.8, "feed": 0.8, "sensor": 0.6}),
            ("Within hours, with a bearing getting hot",
             {"lube": 3.0, "gbox": 1.2, "solids": 0.6, "scroll": 0.7, "diff": 0.7, "polymer": 0.7, "feed": 0.7, "sensor": 0.6}),
            ("Comes and goes as the feed changes",
             {"feed": 3.0, "polymer": 1.4, "diff": 1.3, "solids": 0.6, "lube": 0.6, "scroll": 0.8, "gbox": 0.8, "sensor": 0.8}),
            ("Alarm only - machine sounds and feels normal",
             {"sensor": 4.0, "lube": 0.5, "solids": 0.5, "scroll": 0.6, "gbox": 0.6, "diff": 0.9, "polymer": 0.9, "feed": 0.9}),
        ], ["vibration", "alarm", "stop"],
          how="Check the SCADA vibration trend and the decanter alarm / stop log, and ask the previous shift.",
          purpose="How fast it came on separates a sudden imbalance from slow wear or a lubrication problem."),
        Q("cake", "How do the cake and the centrate (liquid outlet) look right now?", [
            ("Firm dry cake, clear centrate",
             {"polymer": 0.3, "feed": 0.6, "diff": 0.5, "scroll": 0.6, "solids": 1.1, "lube": 1.3, "gbox": 1.1, "sensor": 1.4}),
            ("Wet sloppy cake, centrate fairly clear",
             {"diff": 2.4, "scroll": 2.2, "polymer": 0.9, "feed": 1.1, "solids": 0.9, "lube": 0.8, "gbox": 1.0, "sensor": 0.7}),
            ("Dirty brown centrate, wet cake",
             {"polymer": 3.2, "feed": 1.8, "diff": 1.2, "scroll": 1.0, "solids": 0.9, "lube": 0.7, "gbox": 0.8, "sensor": 0.6}),
            ("Cake comes out in surges or stops",
             {"feed": 1.8, "diff": 1.6, "gbox": 1.6, "solids": 1.3, "scroll": 1.2, "polymer": 1.0, "lube": 0.7, "sensor": 0.6}),
        ], ["cake", "centrate", "wet", "polymer"],
          how="Look at the cake falling from the solids discharge chute and take a sample of centrate in a clear "
              "bottle from the sample point. Never reach into the chute.",
          purpose="Cake and centrate quality show whether the separation itself (polymer, settings, scroll) is off."),
        Q("torque", "On the decanter HMI, how do the scroll torque and differential speed look?", [
            ("Steady at the usual values",
             {"diff": 0.4, "gbox": 0.4, "scroll": 0.7, "feed": 0.7, "polymer": 1.1, "lube": 1.3, "solids": 1.1, "sensor": 1.3}),
            ("Torque creeping up over days at the same feed",
             {"scroll": 4.5, "diff": 1.0, "gbox": 0.9, "feed": 0.8, "polymer": 0.6, "lube": 0.6, "solids": 0.6, "sensor": 0.5}),
            ("Torque hunting or tripping on high torque",
             {"gbox": 3.2, "diff": 2.2, "feed": 1.6, "scroll": 1.1, "solids": 0.9, "polymer": 0.7, "lube": 0.6, "sensor": 0.6}),
            ("Torque unusually low",
             {"polymer": 2.2, "diff": 1.8, "feed": 1.5, "scroll": 0.8, "gbox": 0.8, "lube": 0.8, "solids": 0.8, "sensor": 1.0}),
        ], ["torque", "differential", "trip"], {"tag": "motor_current_a", "option": 0, "above": 22},
          how="Read torque (% or kNm) and differential speed (rpm) on the decanter panel; compare with the usual values "
              "in the setpoint log or the 7-day SCADA trend.",
          purpose="Torque tells you how much cake is in the bowl and whether the scroll and back-drive are coping."),
        Q("diffset", "Has anyone changed the differential speed, pond / weir setting or feed rate recently?", [
            ("Yes, changed in the last few days",
             {"diff": 5.0, "feed": 0.9, "polymer": 0.8, "solids": 0.7, "lube": 0.6, "scroll": 0.7, "gbox": 0.7, "sensor": 0.6}),
            ("No, same settings as usual",
             {"diff": 0.25, "feed": 1.0, "polymer": 1.0, "solids": 1.1, "lube": 1.1, "scroll": 1.1, "gbox": 1.1, "sensor": 1.1}),
        ], ["differential", "setting"],
          how="Check the setpoint log and the HMI change history, and ask the operators on the last two shifts.",
          purpose="A recent setting change is the first suspect when cake, torque or plugging change suddenly."),
        Q("poly", "Check the polymer make-up tank and dosing pump. What do you see?", [
            ("Fresh, smooth solution; pump running steady",
             {"polymer": 0.25, "feed": 1.1, "diff": 1.1, "scroll": 1.1, "solids": 1.0, "lube": 1.0, "gbox": 1.0, "sensor": 1.0}),
            ("Lumps / fish-eyes, old batch or wrong strength",
             {"polymer": 4.0, "feed": 0.9, "diff": 0.9, "scroll": 0.9}),
            ("Dosing pump stopped or flow erratic",
             {"polymer": 3.5, "feed": 1.0, "diff": 0.9, "scroll": 0.9}),
        ], ["polymer", "dosing", "centrate", "floc"],
          how="Look into the make-up tank: good solution is smooth and stringy with no gel lumps. Check the batch time "
              "on the log (use within 24 h) and watch the dosing pump flow or rotameter.",
          purpose="Bad polymer gives wet cake and dirty centrate even when the decanter is mechanically fine."),
        Q("feedq", "How does the feed to the decanter compare with normal?", [
            ("Same flow and thickness as usual",
             {"feed": 0.25, "polymer": 1.1, "diff": 1.1, "scroll": 1.1, "solids": 1.1, "lube": 1.1, "gbox": 1.1, "sensor": 1.1}),
            ("Much thicker or thinner, or flow surging",
             {"feed": 3.6, "polymer": 1.2, "diff": 1.1, "solids": 1.0, "scroll": 0.9, "lube": 0.8, "gbox": 0.9, "sensor": 0.8}),
            ("Lots of sand, grit or long fibres",
             {"scroll": 2.4, "feed": 2.0, "gbox": 1.2, "solids": 1.1, "polymer": 0.9, "diff": 0.9, "lube": 0.9, "sensor": 0.8}),
        ], ["feed", "consistency", "solids", "flow"],
          how="Look at the feed flow trend on SCADA and take a feed grab sample from the sample cock; let it settle "
              "in a bucket for a minute to see grit and fibres.",
          purpose="Feed swings upset polymer dose, torque and balance - they are a common hidden cause."),
        Q("gear", "Listen at the gearbox / back-drive end and check its oil. What do you notice?", [
            ("Quiet, oil clean and at level",
             {"gbox": 0.25, "lube": 1.1, "solids": 1.1, "scroll": 1.1, "diff": 1.1, "polymer": 1.1, "feed": 1.1, "sensor": 1.1}),
            ("Whine, knocking, or metal bits in the oil",
             {"gbox": 5.5, "lube": 0.8, "scroll": 0.7, "solids": 0.5, "diff": 0.6, "polymer": 0.5, "feed": 0.5, "sensor": 0.3},
             ["rotating_abnormal"]),
            ("Oil leaking or level low",
             {"gbox": 3.0, "lube": 1.1, "scroll": 0.9, "solids": 0.8, "diff": 0.8, "polymer": 0.8, "feed": 0.8, "sensor": 0.8}),
        ], ["gearbox", "back-drive", "noise", "torque"],
          how="Listen from outside the guard while running. Check the gearbox oil sight glass only with the machine "
              "stopped and fully run down (some gearboxes rotate with the bowl).",
          purpose="Gearbox noise or metal in the oil points to the back-drive rather than the bowl."),
        Q("local", "Take a handheld vibration reading on both main bearing housings. How does it compare with SCADA?", [
            ("Both high, same as SCADA",
             {"sensor": 0.2, "lube": 1.2, "solids": 1.2, "scroll": 1.2, "gbox": 1.2, "diff": 1.0, "polymer": 1.0, "feed": 1.0},
             ["rotating_abnormal"]),
            ("Handheld normal, SCADA says high",
             {"sensor": 5.0, "lube": 0.5, "solids": 0.4, "scroll": 0.5, "gbox": 0.5, "diff": 0.8, "polymer": 0.8, "feed": 0.8}),
            ("Very high, machine shaking on its frame",
             {"solids": 2.5, "scroll": 1.6, "lube": 1.2, "gbox": 1.1, "sensor": 0.1, "diff": 0.8, "polymer": 0.7, "feed": 0.9},
             ["rotating_critical"]),
        ], ["vibration", "alarm", "sensor", "reading"],
          how="Hold the meter probe on the bearing housing (not the guard or frame) from outside the guard. If you "
              "have no meter, do not touch the machine - just report how it looks from a safe distance.",
          purpose="Confirms the vibration is real before we stop production, and shows how serious it is."),
        Q("flushed", "Was the last stop a proper shutdown with a low-speed flush?", [
            ("Yes, flushed before stopping",
             {"solids": 0.25, "lube": 1.1, "scroll": 1.1, "gbox": 1.1, "diff": 1.1, "polymer": 1.1, "feed": 1.1, "sensor": 1.1}),
            ("No - it tripped or was stopped without flushing",
             {"solids": 4.0, "lube": 0.8, "scroll": 0.8, "gbox": 0.9, "diff": 0.9, "polymer": 0.8, "feed": 0.9, "sensor": 0.8}),
            ("Not sure", {}),
        ], ["cleaning", "flush", "stop", "vibration"],
          how="Check the decanter stop log (normal stop vs trip / E-stop) and the shift logbook, or ask the operator.",
          purpose="Solids left in a stopped bowl set unevenly and throw it badly out of balance at the next start."),
    ],
}

# ----------------------------------------------------------------------------------------------------------------------
# WAM screw-press / screen separator
# ----------------------------------------------------------------------------------------------------------------------
TREES["WAM"] = {
    "causes": [
        C("wash", "Fibrous build-up on the screen from low wash water", "Method",
          ["mesh", "choke", "wash", "flow"], [
            "Stop the separator under LOTO and clean the screen mesh (pressure-wash from outside)",
            "Restore wash water: open the supply valve fully, clean the line strainer, confirm header pressure ≥ 2 bar",
            "Set the wash cycle timer to the OEM interval and check the solenoid valve opens",
            "Restart and check the filtrate flows freely along the full screen length"],
          why=W("Why was the wash water low?", [
              B("Wash water supply pressure low", W("Why was the supply pressure low?", [
                  B("Service water shared with other users at the same time", R(
                      "Wash water comes from a shared header with no priority or dedicated pump", "Machine",
                      prevent=["Give the separator wash a dedicated booster pump or a pressure-sustaining valve",
                               "Stagger large water users (hose-down, polymer make-up) away from wash cycles"])),
                  B("Line strainer blocked", R(
                      "Wash water line strainer is not on the cleaning schedule", "Method",
                      prevent=["Clean the wash line strainer weekly; fit a pressure gauge after it"])),
              ])),
              B("Wash cycle shortened or switched off", W("Why was the wash cycle changed?", [
                  B("Reduced to save water", R(
                      "Wash timer settings are not controlled", "Method",
                      prevent=["Fix wash on/off times in the setpoint log; change only via supervisor"])),
                  B("Solenoid valve failed closed", R(
                      "Wash solenoid valve is not function-tested in PM", "Machine",
                      prevent=["Function-test wash solenoid valves monthly; keep a spare coil"])),
              ])),
          ], how="Read the wash water gauge during a wash cycle and check the wash timer settings."),
          case="KB-0611"),
        C("nozzle", "Wash spray nozzles choked", "Material", ["mesh", "nozzle", "spray", "choke"], [
            "Isolate wash water, remove the spray bar and clean or replace choked nozzles",
            "Flush the spray bar before refitting",
            "Check the spray pattern covers the full screen width",
            "Add or clean a fine strainer ahead of the spray bar"],
          why=W("Why did the nozzles choke?", [
              B("Recycled filtrate / dirty water used for washing", R(
                  "Wash water is recycled liquid fraction with solids, without fine filtration", "Material",
                  prevent=["Use clean service water for spray wash, or fit a self-cleaning fine filter",
                               "Clean nozzles weekly when recycled water must be used"])),
              B("Hard water scaling", R(
                  "Untreated hard water scales the small nozzle orifices", "Material",
                  prevent=["Use softened water or descale nozzles monthly"])),
              B("Nozzles not inspected", R(
                  "Spray nozzle check is not on the shift round", "Man",
                  prevent=["Add 'watch the spray pattern' to the SLS shift round"])),
          ], how="Remove one nozzle and see what is blocking it: fibres and sludge, or white scale."),
          case=None),
        C("flight", "Worn screw flights / brush - screen not scraped clean", "Machine",
          ["mesh", "screw", "brush", "wear", "vibration"], [
            "Stop the separator under LOTO and open the inspection hatch",
            "Measure the gap between the screw flight / brush and the screen",
            "Replace worn brush strips or screw flight segments; check the screen for scoring",
            "Clean the screen and restart; check filtrate and cake"],
          why=W("Why did the flights / brush wear out unnoticed?", [
              B("Abrasive grit in the digestate", R(
                  "Grit / sand in digestate is not controlled upstream", "Material",
                  prevent=["Improve grit removal before SLS; track sand content of feedstock"])),
              B("No wear inspection", W("Why is wear not checked?", [
                  B("Not in the PM plan", R(
                      "Screw and brush wear measurement is not in the PM plan", "Method",
                      prevent=["Measure screw / brush to screen gap every 500 h and record it",
                               "Keep a spare brush set and screw segment in stores"])),
                  B("Crew unsure what limit to use", R(
                      "Wear limits from the OEM are not given to the maintenance crew", "Man",
                      prevent=["Put OEM wear limits on the PM job card and train fitters"])),
              ])),
          ], how="Check the PM history for the last screw / brush inspection and measure the gap now."),
          case=None),
        C("overload", "Feed rate above the separator's capacity", "Method",
          ["flow", "choke", "overflow", "material flow", "overload"], [
            "Reduce the feed pump speed to the rated flow for this separator",
            "Spread the feed evenly across the separators in service",
            "Clear any overflow and clean the inlet box",
            "Watch for 30 minutes that the inlet level stays stable"],
          why=W("Why was the separator overfed?", [
              B("One separator out of service; others took its share", R(
                  "No load-sharing rule when a separator is down", "Method",
                  prevent=["Define maximum feed per separator and reduce total SLS feed when one is down"])),
              B("Feed pump set by hand without a flow reading", W("Why was the feed not controlled?", [
                  B("No flowmeter on the feed", R(
                      "Separator feed has no flow measurement", "Measurement",
                      prevent=["Fit a flowmeter on each separator feed or a calibrated pump-speed curve"])),
                  B("Operator chasing digester level", R(
                      "Digestate withdrawal target pushes operators to overfeed SLS", "Man",
                      prevent=["Plan digestate withdrawal against SLS capacity; train operators on limits"])),
              ])),
          ], how="Compare the feed pump speed / flow with the separator rating on the nameplate."),
          case="KB-0212"),
        C("fibre", "Long fibres, plastics or debris in the feed", "Material",
          ["choke", "material flow", "fibre", "plastic", "flow"], [
            "Stop under LOTO and remove wrapped fibres, plastics or ropes from the screw and inlet",
            "Check the screen for damage from foreign objects",
            "Check the upstream shredder / macerator cut length and the reception sorting",
            "Restart at reduced feed and watch motor current"],
          why=W("Why did the debris reach the separator?", [
              B("Shredder / macerator cut length too long", R(
                  "Upstream shredder blades blunt or worn", "Machine",
                  prevent=["Check shredder blades weekly; sharpen or rotate per OEM"])),
              B("Contaminated feedstock received", W("Why was contaminated feedstock accepted?", [
                  B("No visual check at reception", R(
                      "Feedstock reception has no contamination check", "Method",
                      prevent=["Add a visual plastics / rope check at reception and reject or sort"])),
                  B("Supplier not told the specification", R(
                      "Feedstock specification not agreed with suppliers", "Material",
                      prevent=["Share a written feedstock specification with suppliers; feedback on rejects"])),
              ])),
          ], how="Look at what is wrapped on the screw: straw, plastic film, rope or rags tell you the source."),
          case="KB-0213"),
        C("press", "Outlet counter-pressure set wrong", "Man",
          ["cake", "wet", "plug", "counter-pressure", "setting"], [
            "Return the outlet flap weights / pneumatic counter-pressure to the commissioning setting",
            "If the outlet is plugged, stop under LOTO and clear the press zone",
            "Adjust in small steps and check cake dryness after each change",
            "Record the setting in the setpoint log"],
          why=W("Why was the counter-pressure wrong?", [
              B("Adjusted by an operator to fix wet cake", R(
                  "Operators not trained on how counter-pressure affects dryness and plugging", "Man",
                  prevent=["Train operators: more pressure = drier cake but risk of plugging and overload",
                           "Mark the normal flap weight positions / air pressure on the machine"])),
              B("Air regulator or flap weights drifted", R(
                  "Counter-pressure regulator and gauge not checked in PM", "Measurement",
                  prevent=["Check counter-pressure regulator and gauge monthly; replace faulty gauge"])),
          ], how="Compare the flap weight position or air pressure with the setting marked at commissioning."),
          case=None),
        C("torn", "Torn or worn-through screen", "Machine", ["mesh", "filtrate", "screen", "torn"], [
            "Stop the separator under LOTO and remove the screen basket",
            "Replace the torn screen; check the screw for bent flights that cut it",
            "Clean the filtrate tank / CDT of fibres that passed through",
            "Restart and check filtrate clarity"],
          why=W("Why did the screen tear?", [
              B("Foreign object (stone, metal) went through", R(
                  "No stone trap / magnet ahead of the separator", "Machine",
                  prevent=["Fit a stone trap or magnet upstream and clean it weekly"])),
              B("Screen past its service life", R(
                  "Screen replaced only on failure, not by hours", "Method",
                  prevent=["Replace screens at 2,000-3,000 h or per OEM; inspect weekly"])),
              B("High-pressure hose used on the screen", R(
                  "Cleaning with a high-pressure lance damages fine mesh", "Man",
                  prevent=["Specify a low-pressure wash for screens in the cleaning SOP; train the crew"])),
          ], how="Look at the tear: a clean cut or dent suggests a foreign object; thin worn mesh suggests age."),
          case="KB-0215"),
        C("drive", "Gearmotor or electrical fault", "Machine", ["trip", "current", "motor", "gearbox", "noise"], [
            "Isolate the gearmotor at the MCC and apply LOTO",
            "Check gearbox oil level and condition; listen for bearing noise on a hand turn",
            "Have the electrician check phase currents, insulation and the overload setting",
            "Restart and record the running current"],
          why=W("Why did the gearmotor fail?", [
              B("Gearbox oil low or old", R(
                  "Gearmotor oil level and changes not in PM", "Method",
                  prevent=["Add gearmotor oil level to weekly rounds; change oil per OEM hours"])),
              B("Water in motor terminal box", R(
                  "Washdown water reaches the motor; glands not sealed", "Environment",
                  prevent=["Fit proper cable glands; shield the motor from wash spray"])),
              B("Repeated overloads from plugging", R(
                  "No torque / current alarm before the overload trip", "Measurement",
                  prevent=["Add a high-current warning on SCADA below the trip setting"])),
          ], how="Look at the trip history and the gearbox oil before replacing parts."),
          case=None),
    ],
    "questions": [
        Q("spray", "Watch the wash spray during a wash cycle. How does it look?", [
            ("Full, even spray across the screen",
             {"wash": 0.2, "nozzle": 0.2, "flight": 1.6, "overload": 1.3, "fibre": 1.3, "press": 1.3, "torn": 1.2, "drive": 1.2}),
            ("Weak spray along the whole bar",
             {"wash": 3.5, "nozzle": 1.0, "flight": 0.8, "overload": 0.9, "fibre": 0.9, "press": 0.8, "torn": 0.9, "drive": 0.9}),
            ("Some nozzles dead or dribbling",
             {"nozzle": 5.0, "wash": 0.7, "flight": 0.7, "overload": 0.7, "fibre": 0.7, "press": 0.6, "torn": 0.7, "drive": 0.6}),
        ], ["mesh", "wash", "spray", "nozzle", "choke"],
          how="Look through the inspection window or from outside the guard while the wash runs. Don't open covers "
              "while the screw is turning.",
          purpose="The spray keeps the mesh open; a weak or patchy spray lets fibres mat on the screen."),
        Q("wpress", "What does the wash water pressure gauge read during washing?", [
            ("Normal, 2 bar or more",
             {"wash": 0.25, "nozzle": 1.5, "flight": 1.1, "overload": 1.0, "fibre": 1.0, "press": 1.0, "torn": 1.0, "drive": 1.0}),
            ("Low or dropping",
             {"wash": 3.6, "nozzle": 0.6, "flight": 0.9, "overload": 0.9, "fibre": 0.9, "press": 0.9, "torn": 0.9, "drive": 0.9}),
        ], ["wash", "mesh", "flow"],
          how="Read the gauge on the wash water line next to the separator while the wash valve is open.",
          purpose="Low header pressure means the whole wash is weak - a supply problem, not the nozzles."),
        Q("mesh", "With the separator stopped under LOTO, open the inspection hatch. How does the screen look?", [
            ("Clean and open",
             {"wash": 0.3, "nozzle": 0.4, "flight": 0.5, "overload": 1.2, "fibre": 1.0, "press": 1.4, "torn": 0.7, "drive": 1.5}),
            ("Matted fibres or blinded patches",
             {"wash": 2.4, "nozzle": 2.4, "flight": 2.0, "fibre": 1.4, "overload": 1.2, "press": 0.8, "torn": 0.5, "drive": 0.7}),
            ("Torn, holed or worn through",
             {"torn": 5.0, "fibre": 1.3, "flight": 1.1, "wash": 0.5, "nozzle": 0.5, "overload": 0.6, "press": 0.6, "drive": 0.6}),
        ], ["mesh", "screen", "choke", "filter"],
          how="Stop the separator and the feed pump, apply LOTO (SOP-ROT-01), wait for the screw to stop, then open "
              "the inspection hatch and look at the screen with a torch.",
          purpose="Blinded mesh, a clean mesh and a torn mesh each point to a different cause."),
        Q("brush", "While it's open, look at the screw flight edge / brush where it meets the screen.", [
            ("Brush intact, touching the screen",
             {"flight": 0.2, "wash": 1.15, "nozzle": 1.15, "overload": 1.2, "fibre": 1.0, "press": 1.2, "torn": 1.0, "drive": 1.2}),
            ("Brush worn, gap to the screen",
             {"flight": 4.0, "wash": 0.8, "nozzle": 0.8, "overload": 0.8, "fibre": 0.8, "press": 0.8, "torn": 1.0, "drive": 0.8}),
            ("Flights bent, broken or wrapped",
             {"fibre": 2.4, "flight": 2.0, "torn": 1.5, "wash": 0.7, "nozzle": 0.7, "overload": 0.9, "press": 0.8, "drive": 1.1}),
        ], ["screw", "brush", "wear", "mesh"],
          how="Only with LOTO applied: look along the screw through the hatch; check whether the brush or flight edge "
              "still touches the screen and measure the gap with a feeler or rule if you can.",
          purpose="A worn brush stops scraping the screen, so it blinds even with good wash water."),
        Q("inlet", "How is the feed coming in compared with normal?", [
            ("Normal flow, inlet not backing up",
             {"overload": 0.25, "wash": 1.1, "nozzle": 1.1, "flight": 1.1, "fibre": 1.0, "press": 1.1, "torn": 1.1, "drive": 1.1}),
            ("Feed pump turned up or feed much thicker",
             {"overload": 5.5, "fibre": 0.7, "wash": 0.55, "nozzle": 0.55, "flight": 0.55, "press": 0.7, "torn": 0.55, "drive": 0.6}),
            ("Inlet backing up or overflowing",
             {"overload": 2.0, "wash": 1.6, "nozzle": 1.4, "flight": 1.4, "fibre": 1.6, "press": 1.2, "torn": 0.5, "drive": 1.0}),
        ], ["flow", "overflow", "choke", "material flow"],
          how="Check the feed pump speed / flow on SCADA and look at the inlet box level from the walkway.",
          purpose="Feeding more than the separator can take chokes it even when everything else is fine."),
        Q("debris", "What's in the feed and cake - anything unusual?", [
            ("Just the usual digestate",
             {"fibre": 0.25, "wash": 1.1, "nozzle": 1.1, "flight": 1.1, "overload": 1.1, "press": 1.1, "torn": 1.0, "drive": 1.1}),
            ("Long straw, plastic film, rope or rags",
             {"fibre": 5.5, "wash": 0.6, "nozzle": 0.55, "flight": 0.7, "overload": 0.6, "press": 0.55, "torn": 0.9, "drive": 0.7}),
            ("Lots of sand, grit or stones",
             {"flight": 2.2, "torn": 2.2, "fibre": 1.2, "wash": 0.8, "nozzle": 0.8, "overload": 0.9, "press": 0.9, "drive": 1.0}),
        ], ["material flow", "fibre", "choke"],
          how="Look at the cake pile and, with LOTO, at the inlet and the screw. Rub a sample of liquid between "
              "gloved fingers to feel for grit.",
          purpose="Debris wraps the screw and grit wears the brush and screen - both start upstream."),
        Q("cake", "How is the solid cake coming out of the outlet?", [
            ("Steady, normal dryness",
             {"press": 0.3, "overload": 0.7, "wash": 1.1, "nozzle": 1.1, "flight": 1.0, "fibre": 1.0, "torn": 0.8, "drive": 1.2}),
            ("Wet and sloppy",
             {"press": 2.6, "overload": 1.8, "torn": 1.5, "wash": 1.1, "nozzle": 1.1, "flight": 1.2, "fibre": 0.8, "drive": 0.8}),
            ("Little or no cake - outlet plugged",
             {"press": 2.6, "fibre": 1.6, "drive": 1.5, "overload": 1.2, "wash": 0.9, "nozzle": 0.9, "flight": 0.8, "torn": 0.5}),
        ], ["cake", "wet", "plug"],
          how="Watch the cake leaving the outlet flap from a safe position; squeeze a handful (gloved) - water "
              "running out means it's wet.",
          purpose="Cake dryness shows if the press zone is set right or if liquid is bypassing the screen."),
        Q("cpset", "Has anyone changed the outlet flap weights or counter-pressure recently?", [
            ("Yes, changed recently",
             {"press": 5.0, "overload": 0.8, "wash": 0.6, "nozzle": 0.6, "flight": 0.6, "fibre": 0.6, "torn": 0.6, "drive": 0.6}),
            ("No, same as usual",
             {"press": 0.25, "wash": 1.1, "nozzle": 1.1, "flight": 1.1, "overload": 1.1, "fibre": 1.1, "torn": 1.1, "drive": 1.1}),
        ], ["counter-pressure", "setting", "cake"],
          how="Compare the flap weight position or air pressure with the commissioning mark, check the setpoint log "
              "and ask the last two shifts.",
          purpose="A changed counter-pressure explains wet cake or a plugged outlet without any breakdown."),
        Q("filtrate", "Look at the liquid (filtrate) leaving the separator. What's it like?", [
            ("Usual - some fines, no fibres",
             {"torn": 0.25, "wash": 1.1, "nozzle": 1.1, "flight": 1.0, "overload": 1.0, "fibre": 1.0, "press": 1.1, "drive": 1.1}),
            ("Lots of fibres or coarse solids in it",
             {"torn": 4.5, "overload": 1.3, "flight": 1.0, "wash": 0.7, "nozzle": 0.7, "fibre": 1.0, "press": 1.0, "drive": 0.8}),
            ("Very little - liquid stays with the screw",
             {"wash": 1.9, "nozzle": 1.9, "flight": 1.6, "overload": 1.5, "fibre": 1.2, "torn": 0.3, "press": 1.0, "drive": 0.9}),
        ], ["filtrate", "mesh", "screen", "flow"],
          how="Look at the filtrate outlet or channel and fill a clear bottle from the sample point.",
          purpose="Fibres in the filtrate mean the screen is torn; very little filtrate means the screen is blinded."),
        Q("motor", "How do the gearmotor current and sound look?", [
            ("Normal current, runs quiet",
             {"drive": 0.25, "overload": 0.8, "fibre": 0.8, "press": 0.9, "wash": 1.1, "nozzle": 1.1, "flight": 1.1, "torn": 1.1}),
            ("High current or trips on overload",
             {"drive": 2.2, "overload": 2.0, "fibre": 1.8, "press": 1.6, "wash": 0.9, "nozzle": 0.8, "flight": 0.9, "torn": 0.6}),
            ("Gearbox noise, heat or oil leak",
             {"drive": 5.0, "fibre": 0.8, "overload": 0.6, "press": 0.6, "wash": 0.5, "nozzle": 0.5, "flight": 0.8, "torn": 0.5},
             ["rotating_abnormal"]),
        ], ["trip", "current", "motor", "gearbox", "noise"], {"tag": "motor_current_a", "option": 0, "above": 22},
          how="Read the motor current on SCADA or the MCC ammeter and compare with the nameplate; listen at the "
              "gearbox from outside the guard and look for oil underneath.",
          purpose="Separates a drive / electrical fault from a choking problem that only loads the motor."),
    ],
}

# ----------------------------------------------------------------------------------------------------------------------
MAINTENANCE = {
    "Decanter": {
        "summary": "Decanter centrifuges dewater digestate at high bowl speed (≈2,500-3,500 rpm); a scroll turning "
                   "slightly slower (differential speed via gearbox / back-drive) conveys the cake. Main bearing "
                   "lubrication, bowl balance, scroll wear, gearbox health and polymer conditioning decide both "
                   "reliability and cake dryness.",
        "pm": [
            ("Every shift", "Check vibration, main bearing temperatures, torque and differential, lubricator level, "
                            "cake dryness and centrate clarity; check polymer batch age"),
            ("Every stop", "Run the low-speed flush sequence before stopping; flush after any trip before restart"),
            ("Weekly", "Grease main bearings per OEM table if manual; check gearbox oil level and leaks; "
                       "trend torque at constant feed"),
            ("Monthly", "Confirm grease reaches each bearing point; clean polymer make-up unit; check belts and guards"),
            ("3-monthly", "Gearbox oil sample (wear metals, water); vibration spectrum on both main bearings"),
            ("4,000-8,000 h / per OEM", "Inspect scroll flights, tiles, feed zone and discharge ports; re-tile and "
                                        "dynamically balance as needed; gearbox oil change"),
            ("Per OEM life / condition", "Main bearing replacement from L10 life, grease condition and vibration trend"),
        ],
        "failure_modes": ["Main bearing failure from lubrication starvation or wrong grease",
                          "Bowl imbalance from solids left after an unflushed stop",
                          "Scroll flight / tile wear from grit - wet cake, rising torque, imbalance",
                          "Gearbox / back-drive wear - torque hunting, metal in oil",
                          "Poor flocculation - wet cake and dirty centrate",
                          "Plugging / high-torque trips from wrong differential or feed surges",
                          "Feed zone and discharge port erosion"],
        "operating_limits": [("Vibration (ISO 10816-3)", "< 4.5 mm/s normal; alarm ≈ 7 mm/s; trip per OEM (≈ 11 mm/s)"),
                             ("Main bearing temperature", "< 75 °C normal; alarm 85 °C; stop above 90 °C"),
                             ("Scroll torque", "50-70 % of maximum in steady operation"),
                             ("Differential speed", "≈ 2-15 rpm for digestate (per OEM recipe)"),
                             ("Polymer solution", "0.1-0.3 % active, used within 24 h")],
    },
    "WAM": {
        "summary": "Screw-press / screen separators (WAM / Sepcom type) push digestate along a cylindrical screen with "
                   "a slow screw; liquid drains through the mesh and a counter-pressure outlet presses the solids to "
                   "≈ 25-35 % DM. Screen cleanliness (wash spray, brush), screw / screen wear and feed rate control "
                   "decide throughput and cake dryness.",
        "pm": [
            ("Every shift", "Check wash spray pattern and pressure, inlet level, cake dryness, filtrate clarity and "
                            "motor current"),
            ("Weekly", "Clean wash line strainer and nozzles; inspect screen through hatch (LOTO); clean inlet box"),
            ("Monthly", "Function-test wash solenoid; check counter-pressure setting / regulator; gearmotor oil level"),
            ("Every 500 h", "Measure screw / brush to screen gap; replace brush strips if worn"),
            ("2,000-3,000 h", "Replace screen basket (or per OEM / condition)"),
            ("Yearly", "Gearmotor oil change, bearing check, motor insulation test"),
        ],
        "failure_modes": ["Screen blinding from low wash water or choked nozzles",
                          "Worn screw / brush no longer scraping the screen",
                          "Choking from overfeeding or long fibres / plastics",
                          "Wet cake or plugged outlet from wrong counter-pressure",
                          "Torn screen from foreign objects or age",
                          "Gearmotor overload or oil loss"],
        "operating_limits": [("Wash water pressure", "≥ 2 bar at the spray bar"),
                             ("Feed flow", "≤ nameplate rating per separator (reduce for thick feed)"),
                             ("Cake dry matter", "≈ 25-35 % DM"),
                             ("Motor current", "≤ nameplate FLA; ≈ 18 A typical here"),
                             ("Vibration", "< 4.5 mm/s")],
    },
}

# ----------------------------------------------------------------------------------------------------------------------
CONDITIONS = [
    {"id": "SLS", "title": "Solid-Liquid Separation - normal operating conditions", "areas": ["SLS"],
     "params": [
         ("Feed total solids (TS)", "3-8 % (digestate from PST)",
          "Polymer dose, feed rate and torque are all set for a given feed TS",
          "Re-check TS by grab sample; adjust feed rate and polymer dose; check the PST agitator is running"),
         ("Decanter feed flow", "Steady at recipe value, no start/stop surges",
          "Surges upset flocculation and load the scroll unevenly",
          "Put the feed pump on flow control; check the feed line for blockages"),
         ("Decanter cake dryness", "≈ 25-35 % DS",
          "Wet cake overloads bagging / briquetting and raises disposal cost",
          "Check polymer, then differential speed / pond setting, then scroll wear"),
         ("Centrate quality (TSS)", "< 0.5-1 % TSS; visibly clear to light brown",
          "Solids in the centrate return to the CDT and cause build-up and foaming",
          "Check polymer make-up and dose first; then reduce feed or adjust pond depth"),
         ("Solids capture", "≥ 90 % for decanters; 85-92 % for screw presses",
          "Low capture means solids recycle around the plant",
          "Jar test polymer; check screens for tears on screw presses"),
         ("Polymer dose", "≈ 6-10 kg/t dry solids (decanter)",
          "Too little gives dirty centrate; too much wastes money and makes slimy cake",
          "Recalculate from feed flow x TS; jar test when feedstock changes"),
         ("Polymer solution", "0.1-0.3 % active, smooth with no fish-eyes, used within 24 h",
          "Old or lumpy polymer loses flocculating power",
          "Make a fresh batch per the posted recipe; clean the wetting head"),
         ("Decanter bowl speed", "≈ 2,500-3,500 rpm (per OEM recipe)",
          "Sets G-force and separation sharpness",
          "Do not change without OEM advice; check VFD if speed drifts"),
         ("Differential speed", "≈ 2-15 rpm per recipe",
          "Lower = drier cake but higher torque; higher = wetter cake",
          "Return to logged recipe; change in 0.5-1 rpm steps only"),
         ("Scroll torque", "50-70 % of maximum, steady",
          "Creeping torque at constant feed signals scroll wear; spikes signal plugging",
          "Reduce feed; check differential; plan scroll inspection if creeping"),
         ("Decanter vibration", "< 4.5 mm/s (alarm ≈ 7 mm/s)",
          "Rising vibration means imbalance or bearing damage",
          "Follow the decanter troubleshooting tree; stop at Critical and let the bowl run down fully"),
         ("Main bearing temperature", "< 75 °C (alarm 85 °C)",
          "Hot bearings mean lubrication starvation",
          "Check lubricator and regrease per OEM; stop above 85-90 °C"),
         ("WAM wash water pressure", "≥ 2 bar during wash cycle",
          "Low wash lets fibres blind the screen",
          "Clean the line strainer; check solenoid valve and supply pump"),
         ("WAM cake dry matter", "≈ 25-35 % DM",
          "Shows correct counter-pressure and screen condition",
          "Check counter-pressure setting, feed rate and screen / brush"),
     ],
     "notes": ["Decanters can coast for 10-20 minutes after stop - never open covers until the bowl has stopped and "
               "LOTO is applied (SOP-ROT-01).",
               "Always flush decanters at low speed before stopping and after any trip.",
               "Record every setpoint change (feed, polymer, differential, pond, counter-pressure) in the setpoint log.",
               "Polymer powder is extremely slippery when wet - clean spills immediately."]},
    {"id": "CDT", "title": "CDT & PST storage - normal operating conditions", "areas": ["CDT", "PST"],
     "params": [
         ("PST level", "Between 30 % and 85 % of working volume",
          "Low level starves the decanter feed pumps; high level risks overflow",
          "Balance digestate withdrawal against SLS throughput; check level transmitter against the dip"),
         ("CDT level", "Between 30 % and 85 %",
          "The CDT buffers centrate / liquid fraction; overflow causes spills and odour",
          "Increase liquid-fraction disposal / recirculation; reduce SLS feed if near high level"),
         ("Agitator running", "Running on schedule (continuous or timed cycles)",
          "Without mixing, solids settle and feed TS swings at the decanters",
          "Restart the agitator; check for trips, fibres on the impeller and gearbox condition"),
         ("Feed TS from PST", "3-8 %, stable within ± 1 % per shift",
          "A stratified tank sends thick then thin feed to the SLS",
          "Check agitation and minimum level; sample at the feed pump"),
         ("Liquid temperature", "≈ 30-45 °C (cooling from digester temperature)",
          "Hot digestate increases odour and foaming; temperature also affects polymer",
          "Check digester outlet temperature; allow residence time"),
         ("pH", "≈ 7.5-8.5",
          "Normal for digestate; a change warns of process upset upstream",
          "Inform the digester team; check feedstock changes"),
         ("H2S at tank vents / hatches", "< 10 ppm in the working area",
          "Digestate tanks release H2S - toxic; confined space risk",
          "Wear a personal gas monitor; ventilate; never enter or lean into hatches without a permit"),
         ("Foam", "No foam above the tank roof / hatches",
          "Foaming carries solids out of vents and upsets level readings",
          "Reduce agitation intensity; check for polymer overdose in centrate; dose antifoam if approved"),
         ("Mud / slurry pump discharge pressure", "Steady at the pump's normal value",
          "Falling pressure means a choked suction or wear",
          "Follow the Pump troubleshooting tree"),
         ("Sediment / grit build-up", "Desludging per schedule; dead volume not increasing",
          "Grit build-up reduces working volume and wears pumps",
          "Plan desludging; improve grit removal upstream"),
         ("Level instrument agreement", "SCADA level within ± 5 % of manual dip",
          "Foam and crust fool radar / ultrasonic level sensors",
          "Clean or recalibrate the sensor; cross-check with a dip each week"),
     ],
     "notes": ["CDT/PST tanks are confined spaces with H2S risk - entry only under permit with gas testing.",
               "Keep agitators running whenever the tank feeds the decanters or screw presses.",
               "Polymer-rich centrate returning to the CDT can cause foaming - watch centrate clarity."]},
]

# ----------------------------------------------------------------------------------------------------------------------
CASES = [
    K("KB-0333", ["Decanter"], ["grease", "vibration", "bearing"], "Low bowl grease with rising decanter vibration",
      "Main bearing lubrication starvation",
      "Regreased main bearings per OEM schedule and quantity, repaired the auto-lubricator line, trended vibration and "
      "bearing temperature for the shift",
      why=["Why the rising vibration? Feed-end main bearing running hot (88 °C) and rough",
           "Why hot? Bearing short of grease - no fresh grease at the purge",
           "Why no grease? Auto-lubricator reservoir empty for about a week",
           "Why unnoticed? Reservoir level not on the shift round and no low-level alarm"],
      category="Man", prevent="Lubricator level added to the SLS shift checklist; low-level contact wired to SCADA"),
    K("KB-0611", ["WAM"], ["mesh", "choke", "flow"], "WAM screen mesh partially blocked",
      "Fibrous solids build-up on mesh from low wash water",
      "Cleaned mesh under LOTO, cleaned wash line strainer, restored spray pressure to 2.5 bar, inspected screw brush",
      why=["Why the low throughput? Screen mesh matted with fibres over half its length",
           "Why matted? Wash spray weak along the whole bar",
           "Why weak? Wash water pressure 0.8 bar - line strainer blocked",
           "Why blocked? Wash line strainer not on any cleaning schedule"],
      category="Method", prevent="Weekly strainer cleaning added to PM; pressure gauge fitted after the strainer"),
    K("KB-0201", ["Decanter"], ["vibration", "stop", "flush", "power"],
      "Decanter vibration trip on restart after a grid power failure",
      "Uneven solids set in the bowl after an unflushed stop",
      "Ran low-speed hot-water flush for 40 min; vibration fell from 9 to 2.5 mm/s; restored feed slowly",
      why=["Why the vibration trip? Bowl out of balance at run-up",
           "Why out of balance? Solids settled unevenly in the stopped bowl",
           "Why not flushed? Power cut stopped the flush water pump too",
           "Why no flush water? Flush pump not on the DG-backed board"],
      category="Environment", prevent="Flush pump moved to DG board; PLC auto-flush step added on trip recovery"),
    K("KB-0202", ["Decanter"], ["torque", "wet cake", "scroll", "vibration"],
      "Torque creeping up and cake getting wetter over six weeks on Decanter 2",
      "Scroll flight tiles worn by grit",
      "Rotating assembly sent for re-tiling and dynamic balancing; feed zone liner replaced",
      why=["Why the torque creep? Scroll no longer conveying cake efficiently",
           "Why? Flight tiles worn 4 mm and several cracked",
           "Why so fast? High sand load from press-mud feedstock",
           "Why not controlled? No grit check at feedstock reception"],
      category="Material", prevent="Sand test at reception with limit; weekly torque trend at constant feed"),
    K("KB-0204", ["Decanter"], ["differential", "torque", "trip", "plug"],
      "Decanter 3 repeated high-torque trips and plugging after a night shift",
      "Differential speed reduced from 6 to 2 rpm by an operator chasing drier cake",
      "Restored the logged recipe (6 rpm), flushed the bowl, restarted at 70 % feed",
      why=["Why the torque trips? Bowl plugging with cake",
           "Why plugging? Differential too low for the feed solids load",
           "Why changed? Operator tried to fix wet cake by lowering differential",
           "Why possible? Settings not password-protected and no setpoint log or training"],
      category="Man", prevent="HMI settings protected; setpoint log introduced; operators trained on differential vs torque"),
    K("KB-0205", ["Decanter"], ["polymer", "centrate", "wet"],
      "Dirty centrate and wet cake on all decanters during monsoon",
      "Polymer powder caked by humidity - lumpy solution with low active strength",
      "Discarded caked bags, made fresh solution, jar-tested and raised dose from 7 to 8 kg/t DS",
      why=["Why the dirty centrate? Flocs not forming",
           "Why? Polymer solution full of fish-eyes",
           "Why? Powder had absorbed moisture and lumped in the wetting head",
           "Why? Bags stored open on the floor in the humid SLS building"],
      category="Environment", prevent="Polymer stored sealed in a dry room on pallets; FIFO stock rotation"),
    K("KB-0212", ["WAM"], ["flow", "choke", "overflow", "material flow"],
      "WAM 3 and WAM 4 choking and inlet overflow while WAM 2 was down",
      "Separators overfed - total SLS feed was not reduced when one machine was out",
      "Reduced feed pump speed, cleared inlets, spread feed evenly across in-service separators",
      why=["Why choking? Feed above the separators' rated flow",
           "Why? WAM 2's share was pushed to the others",
           "Why? No rule to cut SLS feed when a separator is down"],
      category="Method", prevent="Maximum feed per separator posted; feed reduced when one is out of service"),
    K("KB-0213", ["WAM"], ["fibre", "plastic", "choke", "trip"],
      "WAM 1 overload trips with plastic film wrapped on the screw",
      "Plastic contamination in received feedstock",
      "Removed wrapped plastic under LOTO, checked screen, informed supplier",
      why=["Why the trip? Motor overloaded by material wrapped on the screw",
           "Why wrapped? Plastic film and twine in the digestate",
           "Why in the feed? Packaged waste batch accepted without a visual check"],
      category="Material", prevent="Visual contamination check at reception; feedstock spec shared with suppliers"),
    K("KB-0215", ["WAM"], ["mesh", "filtrate", "torn"],
      "Fibres in WAM 5 filtrate and solids building up in the CDT",
      "Screen torn by a stone",
      "Replaced screen basket, straightened a bent flight, desludged CDT inlet",
      why=["Why fibres in filtrate? Screen torn over 10 cm",
           "Why torn? Stone jammed between flight and screen",
           "Why a stone? No stone trap ahead of the separators"],
      category="Machine", prevent="Stone trap fitted on the SLS feed line; weekly screen inspection"),
]
