"""Feeding and material handling: feed-hall shredding lines ("Shredder 1 / 2 Full Line" — shredder, feed hopper and
belt / screw conveyors for press mud, napier grass and agri residue), SLS bagging and briquetting machines for the
separated digestate solids / fermented organic manure, and the generic "Machine" type that is also the fallback for
any equipment not otherwise modelled (so its causes cover drives, gearboxes, belts and material handling in
general). Also the normal operating envelope of the feed hall (FEED profile).

Sources: biogas feedstock pre-treatment OEM literature (blade / rotor shredders, wet cutters with heavy-material
and stone traps, magnetic separators on conveyors), biogas pre-treatment maintenance guidance (blade inspection,
wear plates, belts and pulleys), conveyor belt maintenance practice (tracking, tension, skirt rubbers, dust
extraction), academic studies of screw-extruder biomass briquetting (screw and die wear from sand and high
pressure, moisture limits), bagging machine OEM practice (load-cell calibration, auger filler and sealer
maintenance), anaerobic-digestion feeding guidance (TS %, particle size, C:N, mixing tank levels) and plant incident
history (incident_log_2026.csv, incident_log_agitation_feeding.csv), OEM_Feed_Shredder_and_Conveyor_Maintenance.md
and SOP-ROT-01 (LOTO).
"""
from .dsl import B, C, K, Q, R, W

TREES = {}


def _lik(ids, v, **kw):
    d = {c: v for c in ids}
    d.update(kw)
    return d


# ---------------------------------------------------------------------------
# Shredder
# ---------------------------------------------------------------------------

_S = ["blades", "foreign", "wet", "overfeed", "conv", "drive", "seal", "trip"]


def _s(v, **kw):
    return _lik(_S, v, **kw)


TREES["Shredder"] = {
    "causes": [
        C("blades", "Blunt or worn cutter blades", "Machine", ["material flow", "blade", "cut"], [
            "Stop the shredder line and apply LOTO (SOP-ROT-01); wait for the rotor to stop fully",
            "Inspect the cutter blades and counter-knives; rotate, re-sharpen or replace as a set",
            "Reset the blade-to-counter-knife gap to the OEM value",
            "Check the screen / grate for wear and blockage",
            "Restart empty, then feed at rated capacity and check cut length (≈ 20–40 mm)"],
          why=W("Why were the blades blunt?", [
              B("Blade change is overdue", W("Why was the blade change missed?", [
                  B("No tonnage / hours-based blade schedule", R(
                      "Blade wear is not tracked against tonnes processed", "Method",
                      prevent=["Log tonnes per day and change / rotate blades at the OEM tonnage",
                               "Weekly blade check with a photo in the PM record"])),
                  B("No spare blade set in stock", R(
                      "Critical spares (blade set, counter-knife) not kept at minimum stock", "Method",
                      prevent=["Keep one full blade set and counter-knife in stores with a reorder level"])),
              ])),
              B("Blades wear fast from sand and stones", R(
                  "Feedstock carries sand / soil (press mud, field-collected residue) with no acceptance check", "Material",
                  prevent=["Visual and sand-content check of each load at reception; reject heavily soiled loads",
                           "Use hard-faced or tungsten-carbide-tipped blades"])),
          ], how="Look at the blade edges: rounded edges mean normal wear; nicks and chips mean stones or metal."),
          case="KB-0624"),
        C("foreign", "Foreign object (stone / metal) jammed in the cutting chamber", "Material",
          ["knock", "bang", "jam", "stone"], [
            "Stop the shredder and apply LOTO; never clear a jam with the drive energised",
            "Open the inspection door and remove the object with tools, not hands; watch for stored energy in the rotor",
            "Inspect blades and counter-knives for chips and cracks; replace damaged ones",
            "Check the magnet and stone trap upstream; clean them",
            "Restart empty, then feed slowly"],
          why=W("Why did the foreign object reach the shredder?", [
              B("Magnet or stone trap not catching it", W("Why did the protection miss it?", [
                  B("Magnet switched off or not cleaned", R(
                      "Magnetic separator cleaning / operation not in the shift checklist", "Man",
                      prevent=["Add 'magnet ON and cleaned' to the shift start-up checklist",
                               "Interlock the shredder start with the magnet running"])),
                  B("No stone trap on this line", R(
                      "Line designed without heavy-material separation for field-collected feed", "Machine",
                      prevent=["Fit a stone trap / heavy-material separator ahead of the shredder"])),
              ])),
              B("Loads contain stones, iron and debris", R(
                  "No feedstock acceptance criteria with suppliers; loads not inspected", "Material",
                  prevent=["Write feedstock acceptance criteria into supplier agreements",
                           "Inspect and spread suspect loads on the tipping floor before loading"])),
          ], how="Keep the object you removed: a stone points to supplier / yard; a bolt or tine points to plant debris."),
          case="KB-0407"),
        C("wet", "Wet, sticky or over-long feed wrapping / bridging", "Material", ["choke", "wrap", "wet", "bridging"], [
            "Stop the line under LOTO and clear wrapped fibre from the rotor and bridged material from the hopper",
            "Blend wet press mud or fresh napier with drier residue before loading",
            "Reduce the feed rate until the material flows freely",
            "Check that bale twine and plastic are removed at reception"],
          why=W("Why was the feed so wet or long?", [
              B("Feed stored uncovered and soaked by rain", R(
                  "Feedstock yard has no cover or drainage for the monsoon", "Environment",
                  prevent=["Cover the feedstock pad (tarpaulin / shed) and give it a drained slope",
                           "Use first-in-first-out from the yard so wet heaps do not age"])),
              B("Fresh green napier fed without wilting / pre-cut", R(
                  "Feeding SOP has no blending rule for wet or long-fibre feed", "Method",
                  prevent=["Add a blending rule (wet : dry ratio) to the feeding SOP",
                           "Pre-chop long grass before it reaches the shredder hopper"])),
              B("Twine and plastic left on bales", R(
                  "No picking step for twine and plastic at reception", "Man",
                  prevent=["Assign a picker at the tipping floor and train loader operators"])),
          ], how="Squeeze a handful of the feed: if water runs out, it is too wet; check stem length and look for twine."),
          case="KB-0408"),
        C("overfeed", "Feed overload — hopper loaded too fast or unevenly", "Man", ["material flow", "current", "overload"], [
            "Ask the loader operator to feed in small, steady scoops",
            "Let the hopper run down to the normal level before loading again",
            "Set the conveyor / feeder speed to rated capacity on the VFD",
            "Fit a hopper level marker or camera so the operator can see the level"],
          why=W("Why was the shredder overfed?", [
              B("Operator dumps full buckets to keep up", W("Why does the operator rush?", [
                  B("Daily feed target squeezed into fewer hours", R(
                      "Feeding schedule gives too few hours for the daily tonnage", "Method",
                      prevent=["Spread feeding across two shifts; set an hourly tonnage limit"])),
                  B("Operator not trained on rated capacity", R(
                      "Loader operators not trained on shredder capacity and overload signs", "Man",
                      prevent=["Train loader operators; post the rated t/h at the hopper",
                               "Add hopper-level signal lights (green / amber / red)"])),
              ])),
              B("No automatic load control", R(
                  "Feeder speed not linked to shredder motor current", "Machine",
                  prevent=["Add current-based feeder speed control (slow / reverse on high load)"])),
          ], how="Watch two or three loader cycles and the motor current at the same time."),
          case="KB-0624"),
        C("conv", "Conveyor belt slipping, misaligned or spilling", "Machine", ["belt", "spillage", "conveyor", "material flow"], [
            "Stop the conveyor under LOTO (pull-cord is not an isolation)",
            "Clean material build-up from the head and tail pulleys and return idlers",
            "Re-track the belt with the tail take-up; re-tension to OEM value",
            "Replace worn skirt rubbers and seized idlers",
            "Restart empty and watch tracking for 10 minutes before feeding"],
          why=W("Why is the conveyor slipping or running off?", [
              B("Material stuck on pulleys and idlers", W("Why is material building up?", [
                  B("Belt scraper worn or missing", R(
                      "Belt scrapers not in the PM and not adjusted", "Method",
                      prevent=["Add belt scraper inspection / adjustment to the weekly PM"])),
                  B("Sticky wet feed carried back", R(
                      "Wet press mud fed without blending makes the belt carry back", "Material",
                      prevent=["Apply the wet : dry blending rule; clean pulleys every shift in monsoon"])),
              ])),
              B("Belt tension or alignment wrong", R(
                  "No belt tension / tracking check after belt jointing or replacement", "Method",
                  prevent=["Record tension and tracking after every belt job; recheck after 24 h"])),
          ], how="Look at the head pulley and the belt edge: build-up, edge wear and a polished pulley show the cause."),
          case="KB-0409"),
        C("drive", "Drive bearing, gearbox or coupling wear", "Machine", ["vibration", "bearing", "temperature", "oil", "sound"], [
            "Stop the shredder under LOTO",
            "Check gearbox oil level and condition; check rotor bearings for play and heat",
            "Inspect the coupling / belt drive; replace worn elements and align",
            "Replace failed bearings; regrease rotor bearings to OEM quantity",
            "Restart and trend vibration and bearing temperature for one shift"],
          why=W("Why did the drive wear?", [
              B("Bearings / gearbox not lubricated", R(
                  "Shredder lubrication points missing from the lubrication schedule", "Man",
                  prevent=["Add every shredder grease and oil point to the lubrication route with quantities"])),
              B("Shock loads from jams and stones", R(
                  "Repeated jams and foreign objects hammer the drive", "Material",
                  prevent=["Fix foreign-object control upstream; fit a torque-limiting coupling"])),
              B("Dust gets into the bearings", R(
                  "Bearing seals exposed to fibre dust; no regular cleaning", "Environment",
                  prevent=["Fit taconite / labyrinth bearing seals; blow down the drive weekly"])),
          ]),
          case="KB-0410"),
        C("seal", "Dust escaping from worn chute skirts and weak dust extraction", "Environment", ["dust"], [
            "Replace worn chute skirt rubbers and dust seals",
            "Check the dust-extraction fan, ducts and filter bags; clean or replace",
            "Clean up spilled material so it does not get into bearings or conveyors",
            "Wear a dust mask (FFP2) when working in the shredder area"],
          why=W("Why is dust escaping?", [
              B("Skirts and seals worn out", R(
                  "Chute skirts and seals not in the PM", "Method",
                  prevent=["Monthly check of skirt rubbers and chute seals"])),
              B("Dust extraction not pulling", R(
                  "Dust collector bags not cleaned / fan not maintained", "Machine",
                  prevent=["Weekly dust collector check; differential pressure gauge on the bag filter"])),
              B("Very dry, dusty feed in summer", R(
                  "No dust suppression for dry agri residue in the hot season", "Environment",
                  prevent=["Light water mist at the hopper in dry season", "Close the feed hall doors on windy days"])),
          ]),
          ),
        C("trip", "Nuisance trips from wrong overload / speed-sensor setting", "Measurement", ["trip", "current", "sensor"], [
            "Read the trip cause on the panel / VFD fault log",
            "Check the overload relay setting against the motor nameplate",
            "Check the zero-speed / rotation sensor gap and cable on the conveyor tail pulley",
            "Clean and re-gap the sensor; test the trip; restart"],
          why=W("Why is the protection tripping wrongly?", [
              B("Speed sensor dirty or gap wrong", R(
                  "Rotation / zero-speed sensors not in the PM; dust covers them", "Measurement",
                  prevent=["Monthly clean and gap check of all zero-speed sensors"])),
              B("Overload set below motor rating", R(
                  "Protection settings not verified after motor or VFD replacement", "Measurement",
                  prevent=["Keep a motor protection register and verify after every change"])),
          ]),
          case="KB-0413"),
    ],
    "questions": [
        Q("current", "Watch the shredder motor current (MCC ammeter or SCADA) while it is feeding. How does it behave?", [
            ("Steady near rated", _s(1.1, blades=0.5, foreign=0.6, overfeed=0.3, trip=0.8, seal=1.6)),
            ("Swings high with each loader dump", _s(0.7, overfeed=3.5, blades=1.6, wet=1.3)),
            ("Stays high even with light feed", _s(0.7, blades=3.0, drive=1.8, wet=1.5)),
            ("Sudden spike with a bang, then trip", _s(0.6, foreign=3.5)),
            ("Trips with normal current", _s(0.6, trip=4.0)),
        ], ["current", "trip", "overload", "material flow"], {"tag": "motor_current_a", "option": 0, "above": 22},
          how="Stand at the MCC or ask the control room to watch the current trend for a few loader cycles. Compare with "
              "the full-load amps on the motor nameplate.",
          purpose="The current pattern tells overfeeding, blunt blades, a foreign object and a false trip apart."),
        Q("blades", "With the line stopped under LOTO and the rotor at rest, look at the cutter blades. How are they?", [
            ("Sharp, undamaged", _s(1.1, blades=0.25, foreign=0.7)),
            ("Blunt / rounded edges", _s(0.8, blades=4.0)),
            ("Chipped / broken teeth", _s(0.7, foreign=4.0, blades=1.2)),
            ("Wrapped with wet fibre or twine", _s(0.7, wet=4.0)),
        ], ["blade", "cut", "material flow", "jam", "wrap"],
          how="Only after LOTO, a try-start and waiting for the rotor to stop: open the inspection door, use a torch, and "
              "do not put hands between blades — the rotor can move under its own weight.",
          purpose="Blade condition shows whether it is wear, a foreign object, or wet fibre wrapping."),
        Q("feed", "Grab a handful of what is going into the hopper. What is it like?", [
            ("Normal mix, fairly dry", _s(1.1, wet=0.3, foreign=0.8)),
            ("Wet / sticky press mud or soaked grass", _s(0.8, wet=4.0, conv=1.5)),
            ("Long stalks, twine or plastic", _s(0.8, wet=3.0, blades=1.3)),
            ("Stones, soil or metal in the load", _s(0.8, foreign=3.5, blades=1.5)),
        ], ["choke", "wet", "wrap", "stone"],
          how="Take a handful from the tipping floor, not the hopper. Squeeze it — water running out means it is too wet.",
          purpose="Most shredder choking starts with what we feed it."),
        Q("loader", "How is the loader feeding the hopper right now?", [
            ("Steady small scoops, hopper half full", _s(1.1, overfeed=0.25)),
            ("Big dumps, hopper overflowing", _s(0.8, overfeed=4.0, seal=1.3)),
            ("Hopper often runs empty", _s(1.0, overfeed=0.5, trip=1.3)),
        ], ["material flow", "overload", "dust"],
          how="Watch two or three loader cycles from a safe spot outside the loader's path.",
          purpose="Overfeeding is the most common cause of shredder overload and spillage."),
        Q("dust", "Is dust or material escaping anywhere? Where?", [
            ("From chute skirts / seals", _s(0.7, seal=5.0)),
            ("Spilling off the conveyor belt", _s(0.8, conv=3.5, overfeed=1.3)),
            ("Overflowing from the hopper", _s(0.8, overfeed=3.0)),
            ("No dust or spillage", _s(1.1, seal=0.25, conv=0.5)),
        ], ["dust", "spillage"],
          how="Walk along the line from hopper to discharge. Wear a dust mask; stay off the belt walkway while running.",
          purpose="Where material escapes separates seal wear, belt problems and overfeeding."),
        Q("belt", "Look at the conveyor belt while running. How is it tracking?", [
            ("Centred, no slip", _s(1.05, conv=0.25)),
            ("Running off to one side", _s(0.8, conv=3.5)),
            ("Slipping at the head pulley", _s(0.8, conv=3.5, overfeed=1.3, wet=1.3)),
        ], ["belt", "spillage", "material flow"],
          how="Watch the belt edge at the head and tail pulleys from the walkway. Never touch the belt or reach in; use "
              "the pull-cord only for emergencies.",
          purpose="A belt that slips or runs off spills feed and starves the shredder."),
        Q("noise", "Listen at the shredder and its drive. What do you hear?", [
            ("Normal steady cutting", _s(1.1, drive=0.3, foreign=0.4)),
            ("Bang or loud clunk, then stop", _s(0.7, foreign=4.0)),
            ("Grinding or whine from the gearbox", _s(0.7, drive=4.0)),
            ("Squeal from the conveyor", _s(0.8, conv=3.0)),
        ], ["sound", "noise", "knock", "vibration", "bang"], {"tag": "vibration_mm_s", "option": 0, "above": 4.5},
          how="Listen from the walkway at the cutting chamber, then at the gearbox and bearings. Ear defenders on — "
              "shredders are loud.",
          purpose="A bang means a foreign object, a grind means the drive, a squeal means the belt."),
        Q("temp", "Put the IR gun on the shredder rotor bearings and gearbox. What is the hottest reading?", [
            ("Below 70°C", _s(1.1, drive=0.3)),
            ("70–85°C", _s(0.9, drive=2.5, blades=1.3, overfeed=1.2)),
            ("Above 85°C", _s(0.6, drive=4.0), ["rotating_critical"]),
        ], ["temperature", "bearing", "vibration", "oil"], {"tag": "bearing_temp_c", "option": 0, "above": 80},
          how="Aim at the bearing housings and gearbox body from outside the guards. Don't touch — they may be hot.",
          purpose="A hot bearing or gearbox means the drive itself is failing."),
        Q("empty", "Does the line trip even when it is running empty?", [
            ("Yes, trips running empty", _s(0.5, trip=4.0, drive=1.5)),
            ("Only trips under load", _s(1.1, trip=0.4, overfeed=1.4, foreign=1.3, blades=1.3)),
            ("It does not trip", _s(1.1, trip=0.2)),
        ], ["trip", "current", "sensor"],
          how="After clearing the hopper, restart the line with no feed and run it for 10 minutes. Check the panel for "
              "the trip message.",
          purpose="A trip with no load points to the protection setting or a sensor, not the material."),
        Q("magnet", "Check the magnet and stone trap before the shredder. What's in them?", [
            ("Clean, little caught", _s(1.05, foreign=0.6)),
            ("Full of metal or stones", _s(0.9, foreign=3.0, blades=1.5)),
            ("Magnet off or trap bypassed", _s(0.9, foreign=3.5)),
        ], ["jam", "stone", "knock", "bang"],
          how="With the conveyor stopped under LOTO, look at the overband magnet face and the stone trap. Use gloves; "
              "magnets grab tools strongly.",
          purpose="If the protection is full or off, foreign objects are getting through to the blades."),
    ],
}

# ---------------------------------------------------------------------------
# Machine (bagging, briquetting, and fallback for unknown equipment)
# ---------------------------------------------------------------------------

_M = ["lube", "belt", "jam", "wear", "brg", "mis", "weigh", "elec"]


def _m(v, **kw):
    return _lik(_M, v, **kw)


TREES["Machine"] = {
    "causes": [
        C("lube", "Gearbox / drive lubrication low or contaminated", "Man", ["oil", "grease", "lube"], [
            "Stop the machine under LOTO",
            "Check gearbox oil level and colour; top up or change to the grade on the lube label",
            "Grease the bearings and chains to the lubrication chart",
            "Find and fix the leak source (oil seal, drain plug, gasket)",
            "Restart and check temperature after 1 h"],
          why=W("Why was lubrication short?", [
              B("Lube point missed on rounds", W("Why was it missed?", [
                  B("Not on the lubrication route", R(
                      "Machine lubrication points are not listed on the lubrication route", "Man",
                      prevent=["Map every lube point with grade and quantity; add to the route with a tick-sheet"])),
                  B("Machine runs in campaigns and gets forgotten", R(
                      "Intermittently used machines have no run-hour based PM", "Method",
                      prevent=["Add run-hour meters and trigger PM by hours, not calendar"])),
              ])),
              B("Oil leaking out", R(
                  "Oil seals and gaskets not replaced at overhaul", "Method",
                  prevent=["Replace oil seals at overhaul; check for leaks on weekly rounds"])),
              B("Dust or water in the oil", R(
                  "Breathers and fill caps exposed to dust and washdown", "Environment",
                  prevent=["Fit filter breathers; keep fill caps closed; no hosing near gearboxes"])),
          ]),
          case="KB-0420"),
        C("belt", "Drive belt or chain worn, slack or misaligned", "Machine", ["belt", "chain", "slip"], [
            "Stop the machine under LOTO",
            "Replace worn belts as a matched set (or the chain and sprockets together)",
            "Align pulleys / sprockets with a straight edge or laser",
            "Tension to OEM deflection; recheck after 4 h of running"],
          why=W("Why did the belt / chain wear?", [
              B("Tension not checked", R(
                  "Belt / chain tension not in the PM", "Method",
                  prevent=["Monthly belt tension and chain slack check with OEM values on the PM sheet"])),
              B("Pulleys or sprockets misaligned", R(
                  "No alignment check after belt or motor replacement", "Method",
                  prevent=["Check alignment with a straight edge / laser after every drive job"])),
              B("Single belt replaced in a set", R(
                  "Fitters replace only the broken belt; matched sets not stocked", "Man",
                  prevent=["Stock matched belt sets; train fitters to replace the full set"])),
          ]),
          ),
        C("jam", "Material jam / bridging (wet, lumpy or oversize solids)", "Material",
          ["material flow", "choke", "jam", "bridging"], [
            "Stop the machine and clear the jam under LOTO — never by hand with the drive live",
            "Check the moisture of the incoming solids; blend or dry if too wet",
            "Break lumps and remove oversize / foreign material at the hopper",
            "Restart empty, then load gradually"],
          why=W("Why is material jamming?", [
              B("Solids too wet from the separator", W("Why is the cake too wet?", [
                  B("Separator not dewatering well", R(
                      "Screw-press / decanter settings and wear not checked against cake dryness", "Method",
                      prevent=["Test cake moisture each shift; adjust separator back-pressure / differential speed"])),
                  B("Stockpile soaked by rain", R(
                      "Solids stockpile uncovered in the monsoon", "Environment",
                      prevent=["Cover the solids stockpile and drain the pad"])),
              ])),
              B("Lumps or foreign material in the feed", R(
                  "No screen or lump breaker ahead of the machine", "Machine",
                  prevent=["Fit a grid / lump breaker on the hopper; train operators to remove debris"])),
          ]),
          case="KB-0422"),
        C("wear", "Worn screw, die or wear parts (poor output quality)", "Machine", ["quality", "wear", "weak", "die"], [
            "Stop the machine under LOTO",
            "Measure screw flight and die / sleeve wear against OEM limits",
            "Hard-face or replace the screw tip and die sleeve",
            "Check heater bands (briquetting) or auger / spout (bagging)",
            "Restart and check output density / bag fill"],
          why=W("Why did the wear parts wear early?", [
              B("Sand and grit in the solids", R(
                  "Grit in digestate solids not controlled (from press mud / dung)", "Material",
                  prevent=["Track ash / sand content of the solids; improve grit removal upstream",
                           "Use hard-faced (stellite / tungsten carbide) screw tips"])),
              B("Wear not measured until output failed", R(
                  "No wear measurement in the PM", "Method",
                  prevent=["Measure screw / die wear every 250 h and plan replacement before limit"])),
          ]),
          case="KB-0423"),
        C("brg", "Bearing wear / overheating in the drive", "Machine", ["vibration", "sound", "bearing", "temperature", "hot"], [
            "Stop the machine under LOTO",
            "Check bearing play and condition; replace the bearing set if rough",
            "Regrease / refill with the correct lubricant",
            "Check alignment and belt tension before restart",
            "Trend bearing temperature for one shift"],
          why=W("Why did the bearing fail?", [
              B("Not lubricated or wrong grease", R(
                  "No lubrication schedule or labelling for the bearings", "Man",
                  prevent=["Label each bearing with grease grade and quantity; add to the lube route"])),
              B("Overloaded by belt tension or misalignment", R(
                  "Belt over-tensioned / misaligned after maintenance", "Method",
                  prevent=["Tension to OEM value with a gauge; align with a straight edge / laser"])),
              B("Dust and water got into the bearing", R(
                  "Bearing seals not suited to dusty, wet environment", "Environment",
                  prevent=["Use sealed / labyrinth bearings; keep the area clean"])),
          ]),
          ),
        C("mis", "Misalignment or loose mounting after maintenance", "Method", ["vibration", "coupling", "loose"], [
            "Stop the machine under LOTO",
            "Check and re-torque base and frame bolts; check for soft foot",
            "Replace the worn coupling element; align motor to gearbox",
            "Restart and trend vibration"],
          why=W("Why is it out of alignment or loose?", [
              B("Not aligned after maintenance", R(
                  "No alignment step in the reassembly procedure", "Method",
                  prevent=["Add alignment with a recorded result to every drive work order"])),
              B("Bolts loosen from vibration", R(
                  "Bolt torque check not in the PM", "Method",
                  prevent=["Quarterly torque check of base and frame bolts; use lock nuts"])),
          ]),
          ),
        C("weigh", "Weighing or sensor out of calibration (wrong bag weight, false stops)", "Measurement",
          ["weight", "sensor", "calibration", "stop"], [
            "Check bag weights with a calibrated test weight / platform scale",
            "Clean the load cell and remove build-up from the weigh hopper",
            "Re-zero and span-calibrate the weigher; record the result",
            "Clean and re-gap proximity / photo sensors; check cables"],
          why=W("Why is the measurement wrong?", [
              B("Load cell / hopper fouled with material", R(
                  "Weigh hopper cleaning not scheduled; material builds up and adds weight", "Method",
                  prevent=["Clean the weigh hopper every shift; check zero at shift start"])),
              B("Never re-calibrated", R(
                  "No calibration schedule for weighers and sensors", "Measurement",
                  prevent=["Monthly calibration check with certified test weights; keep a calibration log"])),
              B("Sensor dusty or knocked out of position", R(
                  "Sensors exposed to dust and impact; not checked", "Environment",
                  prevent=["Fit sensor guards; wipe sensors on shift rounds"])),
          ]),
          case="KB-0426"),
        C("elec", "Motor, VFD or control fault (trips, won't start)", "Machine", ["trip", "current", "motor", "start"], [
            "Isolate at the MCC and apply LOTO",
            "Have the electrician check insulation, terminals, phase currents and the VFD fault log",
            "Check emergency stops, guard interlocks and limit switches are reset and working",
            "Check the overload setting against the nameplate; restart and record current"],
          why=W("What caused the electrical fault?", [
              B("Moisture or dust in the motor / panel", R(
                  "Panels and terminal boxes not sealed against dust and washdown", "Environment",
                  prevent=["Seal glands and panel doors; filter panel fans; no hosing near panels"])),
              B("Loose terminal or failing contactor", R(
                  "No thermographic scan of panels", "Machine",
                  prevent=["Quarterly thermographic scan; re-torque terminals in PM"])),
              B("Interlock or setting changed", R(
                  "Settings and interlocks not documented or verified after changes", "Measurement",
                  prevent=["Keep a settings register; verify after any change"])),
          ]),
          ),
    ],
    "questions": [
        Q("oil", "Check the gearbox oil sight glass and grease points. What do you find?", [
            ("Oil level OK, clean", _m(1.15, lube=0.2, brg=0.7)),
            ("Low or leaking", _m(0.8, lube=4.5, brg=1.0)),
            ("Dark, milky or gritty", _m(0.8, lube=3.0, brg=1.8)),
        ], ["oil", "grease", "lube"],
          how="Read the sight glass on the gearbox with the machine stopped. Look for oil on the floor and around seals. "
              "Grease nipples should show fresh grease at the seal.",
          purpose="Low or dirty lubrication is the most common cause of drive wear."),
        Q("lubelog", "Check the lubrication log or tag on this machine: when was it last oiled / greased?", [
            ("Within schedule", _m(1.1, lube=0.3, brg=0.8)),
            ("Overdue or not on the log at all", _m(0.8, lube=3.5, brg=1.3)),
        ], ["oil", "grease", "lube"],
          how="Look for the lubrication tag on the machine or ask the lube technician for the route sheet.",
          purpose="Missed lubrication is the usual reason a drive runs short of oil or grease."),
        Q("belt", "With the machine stopped under LOTO, look at the drive belts or chain. How are they?", [
            ("Good, correct tension", _m(1.1, belt=0.2)),
            ("Worn, cracked or slack", _m(0.8, belt=4.0)),
            ("Running off the pulley / sprocket", _m(0.8, belt=3.0, mis=2.0)),
        ], ["belt", "chain", "slip"],
          how="Only after LOTO: remove the belt guard, check for cracks and glazing, and press the belt midway — it should "
              "deflect about 1 cm per 50 cm of span. Refit the guard.",
          purpose="Slipping or worn belts cause speed loss, squeal and stoppages."),
        Q("flow", "Does material flow freely through the machine?", [
            ("Yes, flows freely", _m(1.1, jam=0.25)),
            ("Choking / bridging in the hopper", _m(0.8, jam=4.0)),
            ("Flows but output is poor", _m(0.8, wear=3.5, jam=1.2)),
        ], ["material flow", "choke", "jam", "quality"],
          how="Look into the hopper from the platform (do not reach in) and watch the outlet for a few minutes.",
          purpose="Tells a material problem apart from a mechanical one."),
        Q("moist", "Squeeze a handful of the incoming solids. How wet are they?", [
            ("Crumbly, holds shape lightly", _m(1.05, jam=0.5)),
            ("Wet and sticky, water squeezes out", _m(0.9, jam=3.5, wear=1.2)),
            ("Very dry and dusty", _m(1.0, wear=1.5, jam=0.8)),
        ], ["material flow", "choke", "jam", "quality"],
          how="Take a sample from the conveyor or stockpile, not the machine. If water runs between your fingers it is "
              "too wet for briquetting or bagging.",
          purpose="Wet solids bridge and jam; very dry, sandy solids wear the screw and die."),
        Q("quality", "How does the output look — briquettes or filled bags?", [
            ("Normal", _m(1.1, wear=0.3, weigh=0.5, jam=0.8)),
            ("Briquettes crumbly / low density", _m(0.8, wear=3.5, jam=1.5)),
            ("Bag weights wrong or varying", _m(0.8, weigh=4.0)),
        ], ["quality", "weight", "die", "wear"],
          how="Break a briquette by hand and compare with a good one; or weigh three bags on the platform scale.",
          purpose="Output quality points to worn wear parts or a weighing problem."),
        Q("testwt", "Put a known test weight on the weigher (or weigh a bag on the platform scale). Does it agree?", [
            ("Agrees within 0.5%", _m(1.05, weigh=0.2)),
            ("Off by more than 1%", _m(0.6, weigh=4.0)),
            ("Zero drifts with the hopper empty", _m(0.6, weigh=4.0)),
        ], ["weight", "calibration", "sensor"],
          how="Use the certified test weight kept with the bagging machine; place it in the weigh hopper with the "
              "machine in manual mode and read the display.",
          purpose="Proves whether the weigher is out of calibration."),
        Q("noise", "Listen at the drive. What do you hear?", [
            ("Smooth, normal", _m(1.15, brg=0.3, mis=0.4, belt=0.6)),
            ("Grinding or growl from a bearing", _m(0.7, brg=4.0, lube=1.6)),
            ("Squeal from the belt", _m(0.7, belt=4.0)),
            ("Knock or rattle, frame shaking", _m(0.7, mis=4.0, brg=1.2)),
            ("Motor buzz, no turning", _m(0.7, elec=4.0)),
        ], ["sound", "noise", "vibration", "knock"], {"tag": "vibration_mm_s", "option": 0, "above": 4.5},
          how="Listen at the motor, belt / coupling and bearings in turn, from outside the guards.",
          purpose="Each fault sounds different: bearings growl, belts squeal, loose mounts rattle."),
        Q("temp", "Put the IR gun on the bearings and gearbox. What's the hottest reading?", [
            ("Below 70°C", _m(1.1, brg=0.3, lube=0.5)),
            ("70–85°C", _m(0.9, brg=2.5, lube=2.0, mis=1.3)),
            ("Above 85°C", _m(0.6, brg=4.0, lube=2.5), ["rotating_critical"]),
        ], ["temperature", "bearing", "hot", "vibration"], {"tag": "bearing_temp_c", "option": 0, "above": 80},
          how="Aim at bearing housings and the gearbox body from outside the guards; don't touch.",
          purpose="Hot bearings mean lubrication or bearing failure."),
        Q("bolts", "With the machine under LOTO, check the base bolts and coupling. What do you find?", [
            ("Tight, coupling fine", _m(1.1, mis=0.2)),
            ("Loose bolts or worn coupling", _m(0.7, mis=4.0)),
        ], ["vibration", "coupling", "loose"],
          how="Try each base and frame bolt with a spanner; look at the coupling element for cracks.",
          purpose="Loose mounting and misalignment cause vibration and bearing damage."),
        Q("start", "Does the motor start and run normally when empty?", [
            ("Starts and runs normally", _m(1.1, elec=0.2)),
            ("Trips or won't start", _m(0.6, elec=4.0, jam=1.3)),
            ("Stops at random, no fault shown", _m(0.7, elec=2.5, weigh=2.5)),
        ], ["trip", "current", "motor", "start", "stop"], {"tag": "motor_current_a", "option": 0, "above": 22},
          how="Clear the hopper, reset any e-stops and guard interlocks, and start the machine with no material. Note "
              "any fault message on the panel.",
          purpose="Separates electrical and control faults from material or mechanical problems."),
    ],
}

MAINTENANCE = {
    "Shredder": {
        "summary": "Feed-hall shredding lines cut press mud, napier grass and agri residue to a short, even size for "
                   "the digesters. Blade condition, foreign-object protection (magnet, stone trap), feed rate, conveyor "
                   "tracking and the drive (gearbox, bearings, belts) are the main maintenance items.",
        "pm": [
            ("Every shift", "Check magnet and stone trap are on and clean; listen for abnormal noise; check belt tracking and spillage"),
            ("Daily", "Clean head / tail pulleys and scrapers; clean zero-speed sensors in dusty conditions"),
            ("Weekly", "Inspect blades and counter-knives (photo); check cut length; grease rotor bearings"),
            ("Monthly", "Vibration / IR on drive bearings; check belt tension; check chute skirts and dust extraction"),
            ("By tonnage (OEM)", "Rotate / re-sharpen / replace blade set; reset counter-knife gap"),
            ("Yearly", "Gearbox oil change; bearing overhaul; conveyor idler survey"),
        ],
        "failure_modes": ["Blunt blades and long cut length", "Foreign object damage (stones, metal)",
                          "Wrapping and bridging with wet or long-fibre feed", "Overfeeding and overload trips",
                          "Conveyor slip, mistracking and spillage", "Drive bearing / gearbox wear",
                          "Dust emission from worn skirts", "Nuisance trips from sensors or settings"],
        "operating_limits": [("Feed rate", "≤ rated t/h on the nameplate"), ("Cut length", "≈ 20–40 mm"),
                             ("Motor current", "≤ nameplate FLA; swings < ±15 %"),
                             ("Bearing / gearbox temperature", "< 80 °C"),
                             ("Vibration", "< 4.5 mm/s")],
    },
    "Machine": {
        "summary": "Bagging and briquetting machines pack or densify separated digestate solids (fermented organic "
                   "manure); 'Machine' is also the generic type for other drives. Lubrication, belts / chains, "
                   "material moisture and flow, screw / die wear, bearings, alignment and weigher calibration are the "
                   "main maintenance items.",
        "pm": [
            ("Every shift", "Check oil level, belt / chain condition, material flow and abnormal noise; zero the weigher"),
            ("Weekly", "Grease bearings and chains; clean weigh hopper and sensors; check bag seals / briquette quality"),
            ("Monthly", "Belt tension and alignment; base-bolt check; weigher calibration with test weights"),
            ("Every 250 h (briquetting)", "Measure screw and die wear; check heater bands"),
            ("Yearly", "Gearbox oil change; bearing overhaul; electrical thermography"),
        ],
        "failure_modes": ["Low or contaminated lubrication", "Worn / slack belts and chains", "Material jams from wet solids",
                          "Screw and die wear from grit", "Bearing failure", "Misalignment / loose mounting",
                          "Weigher out of calibration", "Motor / control faults"],
        "operating_limits": [("Bearing temperature", "< 80 °C"), ("Vibration", "< 4.5 mm/s"),
                             ("Gearbox oil level", "60–80 % of sight glass"),
                             ("Solids moisture for briquetting", "≈ 8–15 % (dryer needed above)"),
                             ("Bag weight tolerance", "± 0.5 % of nominal")],
    },
}

CONDITIONS = [
    {"id": "FEED", "title": "Feed hall (feed preparation)", "areas": ["FEED"],
     "params": [
         ("Feed total solids (TS) to digester", "10–12 % (max ≈ 12 %)",
          "Thicker feed overloads agitators and pumps and forms crust in the digester",
          "Add dilution water or recirculated liquid fraction; adjust the recipe"),
         ("Particle / cut length after shredder", "≈ 20–40 mm; no stems > 50 mm",
          "Long fibres wrap pump and agitator impellers and float as a crust",
          "Check blade condition and counter-knife gap; reduce feed rate"),
         ("Shredder feed rate", "≤ rated t/h; steady loader cycles",
          "Overfeeding causes overload trips, spillage and uneven cut",
          "Feed in small scoops; spread feeding over the shift"),
         ("Feedstock moisture", "Press mud ≈ 65–75 %; dry residue < 20 %; blend wet with dry",
          "Very wet feed bridges and wraps; very dry feed is dusty and needs more water",
          "Blend wet and dry loads; cover the yard in the monsoon"),
         ("Foreign matter (stones, metal, plastic, twine)", "None visible; magnet and stone trap emptied each shift",
          "Stones and metal break blades; twine and plastic wrap impellers",
          "Inspect loads at reception; keep magnet ON; pick out twine and plastic"),
         ("Sand / grit content", "As low as possible; trend weekly (ash / settled sand test)",
          "Sand wears blades, pumps and seals and settles in the digester, losing volume",
          "Reject heavily soiled loads; use the sand trap; flush settled sand from mixing tanks"),
         ("Mixing / hydrolysis tank level (H1, H2, SBT)", "Between low and high marks (typically 30–85 %)",
          "Too low exposes agitators and starves pumps; too high risks overflow",
          "Match transfer pump runs to feed rate; check level transmitter against a local gauge"),
         ("Mixing tank agitators", "Running per schedule; surface moving, no crust",
          "Without mixing, solids settle and fibres float, causing pump choking",
          "Restart agitators; break crust before transfer; see Agitator checks"),
         ("Feed pH (mixing tank)", "5.5–7.5 (press mud and silage can be acidic)",
          "Very acidic feed can sour the digester if fed too fast",
          "Blend with digestate; feed smaller batches; check digester FOS/TAC"),
         ("Daily feed quantity", "As per feeding plan; changes < 10–15 % per week",
          "Sudden changes in amount or recipe upset the digester biology",
          "Follow the feeding plan; inform process engineer before recipe changes"),
         ("Feed temperature", "Avoid very cold feed; ideally > 15 °C",
          "Large amounts of cold feed drop digester temperature",
          "Feed smaller batches more often; preheat with recirculated digestate if possible"),
         ("C:N ratio of the blend", "≈ 20–30 : 1",
          "Too much nitrogen (poultry litter) raises ammonia; too little slows digestion",
          "Balance nitrogen-rich and carbon-rich feeds per the recipe"),
     ],
     "notes": ["Record every load: source, tonnes, visual quality (wet / soiled / foreign matter).",
               "Never clear a shredder or conveyor jam without LOTO — a pull-cord or e-stop is not an isolation.",
               "Wear a dust mask in the shredder area in the dry season; ear defenders near the shredder.",
               "Change the feed recipe gradually and tell the process engineer; watch digester FOS/TAC for 3–5 days."]},
]

CASES = [
    K("KB-0624", ["Shredder"], ["material flow", "dust", "blade", "current"],
      "Irregular material flow and dust spillage at shredder", "Feed overload with blunt cutter blades",
      "Regulated loader feed rate, rotated and re-sharpened blades, reset counter-knife gap, replaced chute skirts",
      why=["Why irregular flow and spillage? Hopper overfilled and material backed up",
           "Why backed up? Blunt blades cut slowly so throughput fell",
           "Why blunt? Blade change was overdue — no tonnage-based blade schedule",
           "Why overfilled? Loader operator kept full-bucket dumps to meet the daily target"],
      category="Method", prevent="Tonnage-based blade schedule; hourly feed limit and loader operator training"),
    K("KB-0407", ["Shredder"], ["knock", "bang", "jam", "stone"],
      "Loud bang and trip on Shredder 2 line", "Stone in the cutting chamber chipped three blades",
      "LOTO, removed stone, replaced chipped blades, cleaned stone trap, restarted empty",
      why=["Why the bang and trip? A 10 cm stone jammed between rotor and counter-knife",
           "Why did a stone get in? The load was field-collected residue scraped with soil",
           "Why not caught? Stone trap full and not emptied that shift"],
      category="Material", prevent="Stone trap emptied every shift; load inspection at reception"),
    K("KB-0408", ["Shredder"], ["choke", "wrap", "wet"],
      "Shredder 1 choking with wet napier grass in the monsoon", "Rain-soaked grass and twine wrapping the rotor",
      "Cleared rotor under LOTO, blended wet grass with dry residue, removed twine at reception",
      why=["Why choking? Fibre wrapped on the rotor and bridged in the hopper",
           "Why wrapping? Grass was soaked and still tied with twine",
           "Why soaked? Feedstock pad uncovered during the monsoon"],
      category="Environment", prevent="Covered feedstock pad; blending rule; twine picking at reception"),
    K("KB-0409", ["Shredder"], ["belt", "spillage", "material flow"],
      "Conveyor belt running off and spilling after the shredder", "Carry-back of wet press mud built up on tail pulley",
      "Cleaned pulleys, replaced worn scraper blade, re-tracked belt",
      why=["Why running off? Build-up on one side of the tail pulley",
           "Why build-up? Belt scraper worn out",
           "Why worn? Scraper not on any PM checklist"],
      category="Method", prevent="Weekly scraper check in PM; daily pulley cleaning in monsoon"),
    K("KB-0410", ["Shredder"], ["vibration", "bearing", "temperature"],
      "Hot rotor bearing and growl on Shredder 2", "Rotor bearing starved of grease and contaminated with fibre dust",
      "Replaced bearing, fitted labyrinth seal, added grease point to lube route",
      why=["Why the hot bearing? Dry, dust-contaminated grease",
           "Why dry? Grease point not on the lubrication route",
           "Why not listed? Lube route copied from an older line without this bearing"],
      category="Man", prevent="Full lube-point survey; labyrinth seals on rotor bearings"),
    K("KB-0413", ["Shredder"], ["trip", "sensor"],
      "Shredder line tripping every few minutes with light feed", "Zero-speed sensor on discharge conveyor covered in dust",
      "Cleaned and re-gapped sensor to 5 mm; added to monthly PM",
      why=["Why the trips? Zero-speed interlock thought the conveyor had stopped",
           "Why? Sensor face covered with dust and gap opened to 12 mm",
           "Why not caught? Sensors not in the PM"],
      category="Measurement", prevent="Monthly zero-speed sensor clean and gap check"),
    K("KB-0420", ["Machine"], ["oil", "lube", "temperature"],
      "Briquetting machine gearbox running hot", "Low gearbox oil from a leaking output seal",
      "Replaced oil seal, refilled to mark, added gearbox to lube route",
      why=["Why hot? Oil level below the gears",
           "Why low? Output oil seal leaking for weeks",
           "Why not seen? Machine runs in campaigns and was not on the lubrication route"],
      category="Man", prevent="Run-hour based PM for campaign machines; gearbox on lube route"),
    K("KB-0422", ["Machine"], ["material flow", "jam", "choke"],
      "Bagging machine auger jamming with fermented manure", "Solids too wet (cake moisture high from separator)",
      "Cleared auger under LOTO; adjusted screw-press back-pressure; covered stockpile",
      why=["Why jamming? Sticky solids bridged in the hopper",
           "Why sticky? Cake moisture rose to 75 %",
           "Why? Screw-press counter-pressure set low and stockpile rained on"],
      category="Material", prevent="Shift cake-moisture test; covered stockpile"),
    K("KB-0423", ["Machine"], ["quality", "wear", "die"],
      "Briquettes crumbly and low density", "Worn screw tip and die sleeve from sand in digestate solids",
      "Hard-faced screw tip, replaced die sleeve, set 250 h wear check",
      why=["Why crumbly? Low compaction pressure",
           "Why? Screw flight worn 6 mm at the tip",
           "Why so fast? High sand in solids from press mud; no wear measurement in PM"],
      category="Material", prevent="250 h screw / die wear measurement; grit control upstream"),
    K("KB-0426", ["Machine"], ["weight", "calibration"],
      "Bags of organic manure under-weight", "Weigher zero drift from material build-up on the weigh hopper",
      "Cleaned weigh hopper, re-zeroed and span-calibrated with test weights",
      why=["Why under-weight? Weigher read 0.6 kg high",
           "Why? Caked manure on the hopper added weight at zero",
           "Why? No shift cleaning or zero check"],
      category="Measurement", prevent="Shift-start zero check; monthly calibration with test weights"),
]
