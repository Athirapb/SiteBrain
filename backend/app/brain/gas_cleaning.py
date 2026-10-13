"""Gas cleaning & upgrading in the Biogas Upgradation Unit (BUU): H2S Scrubber Vessel (dry-media adsorber), Gas
Filtration Skid (particulate / coalescing elements + secondary guard filter), Chiller (gas dehumidification to a
2–5 °C dew point, condensate separator with auto-drain, Chiller Pumps 1/2) and the Membrane Upgrader (multi-stage
hollow-fibre CH4/CO2 separation with tail-gas recycle and an activated-carbon guard bed).

Gas train: Digesters → H2S Scrubber → Gas Filtration Skid → Gas Blowers → LP Compressors → Chiller → Membrane →
HP compressors → CBG cascade; off-spec / tail gas to flare or recycle.

Sources (types): membrane OEM product literature and operating guidance (Evonik SEPURAN Green — polyimide hollow
fibre, three-stage process, feed pre-treatment for water / oil / VOC; Air Liquide and DMT/Pentair upgrading skid
manuals), IEA Bioenergy Task 37 biogas upgrading and pre-treatment reviews, iron-oxide / impregnated-carbon H2S media
supplier data (iron-sponge basics, SulfaTreat-type media: sulfur loading, moisture needs, exothermic / pyrophoric
regeneration, 2–3 % air dosing effects), compressed-air / gas filtration element OEM manuals (dP change-out limits,
coalescer drains), refrigeration-dryer service guides (condenser fouling, drain traps, refrigerant charge, icing),
Bureau of Indian Standards IS 16087:2016 (CBG: CH4 ≥ 90 %, CO2 ≤ 4 % for cylinder filling, CO2+N2+O2 ≤ 10 %,
H2S ≤ 30.3 mg/m³, moisture ≤ 16 mg/m³), PNGRB CBG injection guidance, published RCA papers, plant incident
history (incident_log_gas_cleaning.csv) and SOP-SCR-02 / SOP-CHL-01 / SOP-BUU-01.
The plant runs a tighter internal product target of CH4 > 95 % (interlock MEM-01).
"""
from .dsl import B, C, K, Q, R, W

TREES = {}

# ─────────────────────────────────────────────────────────────── H2S Scrubber Vessel ──
TREES["Scrubber"] = {
    "causes": [
        C("mesh", "Top distributor mesh misaligned with perimeter seal gap — bed channeling", "Machine",
          ["mesh", "seal gap", "channel"], [
            "Keep the downstream filter bypass valve locked CLOSED (SCR-01)",
            "Depressurise, isolate with spectacle blinds and purge the vessel with N2; issue a confined-space permit",
            "Keep spent media wet while it is exposed — it can self-heat in air (pyrophoric iron sulfide)",
            "Re-seat and level the media; re-align the top distributor mesh to 100% perimeter contact",
            "Fit a new perimeter seal strip and torque mesh fasteners to 25 N·m in a star pattern",
            "Flush the filter skid, pressure-test, then verify dP 0.04–0.06 bar and outlet H2S < 10 ppm before release"],
          why=W("Why did the mesh lose its seal against the vessel wall?", [
              B("It was re-fitted badly after the last media change", W("Why was it not fitted right?", [
                  B("No torque value or seal check in the work pack", R(
                      "Media change-out procedure has no mesh-alignment / perimeter-seal acceptance check", "Method",
                      prevent=["Add a signed mesh-contact and 25 N·m torque check to SOP-SCR-02",
                               "Photograph the mesh perimeter before closing the manway and attach to the work order"])),
                  B("Contractor crew unfamiliar with this vessel", R(
                      "Media change-outs done by contract crews without vessel-specific briefing", "Man",
                      prevent=["Brief contractors on SOP-SCR-02 and have plant fitter witness mesh fitting",
                               "Keep a vessel internals drawing and checklist at the manway"])),
              ])),
              B("Seal strip perished or fasteners corroded", R(
                  "Perimeter seal and fasteners are not replaced as a kit at each media change", "Material",
                  prevent=["Replace the perimeter seal strip and stainless fasteners every media change",
                           "Specify H2S-resistant seal material (EPDM/Viton) and 316 SS fasteners"])),
              B("Bed settled or was lifted by a pressure surge", R(
                  "Fast depressurisation / start-up surges disturb the bed; no ramp limit", "Method",
                  prevent=["Limit pressurisation and venting to slow ramps through a restriction orifice",
                           "Top up and level the bed 1 month after a fresh charge (settling check)"])),
          ], how="With the vessel purged and permitted, look along the mesh edge with a torch: daylight or a finger gap "
                 "at the wall, or media heaped on one side, means channeling."),
          case="KB-0702"),
        C("choke", "Media caking from moisture and elemental sulfur (high dP)", "Material",
          ["differential", "caking", "choke"], [
            "Reduce gas flow to 50% and confirm the dP trend for 30 minutes",
            "Back-flush the bed with dry N2 at 0.5 bar for 20 minutes per SOP-SCR-02",
            "Under permit, vacuum out and replace the caked top 150 mm of media (keep spent media wet)",
            "Drain the upstream moisture knock-out pot and restore its auto-drain"],
          why=W("Where did the water / sulfur that caked the bed come from?", [
              B("Free water from the gas line reached the bed", W("Why did water get past the knock-out?", [
                  B("Knock-out pot drain blocked or not drained", R(
                      "Knock-out pot draining is manual and not on shift rounds", "Method",
                      prevent=["Fit an auto-drain with level alarm on the knock-out pot",
                               "Add knock-out pot draining to every shift round with a tick-sheet"])),
                  B("Warm, saturated gas cools in an unlagged line", R(
                      "Gas line to the scrubber has no fall to drain points and is not insulated", "Environment",
                      prevent=["Insulate the digester-to-scrubber gas line and add low-point drains",
                               "Check line slope and drain legs during the annual shutdown"])),
              ])),
              B("Too much air dosed — sulfur deposited in the bed", R(
                  "Air / O2 dosing not controlled to outlet O2; elemental sulfur builds up", "Method",
                  prevent=["Control air dosing on outlet O2 (target 0.3–0.5%) with a high-O2 alarm",
                           "Record dosing rate each shift and trend against bed dP"])),
              B("Media grade wrong for wet gas", R(
                  "Media purchased on price without a moisture / crush-strength spec", "Material",
                  prevent=["Specify media moisture tolerance and crush strength in the purchase spec",
                           "Ask the supplier for a datasheet and test certificate with each lot"])),
          ], how="When the top layer is removed, look for lumps that don't break between the fingers (wearing gloves) "
                 "and yellow sulfur crust — that is caking, not just fines."),
          case="KB-0703"),
        C("exhaust", "Media exhausted — H2S breakthrough", "Method", ["breakthrough", "exhaust"], [
            "Switch to the standby vessel or reduce gas flow; wear an H2S personal monitor (SCR-02)",
            "Confirm outlet H2S with a Dräger tube and log the reading",
            "Replace the media charge; keep spent media wet and dispose of it per SOP (pyrophoric)",
            "Restart and confirm outlet H2S < 10 ppm before full flow"],
          why=W("Why was the media used beyond its capacity?", [
              B("Change-out is on a calendar, not on sulfur loading", W("Why is sulfur loading not tracked?", [
                  B("Nobody calculates kg of sulfur removed", R(
                      "No sulfur-loading log (gas flow × inlet H2S) against media capacity", "Method",
                      prevent=["Log daily sulfur load (Nm³ × ppm) and forecast the change-out date",
                               "Trigger media ordering at 70% of rated sulfur capacity"])),
                  B("Outlet H2S trend not reviewed", R(
                      "Outlet H2S alarm set too high and trend not reviewed in the daily meeting", "Man",
                      prevent=["Set an outlet H2S pre-alarm at 10 ppm and review the trend daily",
                               "Make the shift engineer sign off the H2S trend each day"])),
              ])),
              B("Replacement media was not in stock", R(
                  "No minimum stock / lead-time plan for scrubber media", "Method",
                  prevent=["Keep one full media charge in stock", "Set a re-order point based on supplier lead time"])),
          ], how="Compare the date and size of the last charge with gas flow × inlet H2S since then."),
          case="KB-0704"),
        C("load", "Inlet H2S load above bed design (feedstock or digester upset)", "Material",
          ["inlet h2s", "feedstock", "load"], [
            "Reduce gas flow through the bed or put both vessels in series if piped for it",
            "Tell the feeding team: hold sulfur-rich feed (press mud, poultry, protein waste) until H2S falls",
            "Increase in-digester biological desulfurisation (air or FeCl3 dosing) within the O2 limit",
            "Plan an earlier media change-out — capacity is being used faster"],
          why=W("Why is the raw gas carrying more H2S than the bed is designed for?", [
              B("Feed recipe changed to sulfur-rich feedstock", R(
                  "Feedstock changes are not reviewed for sulfur impact on the gas train", "Material",
                  prevent=["Add a sulfur / protein check to feedstock acceptance",
                           "Agree a maximum sulfur-rich feed fraction with the BUU team"])),
              B("In-digester desulfurisation stopped", W("Why did digester desulfurisation stop?", [
                  B("FeCl3 dosing pump empty or failed", R(
                      "FeCl3 dosing pump and tank level not on daily rounds", "Machine",
                      prevent=["Add dosing pump stroke and tank level to the daily round",
                               "Alarm low FeCl3 tank level in SCADA"])),
                  B("Digester air dosing turned off", R(
                      "Digester air dosing changed without management-of-change", "Man",
                      prevent=["Make air-dosing setpoint changes a MOC item logged in the shift book"])),
              ])),
          ], how="Check the raw-gas H2S trend on the digester gas analyser and the feed log for the last week."),
          case="KB-0707"),
        C("air", "Air / O2 dosing wrong — bed overheating or poor regeneration", "Man",
          ["oxygen", "o2", "air dosing", "hot"], [
            "Reset air dosing to the setpoint that gives 0.3–0.5% O2 at the scrubber outlet",
            "If the shell has a hot spot: stop air dosing, keep gas flowing, monitor shell temperature; never open the vessel hot",
            "Check outlet O2 stays below 1% (membrane and CBG O2 limit)",
            "Record the dosing setpoint and outlet O2 in the shift log"],
          why=W("Why was the air dosing wrong?", [
              B("Operator changed the rotameter setting", W("Why was it changed?", [
                  B("Tried to stretch media life", R(
                      "No written air-dosing range or reason for it in the operating procedure", "Method",
                      prevent=["Write the air-dosing range and outlet O2 target into SOP-BUU-01",
                               "Train operators on why too much O2 heats the bed and spoils CBG"])),
                  B("Nobody knew the right setting", R(
                      "Shift handover does not include dosing setpoints", "Man",
                      prevent=["Add dosing setpoint and outlet O2 to the handover sheet"])),
              ])),
              B("Air blower / rotameter faulty", R(
                  "Air dosing rotameter and blower have no PM or calibration", "Machine",
                  prevent=["Add rotameter cleaning and blower check to monthly PM",
                           "Interlock air dosing off when gas flow is zero"])),
          ], how="Read the air rotameter and outlet O2 analyser; feel or IR-scan the shell for warm patches."),
          case="KB-0708"),
        C("meas", "H2S analyser fault — false outlet reading", "Measurement",
          ["analyser", "analyzer", "reading", "calibration"], [
            "Take a Dräger tube sample at the outlet sample point and compare with the analyser",
            "Check the sample line for condensate, the sample pump and the filter; drain the line",
            "Calibrate the analyser with certified span gas; replace the sensor cell if it fails",
            "Log the corrected reading and close out any false alarm"],
          why=W("Why is the analyser reading wrong?", [
              B("Sensor cell aged or calibration overdue", R(
                  "Analyser calibration and cell replacement not in the PM plan", "Measurement",
                  prevent=["Monthly span-gas calibration logged in the PM system",
                           "Replace electrochemical H2S cells at the OEM interval (≈ 12–24 months)"])),
              B("Water in the sample line", R(
                  "Sample line has no condensate pot or heating", "Machine",
                  prevent=["Fit a sample-line condensate pot and Peltier cooler / drain",
                           "Add sample-line drain to the weekly round"])),
              B("Span gas expired or wrong concentration", R(
                  "Calibration gas stock not controlled", "Material",
                  prevent=["Keep span gas certificates and expiry dates in the calibration register"])),
          ], how="Compare analyser reading with a fresh tube reading taken within 5 minutes."),
          case="KB-0709"),
    ],
    "questions": [
        Q("mesh", "Primary checkpoint: with a permit and gas test, look at the top distributor mesh through the top "
                  "manway. How does it sit against the vessel wall?", [
            ("100% perimeter contact, fasteners torqued",
             {"mesh": 0.15, "choke": 1.2, "exhaust": 1.2, "load": 1.2, "air": 1.2, "meas": 1.2}),
            ("Perimeter seal gap observed",
             {"mesh": 4.0, "choke": 0.7, "exhaust": 0.7, "load": 0.7, "air": 0.7, "meas": 0.7}, ["channeling"]),
            ("Mesh displaced / torn",
             {"mesh": 4.5, "choke": 0.7, "exhaust": 0.6, "load": 0.6, "air": 0.7, "meas": 0.6}, ["channeling", "particles"]),
            ("Mesh fine but caked crust underneath",
             {"mesh": 0.4, "choke": 3.5, "exhaust": 0.8, "load": 0.9, "air": 1.4, "meas": 0.6}),
        ], ["mesh", "seal gap", "channel", "differential"],
          how="Only under a confined-space / vessel-entry permit: depressurise, purge with N2 to < 10% LEL and O2 > 19.5%, "
              "wear an H2S personal monitor, keep a standby attendant. Look from the manway — do not enter for this check. "
              "Keep exposed media damp: spent iron media can heat up and smoulder in air.",
          purpose="A gap at the mesh edge lets gas run down the wall and skip the media — that's channeling."),
        Q("dp", "How has the scrubber differential pressure (dP) behaved over the last shift?", [
            ("Sudden drop", {"mesh": 3.0, "choke": 0.4, "exhaust": 0.9, "load": 0.9, "air": 0.8, "meas": 1.0}, ["channeling"]),
            ("Steady climb", {"mesh": 0.5, "choke": 3.5, "exhaust": 1.0, "load": 1.0, "air": 1.6, "meas": 1.0}),
            ("Stable", {"mesh": 0.5, "choke": 0.4, "exhaust": 1.4, "load": 1.4, "air": 1.0, "meas": 1.4}),
        ], ["differential", "pressure"], {"tag": "differential_pressure_dp", "option": 2, "above": 0.09},
          how="Read the dP transmitter trend on SCADA (normal about 0.05 bar) or the local dP gauge across the vessel.",
          purpose="A climbing dP means the bed is plugging; a sudden drop means gas has found a short-cut."),
        Q("carry", "Open the filter skid drain or downstream strainer (with permit). Any media granules or black powder?", [
            ("None", {"mesh": 0.6, "choke": 1.1, "exhaust": 1.2, "load": 1.2, "air": 1.1, "meas": 1.2}),
            ("Granules / black powder present",
             {"mesh": 3.0, "choke": 1.2, "exhaust": 0.7, "load": 0.6, "air": 0.8, "meas": 0.5}, ["particles"]),
        ], ["carryover", "particles", "mesh"],
          how="Isolate and depressurise the filter housing drain first, test for H2S at the drain, then open slowly into "
              "a bucket. Black powder can be pyrophoric — keep it wet and don't leave it on the floor.",
          purpose="Media granules downstream prove the bed is bypassing or breaking up and can wreck the compressors."),
        Q("h2s", "What does the outlet H2S analyser (or a tube sample) read?", [
            ("< 10 ppm", {"mesh": 1.0, "choke": 1.2, "exhaust": 0.2, "load": 0.4, "air": 1.0, "meas": 1.0}),
            ("10–100 ppm", {"mesh": 1.5, "choke": 1.0, "exhaust": 2.0, "load": 2.0, "air": 1.2, "meas": 1.3},
             ["h2s_breakthrough"]),
            ("> 100 ppm", {"mesh": 1.2, "choke": 0.8, "exhaust": 3.0, "load": 2.2, "air": 1.0, "meas": 1.3},
             ["h2s_breakthrough"]),
        ], ["breakthrough", "h2s"], {"tag": "h2s_outlet_ppm", "option": 0, "above": 30},
          how="Read the outlet analyser on SCADA. For a tube sample, wear your H2S monitor, purge the sample point for "
              "10 seconds and draw the tube per its instructions.",
          purpose="Outlet H2S tells me whether the media is still doing its job."),
        Q("inlet", "What is the raw-gas H2S coming into the scrubber, compared with the bed design (about 2,000 ppm)?", [
            ("Within design, steady", {"load": 0.2, "exhaust": 1.1, "mesh": 1.1, "choke": 1.1, "air": 1.1, "meas": 1.1}),
            ("Well above design or rising this week",
             {"load": 4.0, "exhaust": 1.4, "mesh": 0.7, "choke": 0.9, "air": 0.7, "meas": 0.7}),
        ], ["inlet h2s", "feedstock", "load"],
          how="Read the digester gas analyser (raw gas H2S) on SCADA and look at the last 7 days' trend; ask the feeding "
              "team if press mud or protein-rich waste was added.",
          purpose="A higher inlet load uses up the media much faster than planned."),
        Q("tube", "Take a quick Dräger tube sample at the outlet and compare it with the analyser. Do they match?", [
            ("Tube matches the analyser", {"meas": 0.15, "mesh": 1.1, "choke": 1.1, "exhaust": 1.1, "load": 1.1, "air": 1.1}),
            ("Tube is much lower than the analyser",
             {"meas": 4.0, "mesh": 0.7, "choke": 0.8, "exhaust": 0.5, "load": 0.6, "air": 0.8}),
            ("Tube is much higher than the analyser",
             {"meas": 3.5, "mesh": 1.0, "choke": 0.7, "exhaust": 1.2, "load": 1.0, "air": 0.8}, ["h2s_breakthrough"]),
        ], ["analyser", "analyzer", "reading", "calibration", "breakthrough"],
          how="Wear your H2S personal monitor. Purge the sample point for 10 s, use the correct range tube and pump strokes, "
              "and read the stain length straight away.",
          purpose="A second, independent reading tells me if the analyser itself is wrong."),
        Q("air", "Check the air / O2 dosing: rotameter setting and outlet O2 reading?", [
            ("At setpoint, outlet O2 0.3–0.5%", {"air": 0.2, "mesh": 1.1, "choke": 1.0, "exhaust": 1.1, "load": 1.1, "meas": 1.1}),
            ("Dosing off or very low", {"air": 3.0, "exhaust": 1.6, "load": 1.2, "choke": 0.6, "mesh": 0.7, "meas": 0.8}),
            ("Higher than setpoint, O2 above 1%", {"air": 3.5, "choke": 1.6, "exhaust": 0.7, "mesh": 0.7, "load": 0.7, "meas": 0.8}),
        ], ["oxygen", "o2", "air dosing"],
          how="Read the rotameter at the air dosing panel and the O2 value on the outlet analyser. Don't change the "
              "setting yourself without the shift engineer.",
          purpose="Some air helps regenerate the media; too much heats the bed, deposits sulfur and spoils CBG."),
        Q("life", "When was the media last changed, compared with the planned change-out?", [
            ("Recently, well within its life", {"exhaust": 0.2, "mesh": 1.2, "choke": 1.0, "load": 1.2, "air": 1.0, "meas": 1.2}),
            ("Past the planned date / not tracked", {"exhaust": 4.0, "mesh": 0.7, "choke": 1.1, "load": 1.0, "air": 1.0, "meas": 0.7}),
        ], ["breakthrough", "exhaust", "media"],
          how="Check the media change-out log or the work order history for this vessel.",
          purpose="Media has a fixed sulfur capacity — once it's full, H2S breaks through."),
        Q("knock", "Drain the upstream moisture knock-out pot. How much water comes out?", [
            ("A little, as usual", {"choke": 0.4, "mesh": 1.1, "exhaust": 1.1, "load": 1.1, "air": 1.1, "meas": 1.1}),
            ("A lot — the pot was full", {"choke": 3.5, "mesh": 0.8, "exhaust": 0.8, "load": 0.9, "air": 0.8, "meas": 0.8}),
        ], ["differential", "caking", "choke", "moisture"],
          how="Wear your H2S monitor, open the drain valve slowly into a bucket and close it as soon as gas appears.",
          purpose="Free water reaching the bed is the main reason dry media cakes and blocks."),
        Q("shell", "Feel the scrubber shell with the back of your hand, or use an IR gun. How warm is it?", [
            ("Even, close to gas temperature", {"air": 0.4, "mesh": 1.1, "choke": 1.0, "exhaust": 1.1, "load": 1.1, "meas": 1.1}),
            ("A hot spot or much warmer than usual", {"air": 3.5, "choke": 1.5, "mesh": 0.8, "exhaust": 0.8, "load": 1.0, "meas": 0.6}),
        ], ["hot", "temperature", "oxygen"],
          how="Scan the shell from top to bottom with an IR thermometer. If any area is above 60 °C, step back, "
              "tell the shift engineer and don't open the vessel.",
          purpose="A hot spot means the media is reacting with too much oxygen — a fire risk."),
    ],
}

# ─────────────────────────────────────────────────────────────── Gas Filtration Skid ──
TREES["Filter"] = {
    "causes": [
        C("element", "Filter element loaded with fines — high dP", "Material", ["element dp", "loaded", "fines"], [
            "Change over to the standby housing (keep the secondary guard filter active)",
            "Replace the loaded element; check it for tears and note what it is loaded with",
            "Trace the fines source upstream — scrubber media carryover or pipe scale"],
          why=W("Where are the fines loading the element coming from?", [
              B("Scrubber media breaking up / carryover", W("Why is the scrubber shedding fines?", [
                  B("Fines not screened at media charging", R(
                      "New media charged without screening out fines", "Method",
                      prevent=["Screen or blow-down new media before start-up per SOP-SCR-02",
                               "Run the filter skid on the standby element for the first week after a media change"])),
                  B("Bed disturbed by pressure surges", R(
                      "No ramp limit on scrubber pressurisation", "Method",
                      prevent=["Pressurise and vent the scrubber slowly through a restriction orifice"])),
              ])),
              B("Rust and scale from carbon-steel gas pipe", R(
                  "Wet H2S-laden gas corrodes carbon-steel pipework upstream", "Material",
                  prevent=["Replace corroded runs with SS or HDPE", "Improve moisture removal before the skid"])),
              B("Elements changed only when they block", R(
                  "No dP-based change-out limit in PM", "Method",
                  prevent=["Change elements at 0.2 bar dP or OEM interval, whichever comes first",
                           "Trend element dP daily and alarm at 0.18 bar"])),
          ], how="Look at the removed element: black granules = scrubber media; brown flakes = pipe scale."),
          case="KB-0705"),
        C("rupture", "Filter element ruptured or collapsed — particles passing downstream", "Machine",
          ["rupture", "particles", "collapsed"], [
            "Trip the LP compressor load line (CMP-01) until downstream is clean",
            "Replace the element and the housing O-ring; inspect the support core",
            "Inspect and clean the compressor suction strainers",
            "Find out why dP went so high before it ruptured"],
          why=W("Why did the element rupture?", [
              B("dP went far past the change-out limit", W("Why was the high dP not acted on?", [
                  B("No alarm on element dP", R(
                      "Element dP not alarmed or trended in SCADA", "Measurement",
                      prevent=["Add a high dP alarm (0.18 bar) and a high-high (0.30 bar) to SCADA"])),
                  B("Alarm seen but change-out postponed", R(
                      "No spare elements in stock, so change-out was deferred", "Method",
                      prevent=["Keep two spare element sets in stock", "Set a re-order point on element stock"])),
              ])),
              B("Pressure surge / reverse flow at start-up", R(
                  "Valves opened fast at start-up, slamming the element", "Man",
                  prevent=["Write a slow-open start-up sequence for the skid and train operators",
                           "Fit a non-return valve if reverse flow is possible"])),
              B("Wrong or poor-quality element fitted", R(
                  "Non-OEM elements without collapse-pressure rating bought", "Material",
                  prevent=["Buy only elements with rated collapse dP ≥ 5 bar and OEM part number"])),
          ], how="Check the old element: split pleats or a crushed core mean overload; a pulled-off end cap means a surge."),
          case="KB-0710"),
        C("bypass", "Bypass left open after maintenance or used without a permit", "Man", ["bypass"], [
            "Close the bypass valve and verify it on the position indicator",
            "Lock it closed and update the LOTO / valve register",
            "Check downstream strainers for particles let through during the bypass window",
            "Review the bypass permit procedure with the shift crew"],
          why=W("Why was the bypass left open?", [
              B("Opened for an element change and forgotten", W("Why was it not closed afterwards?", [
                  B("No valve line-up check at the end of the job", R(
                      "Element change-out procedure has no 'bypass closed and locked' sign-off", "Method",
                      prevent=["Add a bypass closed / locked sign-off to the change-out work order",
                               "Fit a limit switch on the bypass valve with a SCADA alarm when open"])),
                  B("Shift changed mid-job", R(
                      "Handover does not list open bypasses", "Man",
                      prevent=["List all open bypasses on the handover sheet and in the bypass register"])),
              ])),
              B("Opened to beat high dP and keep gas flowing", R(
                  "Bypass used as a workaround for high dP instead of changing elements", "Method",
                  prevent=["Make bypassing a permit item, allowed only with the secondary guard filter active (FLT-02)",
                           "Fix the root of high dP (fines source, element stock)"])),
          ], how="Ask the last shift and check the work orders and bypass register."),
          case="KB-0711"),
        C("liquid", "Condensate / liquid loading the elements (wet gas)", "Environment",
          ["condensate", "wet", "liquid", "drain"], [
            "Drain the filter housing and the upstream low points",
            "Replace wetted elements — wet media blinds and swells",
            "Check the housing auto-drain / drain trap works",
            "Check for cold spots: lag and trace the line if it's cold weather"],
          why=W("Why is liquid reaching the filter?", [
              B("Gas cools in the line and water condenses", R(
                  "Uninsulated gas line in cold / monsoon weather with no drain points", "Environment",
                  prevent=["Insulate the gas line and add low-point drain pots before the skid",
                           "Add drain checks to the monsoon / winter round"])),
              B("Housing drain trap stuck", R(
                  "Filter housing drain trap not on PM", "Machine",
                  prevent=["Clean and test the housing drain trap monthly"])),
              B("Knock-out pot upstream not drained", R(
                  "Knock-out pot draining is manual and missed", "Man",
                  prevent=["Fit an auto-drain with level alarm on the knock-out pot"])),
          ], how="Open the housing drain into a bucket and look at what comes out and how much."),
          case="KB-0712"),
        C("install", "Element wrongly fitted after change-out (unseated, missing O-ring, wrong grade)", "Method",
          ["change-out", "installed", "o-ring", "grade"], [
            "Isolate the housing, depressurise and open it",
            "Re-seat the element with a new O-ring; check the part number and micron rating",
            "Leak-test the housing and confirm dP rises to the normal clean value (≈ 0.05–0.08 bar)",
            "Check downstream strainers for particles"],
          why=W("Why was the element fitted wrong?", [
              B("No change-out procedure at the skid", R(
                  "No step-by-step element change-out SOP or torque values", "Method",
                  prevent=["Write the element change-out SOP (OEM_Gas_Filtration_Skid_Maintenance) and post it at the skid",
                           "Require a second-person check of seating and O-ring"])),
              B("Wrong element in stores", R(
                  "Stores issue elements by size, not OEM part number / micron rating", "Material",
                  prevent=["Label stores bins with OEM part number and micron rating",
                           "Check the part number at issue and before fitting"])),
          ], how="Look at the work order for the last change-out and compare the fitted part number with the OEM list."),
          case=None),
        C("gauge", "Element dP gauge / transmitter fault — false reading", "Measurement",
          ["gauge", "transmitter", "reading"], [
            "Compare the local dP gauge with the SCADA value",
            "Blow down / drain the dP impulse lines; check they are not blocked or wet",
            "Zero and calibrate the dP transmitter",
            "Replace the gauge if it sticks"],
          why=W("Why is the dP reading wrong?", [
              B("Impulse lines full of water or dirt", R(
                  "Impulse lines have no drain pots and are not blown down", "Machine",
                  prevent=["Fit drain pots on dP impulse lines and blow down monthly"])),
              B("Transmitter out of calibration", R(
                  "dP transmitter not in the calibration plan", "Measurement",
                  prevent=["Add the filter dP transmitter to the 6-monthly calibration plan"])),
          ], how="Equalise the transmitter with its manifold valve: it should read zero."),
          case=None),
    ],
    "questions": [
        Q("dptrend", "How has the element dP behaved over the last 24 hours?", [
            ("Rising steadily", {"element": 3.0, "rupture": 0.6, "bypass": 0.7, "liquid": 1.8, "install": 0.5, "gauge": 0.9}),
            ("Rose then suddenly dropped",
             {"element": 0.6, "rupture": 4.0, "bypass": 1.0, "liquid": 0.7, "install": 0.7, "gauge": 0.8}, ["particles"]),
            ("Flat / near zero", {"element": 0.3, "rupture": 1.3, "bypass": 2.5, "liquid": 0.6, "install": 2.5, "gauge": 1.6}),
            ("Steady at the usual value", {"element": 0.4, "rupture": 0.6, "bypass": 0.7, "liquid": 0.7, "install": 0.7, "gauge": 1.4}),
        ], ["element dp", "pressure"], {"tag": "element_dp_bar", "option": 3, "above": 0.15},
          how="Read the element dP on SCADA (normal ≈ 0.08 bar for clean-ish elements) or the local dP gauge on the skid.",
          purpose="The dP shape tells loading, rupture and bypass apart."),
        Q("valve", "Check the bypass valve: what do the position indicator and lock show?", [
            ("Closed and locked", {"element": 1.2, "rupture": 1.2, "bypass": 0.15, "liquid": 1.2, "install": 1.2, "gauge": 1.2}),
            ("Open / unlocked", {"element": 0.8, "rupture": 0.8, "bypass": 4.0, "liquid": 0.8, "install": 0.8, "gauge": 0.8},
             ["bypass_open"]),
        ], ["bypass"],
          how="Walk to the skid and look at the bypass valve handle, position indicator and padlock. Don't operate it — "
              "just report what you see.",
          purpose="An open bypass sends unfiltered gas straight to the compressors."),
        Q("guard", "Is the secondary guard filter in service (valves lined up, its dP showing flow)?", [
            ("In service", {"element": 1.0, "rupture": 0.9, "bypass": 0.9, "liquid": 1.0, "install": 1.0, "gauge": 1.0}),
            ("Isolated / not in service", {"element": 1.0, "rupture": 1.2, "bypass": 1.6, "liquid": 1.0, "install": 1.1, "gauge": 1.0},
             ["guard_inactive"]),
        ], ["bypass", "guard"],
          how="Check the guard filter inlet and outlet valves are open and its dP gauge shows a small positive reading.",
          purpose="The guard filter is the last line of protection if the main element or bypass lets particles through."),
        Q("down", "Inspect the downstream (compressor suction) strainer. Any particles?", [
            ("Clean", {"element": 1.3, "rupture": 0.2, "bypass": 0.6, "liquid": 1.1, "install": 0.5, "gauge": 1.3}),
            ("Particles present", {"element": 0.7, "rupture": 3.0, "bypass": 2.0, "liquid": 0.8, "install": 2.0, "gauge": 0.6},
             ["particles"]),
        ], ["particles", "rupture"],
          how="Only with the LP compressor stopped and the strainer isolated, depressurised and gas-tested. Wear your H2S "
              "monitor and gloves; keep any black powder wet.",
          purpose="Particles after the filter prove something is getting past it."),
        Q("drain", "Open the filter housing drain into a bucket. What comes out?", [
            ("Dry, or a few drops", {"liquid": 0.2, "element": 1.1, "rupture": 1.1, "bypass": 1.1, "install": 1.1, "gauge": 1.1}),
            ("A lot of water / condensate", {"liquid": 4.0, "element": 1.1, "rupture": 0.8, "bypass": 0.7, "install": 0.7, "gauge": 0.9}),
        ], ["condensate", "wet", "drain", "liquid"],
          how="Wear your H2S monitor. Crack the drain valve slowly, stand upwind and close it as soon as gas comes out.",
          purpose="Water soaks the elements, blinds them and pushes dP up."),
        Q("local", "Compare the local dP gauge on the skid with the SCADA dP. Do they agree?", [
            ("They agree", {"gauge": 0.15, "element": 1.1, "rupture": 1.1, "bypass": 1.1, "liquid": 1.1, "install": 1.1}),
            ("They disagree, or the gauge is stuck", {"gauge": 4.5, "element": 0.6, "rupture": 0.7, "bypass": 0.8, "liquid": 0.8, "install": 0.8}),
        ], ["gauge", "transmitter", "reading"],
          how="Read the local gauge and ask the control room for the SCADA value at the same moment.",
          purpose="If the two readings disagree, the problem may be the instrument, not the filter."),
        Q("element", "How did the removed element look at the last change-out (or now, under permit)?", [
            ("Evenly loaded, intact", {"element": 2.2, "rupture": 0.3, "bypass": 1.0, "liquid": 0.7, "install": 0.4, "gauge": 1.0}),
            ("Torn, collapsed or holed", {"rupture": 4.0, "element": 0.8, "bypass": 0.7, "liquid": 0.8, "install": 1.0, "gauge": 0.7},
             ["particles"]),
            ("Wet, swollen or oily", {"liquid": 4.0, "element": 1.0, "rupture": 0.8, "bypass": 0.7, "install": 0.7, "gauge": 0.8}),
            ("Unseated, O-ring missing or wrong part", {"install": 4.5, "rupture": 1.0, "element": 0.6, "bypass": 0.8, "liquid": 0.7, "gauge": 0.7}),
        ], ["element dp", "rupture", "change-out", "o-ring"],
          how="Isolate both housing valves, depressurise to flare, gas-test, then open the housing. Bag the old element "
              "wet — it may hold pyrophoric scrubber fines.",
          purpose="The element itself shows whether it was overloaded, burst, soaked or fitted wrong."),
        Q("recent", "Was any work done on this skid (element change, valve work) in the last few days?", [
            ("No work recently", {"install": 0.2, "bypass": 0.5, "element": 1.2, "rupture": 1.1, "liquid": 1.2, "gauge": 1.1}),
            ("Yes, elements just changed", {"install": 3.5, "bypass": 2.2, "element": 0.5, "rupture": 0.9, "liquid": 0.8, "gauge": 0.9}),
        ], ["change-out", "bypass", "installed"],
          how="Check the work-order history and the shift log, or ask the maintenance supervisor.",
          purpose="Most bypass and fitting mistakes happen right after maintenance."),
    ],
}

# ─────────────────────────────────────────────────────────────────────────── Chiller ──
TREES["Chiller"] = {
    "causes": [
        C("filter", "Condenser-side filter / coil choked with dust — poor heat rejection", "Environment",
          ["filter", "condenser", "dust"], [
            "Clean the condenser-side filter and blow the coil clean (low-pressure air or water, power isolated)",
            "Check the condenser fan runs and refrigerant suction / discharge pressures",
            "Confirm gas outlet temperature returns to 2–5 °C",
            "Set a weekly filter-cleaning task (daily in dusty season)"],
          why=W("Why did the condenser filter choke?", [
              B("Dusty air from roads / feed hall near the chiller", W("Why does so much dust reach it?", [
                  B("Chiller sits downwind of the feed yard / unpaved road", R(
                      "Chiller located without dust protection near feedstock handling", "Environment",
                      prevent=["Fit a pre-filter screen or shelter on the air intake side",
                               "Water-spray or pave the access road; move bale handling away"])),
                  B("Dust season not planned for", R(
                      "Filter cleaning frequency is fixed, not adjusted for season", "Method",
                      prevent=["Increase cleaning to daily in dry / harvest season",
                               "Trend condenser discharge pressure and clean on rise"])),
              ])),
              B("Cleaning task skipped", R(
                  "Filter cleaning not on the PM schedule or rounds", "Man",
                  prevent=["Put weekly condenser filter cleaning on the PM schedule with sign-off"])),
          ], how="Look at the filter and coil fins: matted dust or fibres across the face means poor airflow."),
          case="KB-0637"),
        C("drain", "Condensate auto-drain stuck — water carryover", "Machine",
          ["auto-drain", "carryover", "separator"], [
            "Halt feed to the membranes (interlock CHL-01)",
            "Drain the separator manually; strip, clean or replace the auto-drain trap",
            "Check the drain line downstream of the trap is clear",
            "Verify dew point back within 2–5 °C and drain cycling before releasing the interlock"],
          why=W("Why did the auto-drain stop working?", [
              B("Trap blocked with sludge / sulfur / scale", W("Why is dirt reaching the trap?", [
                  B("No strainer before the trap", R(
                      "Auto-drain has no Y-strainer and is not cleaned in PM", "Machine",
                      prevent=["Fit a Y-strainer ahead of the trap and clean it monthly",
                               "Add drain-trap strip-and-clean to quarterly PM"])),
                  B("Fines from upstream scrubber / filter", R(
                      "Upstream filtration lets fines into the gas train", "Material",
                      prevent=["Fix upstream fines source (see Filter tree)"])),
              ])),
              B("Solenoid / timer drain failed electrically", R(
                  "No alarm when the drain stops cycling", "Measurement",
                  prevent=["Alarm in SCADA when drain cycles drop below 2 per hour",
                           "Fit a high-level switch in the separator"])),
              B("Drain manual isolation left closed", R(
                  "No valve line-up check after drain maintenance", "Man",
                  prevent=["Add drain isolation valve position to the restart checklist"])),
          ], how="Strip the trap: sludge or sulfur in it points to dirt; a clean trap that won't open points to the solenoid."),
          case="KB-0706"),
        C("refrig", "Low refrigerant charge (leak) or refrigeration compressor fault", "Machine",
          ["refrigerant", "sight glass", "leak"], [
            "Check refrigerant suction / discharge pressures and the sight glass",
            "Have a certified refrigeration technician leak-test (electronic detector / soap) and repair",
            "Evacuate and recharge to the nameplate charge",
            "Check refrigeration compressor oil level and current"],
          why=W("Why did the refrigerant charge drop?", [
              B("Leak at a flare joint / brazed joint", W("Why did the joint leak?", [
                  B("Vibration fatigue on unsupported pipe", R(
                      "Refrigerant pipework not clamped against vibration", "Machine",
                      prevent=["Clamp and support refrigerant lines; add vibration loops"])),
                  B("Corrosion from H2S in the air", R(
                      "Copper / brass parts exposed to H2S-laden air", "Environment",
                      prevent=["Coat exposed copper; use corrosion-resistant coil coating",
                               "Fix nearby gas leaks that put H2S in the air"])),
              ])),
              B("Leaks not caught early", R(
                  "No periodic refrigerant leak test or pressure trending", "Method",
                  prevent=["Quarterly leak test and pressure log", "Trend suction pressure in SCADA"])),
          ], how="Look for oily patches on joints — refrigerant leaks carry compressor oil with them."),
          case="KB-0713"),
        C("flow", "Chilled-water / glycol circulation low (Chiller Pump trip, air lock)", "Machine",
          ["chiller pump", "circulation", "glycol"], [
            "Check Chiller Pump 1 / 2: which is running, discharge pressure and current",
            "Start the standby pump; vent air from the high points of the circuit",
            "Top up glycol / water to the expansion tank level and check glycol strength",
            "Repair the tripped pump (see Pump tree)"],
          why=W("Why is the circulation low?", [
              B("Duty pump tripped, standby did not auto-start", R(
                  "No duty / standby auto-changeover tested", "Machine",
                  prevent=["Test auto-changeover monthly", "Alarm on low chilled-water flow"])),
              B("Air in the circuit after top-up", R(
                  "Top-up done without venting procedure", "Method",
                  prevent=["Write a top-up and venting procedure; fit auto air vents at high points"])),
              B("Glycol mix too weak, circuit icing", R(
                  "Glycol concentration not tested", "Material",
                  prevent=["Test glycol strength with a refractometer quarterly; keep ≥ 25–30%"])),
          ], how="Read the pump discharge gauges and listen for gurgling (air) in the circuit."),
          case=None),
        C("icing", "Setpoint too low — gas-side exchanger icing", "Method", ["icing", "ice", "frost", "setpoint"], [
            "Raise the gas outlet setpoint back to 3 °C",
            "Let the exchanger defrost with gas flow reduced; drain the separator well during defrost",
            "Check the anti-freeze / hot-gas bypass control works",
            "Confirm gas-side dP across the chiller returns to normal"],
          why=W("Why was the setpoint set so low?", [
              B("Operator lowered it to chase purity", W("Why did they think that would help?", [
                  B("Purity problems blamed on moisture without checking", R(
                      "No troubleshooting guide; setpoint used as a fix-all", "Man",
                      prevent=["Train operators that below ~1 °C water freezes and blocks the exchanger",
                               "Use the SiteBrain Membrane tree before changing chiller setpoints"])),
                  B("No setpoint limits in the HMI", R(
                      "HMI allows setpoints below freezing", "Method",
                      prevent=["Clamp the setpoint range in the HMI to 2–5 °C",
                               "Log setpoint changes with the user name"])),
              ])),
              B("Hot-gas bypass / anti-freeze control failed", R(
                  "Anti-freeze thermostat not tested", "Machine",
                  prevent=["Test the anti-freeze cut-out in the 6-monthly PM"])),
          ], how="Look at the HMI setpoint history and the gas-side dP trend across the chiller."),
          case="KB-0714"),
        C("load", "Gas arriving hotter / wetter or at higher flow than the chiller rating", "Material",
          ["ambient", "hot", "overload", "inlet temperature"], [
            "Check gas inlet temperature and flow against the chiller rating",
            "Check the LP compressor after-cooler is working (if fitted)",
            "Reduce gas flow until the outlet is back to 2–5 °C",
            "Shade the chiller / condenser from afternoon sun"],
          why=W("Why is the chiller heat load above its rating?", [
              B("After-cooler upstream not cooling", R(
                  "LP compressor after-cooler fouled or fan off", "Machine",
                  prevent=["Clean after-cooler fins monthly; alarm on after-cooler outlet temperature"])),
              B("Hot afternoons beat the condenser", R(
                  "Chiller sized for average, not peak summer ambient", "Environment",
                  prevent=["Shade the condenser and add evaporative pre-cooling",
                           "Review chiller capacity at 45 °C ambient before plant expansion"])),
              B("Gas flow pushed above design", R(
                  "Throughput increased without checking chiller capacity", "Method",
                  prevent=["Make any BUU throughput increase a MOC item including chiller rating"])),
          ], how="Compare inlet gas temperature and flow with the chiller nameplate; note time of day."),
          case=None),
        C("sensor", "Outlet temperature / dew point sensor drift — false reading", "Measurement",
          ["sensor", "dew point", "reading", "calibration"], [
            "Check the outlet temperature with a calibrated probe at the test point",
            "Compare dew point with a portable dew-point meter",
            "Recalibrate or replace the sensor"],
          why=W("Why is the sensor reading wrong?", [
              B("Sensor not calibrated for over a year", R(
                  "Temperature / dew point sensors not in the calibration plan", "Measurement",
                  prevent=["Add chiller outlet temperature and dew point sensors to 6-monthly calibration"])),
              B("Dew point probe wetted by liquid water", R(
                  "Dew point probe mounted where free water hits it", "Machine",
                  prevent=["Relocate the probe after the separator in a sample cell"])),
          ], how="Hold a calibrated probe in the thermowell next to the sensor; compare after 3 minutes."),
          case=None),
    ],
    "questions": [
        Q("gt", "Read the gas outlet temperature at the chiller (local gauge). What is it?", [
            ("2–5°C", {"filter": 0.6, "drain": 0.8, "refrig": 0.3, "flow": 0.4, "icing": 1.2, "load": 0.4, "sensor": 1.6}),
            ("5–8°C", {"filter": 2.2, "drain": 1.0, "refrig": 1.6, "flow": 1.6, "icing": 0.6, "load": 2.0, "sensor": 1.0}),
            ("Above 8°C", {"filter": 1.2, "drain": 1.3, "refrig": 2.6, "flow": 2.0, "icing": 0.4, "load": 1.6, "sensor": 0.8},
             ["water_carryover"]),
            ("Below 1°C", {"icing": 4.0, "filter": 0.4, "drain": 0.8, "refrig": 0.4, "flow": 0.5, "load": 0.4, "sensor": 1.4}),
        ], ["gas outlet", "temperature", "dew point"], {"tag": "gas_outlet_temp_c", "option": 0, "above": 5.5},
          how="Read the local temperature gauge on the gas outlet line after the separator, and the SCADA value.",
          purpose="Gas leaving above 5 °C still carries water that will condense downstream on the membranes."),
        Q("drain", "Watch the condensate auto-drain for 5 minutes. Does it cycle?", [
            ("Cycles normally", {"filter": 1.2, "drain": 0.15, "refrig": 1.2, "flow": 1.2, "icing": 1.0, "load": 1.2, "sensor": 1.2}),
            ("No cycling, separator full",
             {"filter": 0.7, "drain": 4.5, "refrig": 0.7, "flow": 0.7, "icing": 1.0, "load": 0.8, "sensor": 0.7}, ["water_carryover"]),
        ], ["auto-drain", "separator", "carryover"], {"tag": "condensate_drain_cycles_h", "option": 0, "below": 2},
          how="Stand by the separator drain and listen / watch for the trap or solenoid to discharge; check the sight "
              "glass level. Normal is about 6 discharges per hour.",
          purpose="If the drain stops, water piles up in the separator and is carried straight to the membranes."),
        Q("glass", "Check the refrigerant sight glass on the liquid line. What do you see?", [
            ("Clear liquid", {"filter": 1.3, "drain": 1.2, "refrig": 0.2, "flow": 1.2, "icing": 1.2, "load": 1.1, "sensor": 1.2}),
            ("Bubbles / flashing", {"filter": 1.0, "drain": 0.8, "refrig": 3.5, "flow": 0.8, "icing": 0.7, "load": 1.2, "sensor": 0.8}),
            ("Oily patch on a pipe joint", {"refrig": 4.0, "filter": 0.8, "drain": 0.8, "flow": 0.8, "icing": 0.7, "load": 0.8, "sensor": 0.8}),
        ], ["refrigerant", "sight glass", "leak"],
          how="Look at the sight glass with the refrigeration compressor running for at least 10 minutes. Don't open any "
              "refrigerant fitting — that's for a certified technician.",
          purpose="Bubbles mean the circuit is short of refrigerant, so it can't pull the gas down to temperature."),
        Q("cond", "Look at the condenser coil and its air filter. What condition are they in?", [
            ("Clean, fan running", {"filter": 0.15, "drain": 1.1, "refrig": 1.1, "flow": 1.1, "icing": 1.1, "load": 1.1, "sensor": 1.1}),
            ("Dusty / matted filter or coil", {"filter": 5.0, "drain": 0.7, "refrig": 0.8, "flow": 0.7, "icing": 0.6, "load": 1.0, "sensor": 0.7}),
        ], ["filter", "condenser", "dust"],
          how="Look from outside the fan guard. Only clean with the chiller isolated and locked out — the fan can start on its own.",
          purpose="A choked condenser can't throw heat away, so the gas is not cooled enough."),
        Q("pumps", "Check Chiller Pumps 1 and 2. What do you find?", [
            ("One running, normal pressure", {"flow": 0.15, "filter": 1.1, "drain": 1.1, "refrig": 1.1, "icing": 1.1, "load": 1.1, "sensor": 1.1}),
            ("Low pressure or gurgling (air)", {"flow": 3.5, "filter": 0.8, "drain": 0.8, "refrig": 0.9, "icing": 1.2, "load": 0.8, "sensor": 0.8}),
            ("Both stopped / tripped", {"flow": 4.5, "filter": 0.7, "drain": 0.8, "refrig": 0.8, "icing": 0.7, "load": 0.8, "sensor": 0.8}),
        ], ["chiller pump", "circulation", "glycol"],
          how="Read the discharge gauge on each pump and look at the MCC run lamps. Listen at the pipework for gurgling.",
          purpose="Without chilled-water flow the gas exchanger warms up, however well the refrigeration works."),
        Q("frost", "Look at the gas-side exchanger and outlet piping. Any frost or ice, and is the setpoint normal?", [
            ("No frost, setpoint about 3°C", {"icing": 0.15, "filter": 1.1, "drain": 1.1, "refrig": 1.1, "flow": 1.1, "load": 1.1, "sensor": 1.1}),
            ("Frost / ice, or setpoint below 1°C", {"icing": 4.5, "filter": 0.6, "drain": 1.0, "refrig": 0.8, "flow": 0.9, "load": 0.6, "sensor": 0.9}),
        ], ["icing", "ice", "frost", "setpoint"],
          how="Look at the exchanger outlet and separator body; check the setpoint on the HMI. Don't knock ice off pipework.",
          purpose="Ice blocks the gas path and, when it melts, sends a slug of water downstream."),
        Q("inlet", "What are the gas inlet temperature and flow, and what's the weather like?", [
            ("Inlet below 40°C, flow normal", {"load": 0.2, "filter": 1.0, "drain": 1.1, "refrig": 1.1, "flow": 1.1, "icing": 1.1, "sensor": 1.1}),
            ("Hot afternoon / inlet or flow above design",
             {"load": 4.0, "filter": 1.4, "drain": 0.8, "refrig": 1.0, "flow": 0.8, "icing": 0.6, "sensor": 0.8}),
        ], ["ambient", "hot", "overload", "inlet temperature"],
          how="Read the inlet gas temperature and BUU gas flow on SCADA, and note the ambient temperature.",
          purpose="If the gas arrives hotter or faster than the chiller is rated for, it can't reach 2–5 °C."),
        Q("chw", "Feel (or read) the chilled-water supply and return lines at the gas exchanger. How do they compare?", [
            ("Supply cold, return a few degrees warmer", {"flow": 0.2, "refrig": 0.6, "filter": 0.8, "drain": 1.2, "icing": 1.2, "load": 1.3, "sensor": 1.2}),
            ("Little or no difference, both lukewarm", {"flow": 3.0, "refrig": 2.5, "filter": 1.8, "drain": 0.7, "icing": 0.5, "load": 0.8, "sensor": 0.6}),
            ("Big difference, return much warmer than usual", {"load": 4.0, "flow": 0.8, "refrig": 0.8, "filter": 1.0, "drain": 0.8, "icing": 0.5, "sensor": 0.7}),
        ], ["chiller pump", "circulation", "glycol", "overload"],
          how="Read the supply and return temperature gauges on the chilled-water lines, or carefully touch the insulated "
              "pipe at a bare flange with the back of your hand.",
          purpose="The water temperature difference shows whether water isn't flowing or the gas is bringing too much heat."),
        Q("probe", "Put a calibrated probe in the test thermowell. Does it agree with the SCADA outlet temperature?", [
            ("Agrees within 1°C", {"sensor": 0.15, "filter": 1.1, "drain": 1.1, "refrig": 1.1, "flow": 1.1, "icing": 1.1, "load": 1.1}),
            ("Differs by more than 2°C", {"sensor": 4.5, "filter": 0.7, "drain": 0.8, "refrig": 0.7, "flow": 0.7, "icing": 0.8, "load": 0.7}),
        ], ["sensor", "dew point", "reading", "calibration"],
          how="Use the plant's calibrated digital thermometer in the spare thermowell next to the sensor and wait 3 minutes.",
          purpose="A drifting sensor can hide a real problem or raise a false one."),
    ],
}

# ───────────────────────────────────────────────────────────────── Membrane Upgrader ──
TREES["Membrane"] = {
    "causes": [
        C("moist", "Moisture / condensate reaching the membranes from the chiller", "Material",
          ["methane purity", "moisture", "dew point"], [
            "Divert off-spec gas to flare / recycle (MEM-01)",
            "Check chiller dew point and auto-drain upstream; drain the membrane inlet low points",
            "Dry the membranes with dry gas per the OEM procedure before return to product",
            "Confirm CH4 > 95% for 1 hour before releasing the interlock"],
          why=W("Why did wet gas reach the membranes?", [
              B("Chiller auto-drain failed — separator flooded", R(
                  "Auto-drain failure not alarmed; drain not on PM", "Machine",
                  prevent=["Alarm on drain cycles < 2 /h and separator high level",
                           "Clean / test the auto-drain monthly"])),
              B("Gas not reheated after the chiller", W("Why did the reheater not lift the temperature?", [
                  B("Reheater / heat exchanger bypassed", R(
                      "Reheater bypass opened during maintenance and not restored", "Man",
                      prevent=["Add reheater line-up to the BUU restart checklist"])),
                  B("Reheater fouled or control valve failed", R(
                      "Reheater not in PM", "Machine",
                      prevent=["Add reheater inspection and control-valve stroke test to 6-monthly PM"])),
              ])),
              B("No dew-point interlock to the membrane feed", R(
                  "Dew point not interlocked with the membrane feed valve", "Measurement",
                  prevent=["Interlock membrane feed on dew point > 5 °C (CHL-01)"])),
          ], how="Check the chiller drain cycles and dew point trend at the time purity fell."),
          case="KB-0706"),
        C("tail", "Tail-gas / permeate recycle valve malfunction", "Machine", ["tail gas", "recycle", "valve"], [
            "Put the recycle valve in manual and stroke-test 0–100%",
            "Check instrument air pressure and dryness at the positioner",
            "Recalibrate the positioner; replace it if it hunts",
            "Restore the stage pressure ratio and confirm purity > 95% and methane slip < 1%"],
          why=W("Why is the recycle valve not controlling?", [
              B("Wet or dirty instrument air", W("Why is the instrument air bad?", [
                  B("Air dryer off or desiccant spent", R(
                      "Instrument air dryer not on PM", "Machine",
                      prevent=["Monthly instrument-air dew point check; change desiccant per OEM"])),
                  B("Air filter-regulator never drained", R(
                      "Filter-regulator drain not on rounds", "Man",
                      prevent=["Drain instrument air filter-regulators on weekly rounds"])),
              ])),
              B("Positioner out of calibration / sticking stem", R(
                  "Control valves on the membrane skid have no stroke test", "Method",
                  prevent=["Quarterly stroke test of recycle and retentate valves with recorded response"])),
          ], how="Stroke the valve and watch the stem against the demand; hunting or lag points to air or positioner."),
          case="KB-0715"),
        C("foul", "Membrane fouling from compressor oil / VOC / siloxane (guard bed spent)", "Material",
          ["permeate", "fouling", "oil", "voc"], [
            "Check compressor oil carry-over filters and coalescer drains",
            "Replace the activated-carbon guard bed",
            "Compare stage permeate dP and flows with the commissioning baseline",
            "Plan a membrane module inspection / performance test with the OEM"],
          why=W("Why did oil / VOC reach the membranes?", [
              B("Activated-carbon guard bed exhausted", W("Why was the guard bed not changed in time?", [
                  B("Change-out on calendar only", R(
                      "No VOC / breakthrough check after the guard bed", "Measurement",
                      prevent=["Quarterly VOC / siloxane check after the guard bed (PID or lab sample)",
                               "Change carbon on breakthrough or OEM hours, whichever first"])),
                  B("Carbon not in stock", R(
                      "No spares plan for guard-bed carbon", "Method",
                      prevent=["Keep one carbon charge in stock"])),
              ])),
              B("Compressor oil carry-over increased", R(
                  "LP / HP compressor rings or oil separator worn; carry-over not measured", "Machine",
                  prevent=["Check coalescer drain oil weekly and log it",
                           "Overhaul compressor rings / separator at OEM hours"])),
              B("Feedstock brings siloxanes / terpenes", R(
                  "Feedstock with VOC (citrus, solvents, sludge) not screened", "Material",
                  prevent=["Screen new feedstocks for VOC-rich content; inform BUU before trial loads"])),
          ], how="Look at the coalescer drains for oil and check the guard bed hours since last change."),
          case="KB-0716"),
        C("press", "Feed pressure / pressure ratio too low (setpoint or compressor capacity)", "Method",
          ["feed pressure", "pressure ratio", "setpoint"], [
            "Check membrane feed pressure against the setpoint (≈ 12–15 bar g)",
            "Check the LP compressors are all loaded and not short-cycling",
            "Restore the setpoint per SOP-BUU-01; record who changed it",
            "Confirm stage pressures and purity recover"],
          why=W("Why is the feed pressure low?", [
              B("Setpoint lowered to save power", R(
                  "Setpoint changes allowed without MOC or engineer approval", "Method",
                  prevent=["Lock feed pressure setpoint behind engineer access; log changes"])),
              B("A compressor is unloaded or tripped", R(
                  "Compressor capacity loss not alarmed", "Machine",
                  prevent=["Alarm membrane feed pressure 1 bar below setpoint",
                           "Run SiteBrain Compressor tree on the tripped unit"])),
              B("Gas flow above what the compressors can push", R(
                  "Throughput increased beyond compressor / membrane design", "Man",
                  prevent=["Review membrane area and compressor capacity before raising gas flow"])),
          ], how="Read the feed pressure trend and compressor load status at the time purity fell."),
          case=None),
        C("temp", "Feed gas temperature outside the membrane window", "Environment",
          ["feed temperature", "temperature", "hot"], [
            "Check the membrane feed temperature against the OEM window (typically 20–40 °C)",
            "Check the reheater and the after-cooler control",
            "Shade / ventilate the membrane container if it is overheating",
            "Return the temperature to setpoint and confirm purity / methane slip"],
          why=W("Why is the feed temperature off?", [
              B("Container overheating in summer", R(
                  "Membrane container ventilation / AC undersized for peak ambient", "Environment",
                  prevent=["Add container ventilation / AC with high-temperature alarm",
                           "Shade the container roof"])),
              B("Temperature control valve failed", R(
                  "Reheater temperature control not tested", "Machine",
                  prevent=["Stroke-test the reheater TCV quarterly"])),
          ], how="Compare feed temperature trend with ambient: rising with the afternoon heat means ventilation."),
          case=None),
        C("analyser", "CH4 analyser drift — false purity reading", "Measurement",
          ["analyser", "analyzer", "calibration"], [
            "Check the analyser with certified calibration gas",
            "Cross-check with a portable infrared gas analyser at the product sample point",
            "Recalibrate; replace the IR cell or sample filter if needed",
            "Release MEM-01 only after a verified reading"],
          why=W("Why did the analyser drift?", [
              B("Calibration overdue", R(
                  "CH4 analyser not on a calibration schedule", "Measurement",
                  prevent=["Weekly zero/span check; monthly full calibration logged"])),
              B("Sample line wet / filter blocked", R(
                  "Sample conditioning not on PM", "Machine",
                  prevent=["Change sample filter monthly; drain sample line on rounds"])),
              B("Wrong calibration gas used", R(
                  "Calibration gas not controlled", "Material",
                  prevent=["Keep cylinders labelled and certificates in date"])),
          ], how="Compare the analyser with a portable analyser within the same 5 minutes."),
          case="KB-0717"),
    ],
    "questions": [
        Q("purity", "Read the CH4 analyser at the product outlet. What is the methane purity?", [
            ("Above 95%", {"moist": 0.6, "tail": 0.8, "foul": 0.8, "press": 0.7, "temp": 0.8, "analyser": 1.3}),
            ("90–95%", {"moist": 1.4, "tail": 1.2, "foul": 1.2, "press": 1.3, "temp": 1.2, "analyser": 1.0}, ["offspec_gas"]),
            ("Below 90%", {"moist": 1.8, "tail": 1.3, "foul": 1.0, "press": 1.3, "temp": 1.0, "analyser": 1.0}, ["offspec_gas"]),
        ], ["methane purity", "quality"], {"tag": "ch4_purity_pct", "option": 0, "below": 95},
          how="Read the product CH4 analyser on SCADA or the local display on the membrane skid.",
          purpose="Below 95% the gas can't go to the CBG cascade and must be diverted."),
        Q("dew", "What does the chiller report for gas outlet temperature / dew point?", [
            ("2–5°C", {"moist": 0.2, "tail": 1.2, "foul": 1.2, "press": 1.2, "temp": 1.1, "analyser": 1.2}),
            ("Above 5°C", {"moist": 4.0, "tail": 0.8, "foul": 0.8, "press": 0.8, "temp": 1.0, "analyser": 0.8}),
        ], ["moisture", "dew point", "gas outlet"],
          how="Read the chiller gas outlet temperature and dew point on SCADA, or the local gauge at the chiller.",
          purpose="Wet gas condenses in the fibres and blocks them, so CO2 isn't removed."),
        Q("lowpt", "Open the membrane inlet low-point drain (with permit). Any water?", [
            ("Dry", {"moist": 0.3, "tail": 1.1, "foul": 1.1, "press": 1.1, "temp": 1.1, "analyser": 1.1}),
            ("Water comes out", {"moist": 4.0, "tail": 0.8, "foul": 0.9, "press": 0.8, "temp": 0.9, "analyser": 0.8}),
            ("Oily liquid comes out", {"foul": 4.0, "moist": 1.2, "tail": 0.7, "press": 0.8, "temp": 0.8, "analyser": 0.7}),
        ], ["moisture", "oil", "drain"],
          how="This line is at 12–15 bar: use the permit, open the drain needle valve a crack into a container, stand "
              "to the side and wear your gas monitor. Close it as soon as gas appears.",
          purpose="Liquid at the membrane inlet proves contamination is reaching the fibres."),
        Q("valve", "Stroke the tail-gas recycle valve in manual (control room). How does it respond?", [
            ("Moves smoothly to setpoint", {"moist": 1.2, "tail": 0.15, "foul": 1.2, "press": 1.1, "temp": 1.1, "analyser": 1.2}),
            ("Sticky / hunting", {"moist": 0.7, "tail": 4.5, "foul": 0.7, "press": 0.8, "temp": 0.7, "analyser": 0.7}),
        ], ["tail gas", "recycle", "valve"],
          how="Ask the control room to put the valve in manual and step it 10% at a time while you watch the stem. "
              "Keep product diverted to flare / recycle during the test.",
          purpose="The recycle valve sets the pressure ratio between stages — if it can't hold position, purity swings."),
        Q("ratio", "How does the permeate dP compare with the commissioning baseline?", [
            ("Same", {"moist": 1.0, "tail": 1.3, "foul": 0.25, "press": 1.1, "temp": 1.1, "analyser": 1.2}),
            ("Higher by >30%", {"moist": 1.4, "tail": 0.7, "foul": 3.5, "press": 0.7, "temp": 0.8, "analyser": 0.7}),
        ], ["permeate", "fouling"], {"tag": "permeate_dp_bar", "option": 0, "above": 1.15},
          how="Read permeate dP on SCADA (baseline ≈ 0.9 bar) and compare with the commissioning sheet in the control room.",
          purpose="A higher dP than when new means the fibres are fouled."),
        Q("feedp", "What is the membrane feed pressure compared with its setpoint?", [
            ("At setpoint (about 12–15 bar)", {"press": 0.15, "moist": 1.1, "tail": 1.1, "foul": 1.1, "temp": 1.1, "analyser": 1.1}),
            ("Below setpoint / compressor unloaded", {"press": 4.5, "moist": 0.8, "tail": 1.0, "foul": 0.8, "temp": 0.8, "analyser": 0.7}),
        ], ["feed pressure", "pressure ratio", "setpoint", "pressure"],
          how="Read the feed pressure on SCADA and the setpoint on the BUU HMI; check all LP compressors show 'loaded'.",
          purpose="The membranes need pressure to push CO2 through — low pressure means poor separation."),
        Q("feedt", "What is the membrane feed gas temperature?", [
            ("Within the normal band", {"temp": 0.15, "moist": 1.0, "tail": 1.1, "foul": 1.1, "press": 1.1, "analyser": 1.1}),
            ("Much hotter or colder than normal", {"temp": 5.0, "moist": 1.0, "tail": 0.7, "foul": 0.7, "press": 0.7, "analyser": 0.6}),
        ], ["feed temperature", "temperature", "hot"],
          how="Read the feed temperature transmitter after the reheater on SCADA and compare with the setpoint.",
          purpose="Temperature changes how fast gases pass the fibres; too cold also lets water condense."),
        Q("cal", "Cross-check the product gas with a portable analyser (or calibration gas). Does the analyser read right?", [
            ("Reads correctly", {"analyser": 0.15, "moist": 1.1, "tail": 1.1, "foul": 1.1, "press": 1.1, "temp": 1.1}),
            ("Off by more than 1%", {"analyser": 4.5, "moist": 0.7, "tail": 0.7, "foul": 0.7, "press": 0.7, "temp": 0.7}),
        ], ["analyser", "analyzer", "calibration"],
          how="Connect the portable IR analyser to the product sample point with the right regulator; purge for 1 minute "
              "before reading. Wear your gas monitor.",
          purpose="Before blaming the membranes, make sure the reading is true."),
        Q("guard", "Check the activated-carbon guard bed and compressor coalescer drains. What do you find?", [
            ("Within life, no oil in drains", {"foul": 0.2, "moist": 1.1, "tail": 1.1, "press": 1.1, "temp": 1.1, "analyser": 1.1}),
            ("Overdue or oil in the drains", {"foul": 4.0, "moist": 0.9, "tail": 0.8, "press": 0.8, "temp": 0.8, "analyser": 0.8}),
        ], ["oil", "voc", "fouling", "permeate"],
          how="Check the guard bed hour counter / change label, and drain the compressor coalescers into a clear jar.",
          purpose="Oil and VOC coat the fibres permanently — the guard bed is their protection."),
    ],
}

# ─────────────────────────────────────────────────────────────────────── Maintenance ──
MAINTENANCE = {
    "Scrubber": {
        "summary": "Dry-media H2S adsorber (iron-oxide or impregnated activated carbon) with a top distributor mesh and "
                   "perimeter seal. Removes H2S from raw biogas to < 10 ppm. Media has a fixed sulfur capacity, needs "
                   "the gas free of liquid water, and spent media can self-heat in air (pyrophoric iron sulfide).",
        "pm": [
            ("Every shift", "Log bed dP, outlet H2S, outlet O2 and air-dosing setting; drain the upstream knock-out pot"),
            ("Daily", "Calculate sulfur loading (flow × inlet H2S) and update the change-out forecast"),
            ("Weekly", "Dräger tube cross-check of the outlet analyser; IR scan of the shell for hot spots"),
            ("Monthly", "Calibrate the H2S analyser with span gas; clean air-dosing rotameter; check knock-out auto-drain"),
            ("At media change", "Screen new media, level the bed, re-align the top mesh, new perimeter seal, torque 25 N·m; "
                                "keep spent media wet and dispose per SOP"),
            ("Yearly", "Internal inspection of vessel, support grid and coating; pressure test"),
        ],
        "failure_modes": ["Channeling past a misaligned top mesh / perimeter seal gap",
                          "Media caking from free water and elemental sulfur (high dP)",
                          "Media exhaustion — H2S breakthrough", "Inlet H2S load above design",
                          "Bed overheating from excess air / O2 dosing", "Media carryover to the filter skid",
                          "Analyser drift giving false H2S readings"],
        "operating_limits": [("Bed dP", "0.04–0.06 bar (alarm > 0.10 bar or < 0.02 bar)"),
                             ("Outlet H2S", "< 10 ppm (breakthrough > 30 ppm)"),
                             ("Inlet H2S (design)", "≤ 2,000 ppm"),
                             ("Outlet O2 with air dosing", "0.3–0.5% (max 1%)"),
                             ("Shell temperature", "≈ gas temperature; investigate any hot spot > 60 °C")],
    },
    "Filter": {
        "summary": "Gas Filtration Skid with duty / standby particulate–coalescing element housings, a bypass valve kept "
                   "locked closed, and a secondary guard filter. Protects blowers and LP compressors from media fines, "
                   "pipe scale and liquid.",
        "pm": [
            ("Every shift", "Log element dP; check bypass valve closed and locked; guard filter in service"),
            ("Weekly", "Drain housings and check the drain trap; compare local dP gauge with SCADA"),
            ("At 0.20 bar dP or OEM interval", "Change elements with new O-rings; check part number; record what loaded them"),
            ("Monthly", "Blow down dP impulse lines; inspect compressor suction strainers"),
            ("6-monthly", "Calibrate the dP transmitter; inspect housing internals and seat"),
        ],
        "failure_modes": ["Element loading with scrubber fines / pipe scale", "Element rupture or collapse at high dP",
                          "Bypass left open or used without permit", "Liquid loading of elements",
                          "Element unseated / wrong grade after change-out", "dP instrument fault"],
        "operating_limits": [("Element dP (clean)", "0.05–0.10 bar"), ("Element change-out", "0.20 bar"),
                             ("Element dP high-high", "0.30 bar (rupture risk)"),
                             ("Bypass valve", "Closed and locked; open only with permit and guard filter active")],
    },
    "Chiller": {
        "summary": "Gas dehumidification chiller: gas-to-glycol/water exchanger cooling biogas to a 2–5 °C dew point, a "
                   "condensate separator with auto-drain, refrigeration circuit with air-cooled condenser and filter, and "
                   "Chiller Pumps 1/2 circulating chilled water. Protects the membranes from liquid water.",
        "pm": [
            ("Every shift", "Log gas outlet temperature / dew point and drain cycling; check sight glass and pump running"),
            ("Weekly", "Clean condenser filter (daily in dusty season); clean drain-trap strainer"),
            ("Monthly", "Strip and test the auto-drain; test Chiller Pump auto-changeover; vent air from the circuit"),
            ("Quarterly", "Refrigerant leak test and pressure log; glycol strength by refractometer"),
            ("6-monthly", "Calibrate outlet temperature and dew point sensors; test anti-freeze cut-out"),
            ("Yearly", "Coil chemical clean; compressor oil and electrical checks by refrigeration contractor"),
        ],
        "failure_modes": ["Auto-drain stuck — water carryover to membranes", "Condenser filter / coil choked with dust",
                          "Low refrigerant charge from leaks", "Chilled-water circulation loss",
                          "Gas-side icing from too-low setpoint", "Heat load above rating in summer",
                          "Sensor drift"],
        "operating_limits": [("Gas outlet temperature / dew point", "2–5 °C (CHL-01 interlock above 8 °C)"),
                             ("Condensate drain cycling", "4–8 per hour"),
                             ("Chiller setpoint", "3 °C (never below 1 °C)"),
                             ("Glycol strength", "25–30%")],
    },
    "Membrane": {
        "summary": "Multi-stage hollow-fibre (polyimide) membrane upgrader separating CO2 from CH4 to > 95% CH4 product "
                   "(IS 16087 minimum 90%), with tail-gas / permeate recycle, an activated-carbon guard bed for oil / VOC, "
                   "and feed gas reheated above its dew point. Off-spec product is diverted (MEM-01).",
        "pm": [
            ("Every shift", "Log product CH4, feed pressure and temperature, permeate dP, tail-gas flow and methane slip"),
            ("Weekly", "Zero / span check of CH4 analyser; drain compressor coalescers and membrane low points"),
            ("Monthly", "Full analyser calibration; check instrument-air dryer; sample filter change"),
            ("Quarterly", "Stroke-test recycle and retentate valves; VOC check after the guard bed"),
            ("Per OEM hours / breakthrough", "Replace activated-carbon guard bed"),
            ("Yearly", "Membrane performance test vs commissioning baseline with the OEM"),
        ],
        "failure_modes": ["Purity drop from moisture carryover", "Fouling by oil / VOC / siloxanes",
                          "Recycle valve malfunction", "Low feed pressure / pressure ratio",
                          "Feed temperature outside window", "Analyser drift", "High methane slip in off-gas"],
        "operating_limits": [("Product CH4", "> 95% plant target (IS 16087 ≥ 90%)"),
                             ("Product CO2", "≤ 4% for cylinder filling"),
                             ("Feed pressure", "≈ 12–15 bar g"), ("Feed temperature", "≈ 20–40 °C, ≥ 10 °C above dew point"),
                             ("Permeate dP", "≈ 0.9 bar (alarm > 30% above baseline)"),
                             ("Methane slip in off-gas", "< 1% of CH4 in feed")],
    },
}

# ──────────────────────────────────────────────────────────────── Operating conditions ──
CONDITIONS = [
    {
        "id": "BUU-GAS", "title": "Gas cleaning & upgrading (BUU)", "areas": ["BUU"],
        "params": [
            ("Raw biogas CH4", "52–62%", "Sets how much CO2 the membranes must remove and product yield",
             "Below 50%: check digester health (VFA/alkalinity) and air ingress; reduce BUU throughput"),
            ("Raw biogas CO2", "35–45%", "Balance of CH4; drives membrane load",
             "Above 45%: digester upset or acidification — inform the process team"),
            ("Raw biogas H2S", "500–2,000 ppm", "Determines scrubber media life",
             "Above design: hold sulfur-rich feed, increase in-digester desulfurisation, plan earlier media change"),
            ("Raw biogas O2", "< 0.5% (with air dosing ≤ 1%)", "O2 ends up in CBG and heats scrubber media",
             "Above 1%: cut air dosing, check for air ingress at digester / gas holder"),
            ("Scrubber bed dP", "0.04–0.06 bar", "Rising = caking; sudden drop = channeling",
             "Above 0.10 bar: de-choke per SOP-SCR-02. Below 0.02 bar: lock filter bypass (SCR-01), inspect mesh"),
            ("Scrubber outlet H2S", "< 10 ppm", "H2S corrodes compressors and is limited in CBG (30.3 mg/m³)",
             "Above 30 ppm: breakthrough — switch vessel, tube-check, change media (SCR-02 advisory)"),
            ("Filter element dP", "0.05–0.10 bar", "Tells how loaded the elements are",
             "At 0.20 bar change elements; sudden drop after a rise means rupture — trip LP load line (CMP-01)"),
            ("Filter bypass valve", "Closed and locked", "Open bypass sends particles to compressors",
             "Close and lock; bypass only with permit and secondary guard active (FLT-01 / FLT-02)"),
            ("LP compressor discharge", "≈ 6 bar g", "Feeds the chiller and HP stage",
             "Low: check compressor loading; see Compressor tree"),
            ("Chiller gas outlet temperature / dew point", "2–5 °C", "Removes water before the membranes",
             "Above 8 °C: CHL-01 halts membrane feed; check drain, condenser, refrigerant, pumps"),
            ("Chiller condensate drain cycling", "4–8 per hour", "Proves water is being removed",
             "No cycling: drain separator manually, fix the trap; check for carryover"),
            ("Membrane feed pressure", "12–15 bar g", "Driving force for CO2 removal",
             "Low: check setpoint and LP/HP compressor loading"),
            ("Membrane feed temperature", "20–40 °C (≥ 10 °C above dew point)", "Controls selectivity and stops condensation",
             "Out of band: check reheater / TCV and container ventilation"),
            ("Permeate dP", "≈ 0.9 bar (baseline)", "Rise shows fibre fouling",
             "More than 30% above baseline: check guard bed and compressor oil carry-over"),
            ("Product CH4 purity", "> 95% (IS 16087 ≥ 90%)", "Product spec for CBG cascade / pipeline",
             "Below 95%: MEM-01 diverts to flare / recycle; run the Membrane tree"),
            ("Product CO2 / moisture / H2S", "CO2 ≤ 4%, moisture ≤ 16 mg/m³, H2S ≤ 30.3 mg/m³", "IS 16087 CBG limits",
             "Out of spec: divert product, find the failing stage (scrubber, chiller, membrane)"),
            ("Methane slip (off-gas CH4)", "< 1% of feed CH4", "Lost product and greenhouse emissions",
             "Above 1%: check recycle valve, stage pressure ratio and module integrity"),
            ("Tail-gas recycle flow", "≈ 40–45 Nm³/h", "Recycle keeps CH4 recovery high",
             "Large change: stroke-test the recycle valve, check instrument air"),
        ],
        "notes": [
            "Gas train order: Digesters → H2S Scrubber → Gas Filtration Skid → Gas Blowers → LP Compressors → Chiller → "
            "Membrane → HP compressors → CBG cascade. A fault upstream usually shows up downstream first.",
            "Purity problems at the membrane are most often moisture or oil from upstream — check the chiller and "
            "guard bed before touching membrane settings.",
            "Spent scrubber media and filter fines can be pyrophoric: keep them wet and bagged, never dry in a pile.",
            "Any vessel or housing opening needs isolation, depressurisation, N2 purge, gas test and a permit; wear an "
            "H2S personal monitor throughout.",
            "Plant product target (> 95% CH4) is tighter than IS 16087 (≥ 90%) to keep margin for the CBG cascade.",
        ],
    },
]

# ───────────────────────────────────────────────────────────────────────── RCA cases ──
CASES = [
    K("KB-0637", ["Chiller"], ["filter", "condenser", "gas outlet"], "Chiller filter partially choked, gas outlet at 6.5 °C",
      "Dust loading on condenser-side filter reduced heat rejection",
      "Isolated fan, cleaned filter and coil, checked refrigerant pressures, outlet back to 3.5 °C",
      why=["Why was the outlet warm? Condenser discharge pressure high, poor heat rejection",
           "Why poor heat rejection? Condenser filter matted with dust",
           "Why so much dust? Harvest season straw handling upwind of the chiller",
           "Why not cleaned? Weekly cleaning not adjusted for dusty season"],
      category="Environment", prevent="Daily filter cleaning in dusty season; pre-filter screen on intake side"),
    K("KB-0702", ["Scrubber"], ["mesh", "seal gap", "differential", "channel"],
      "Unstable scrubber dP with suspected particulate migration",
      "Top distributor mesh misalignment with perimeter seal gap causing bed channeling",
      "Locked filter bypass closed (SCR-01), purged vessel, re-seated media, re-aligned mesh, new perimeter seal, "
      "flushed filter skid and verified dP",
      why=["Why did dP drop suddenly? Gas channeled past the bed along the wall",
           "Why channeling? Perimeter seal gap at the top distributor mesh",
           "Why the gap? Mesh refitted without torque or contact check after media change",
           "Why no check? Media change-out procedure had no mesh acceptance step"],
      category="Method", prevent="Signed mesh-contact and 25 N·m torque check added to SOP-SCR-02; photo before closing"),
    K("KB-0703", ["Scrubber"], ["differential", "caking", "choke"], "Scrubber dP climbing steadily over a week",
      "Media caking from moisture and elemental sulfur",
      "Back-flushed with N2 per SOP-SCR-02, replaced caked top layer, fixed upstream knock-out drain",
      why=["Why dP climbing? Top 150 mm of media caked into lumps",
           "Why caked? Free water reached the bed",
           "Why water? Knock-out pot auto-drain blocked",
           "Why unnoticed? Knock-out pot not on shift rounds"],
      category="Material", prevent="Auto-drain with level alarm on knock-out pot; added to shift rounds"),
    K("KB-0704", ["Scrubber"], ["breakthrough", "exhaust"], "Downstream H2S breakthrough above 100 ppm",
      "Media exhausted beyond its sulfur capacity",
      "Switched to standby vessel, replaced media charge, disposed spent media wet per SOP",
      why=["Why breakthrough? Media fully loaded with sulfur",
           "Why used so long? Change-out on calendar, not sulfur loading",
           "Why no loading log? Nobody owned the sulfur-loading calculation"],
      category="Method", prevent="Daily sulfur-loading log; reorder media at 70% capacity; 10 ppm pre-alarm"),
    K("KB-0705", ["Filter"], ["element dp", "loaded", "fines"], "Gas filtration skid element dP high (0.21 bar)",
      "Element loading from scrubber media fines after a fresh charge",
      "Changed over to standby, replaced element, traced fines to unscreened new media",
      why=["Why high dP? Element loaded with black granules",
           "Why granules? Fines from newly charged scrubber media",
           "Why fines? New media not screened or blown down before start-up"],
      category="Method", prevent="Screen new media before charging; run standby element for first week"),
    K("KB-0706", ["Membrane", "Chiller"], ["methane purity", "gas outlet", "auto-drain", "moisture"],
      "Methane purity dropped to 92%",
      "Water carryover from chiller auto-drain failure",
      "Diverted to flare (MEM-01), repaired auto-drain, dried membranes, verified purity > 95%",
      why=["Why purity drop? Liquid water reached the membrane fibres",
           "Why water? Chiller separator flooded",
           "Why flooded? Auto-drain trap blocked with sludge",
           "Why blocked unnoticed? No strainer before the trap and no alarm on drain cycling"],
      category="Machine", prevent="Y-strainer before the trap; SCADA alarm on drain cycles below 2/h; monthly trap PM"),
    K("KB-0707", ["Scrubber"], ["inlet h2s", "feedstock", "breakthrough"], "Scrubber outlet H2S rising two months early",
      "Inlet H2S load doubled after press-mud share in feed increased",
      "Cut press-mud share, restarted FeCl3 dosing in digesters, brought media change-out forward",
      why=["Why early breakthrough? Media used up twice as fast",
           "Why faster? Raw-gas H2S rose from 1,500 to 3,200 ppm",
           "Why? Press-mud share raised for gas yield without BUU review"],
      category="Material", prevent="Sulfur impact check on feed recipe changes; agreed maximum press-mud share"),
    K("KB-0708", ["Scrubber"], ["oxygen", "hot", "air dosing"], "Hot spot on scrubber shell and outlet O2 at 1.4%",
      "Air dosing rotameter opened too far, bed heating and sulfur deposition",
      "Cut air dosing, kept gas flowing until shell cooled, reset dosing to 0.4% O2 outlet",
      why=["Why hot spot? Exothermic reaction with excess O2 in the bed",
           "Why excess O2? Rotameter opened to stretch media life",
           "Why? No written dosing range; operator unaware of the risk"],
      category="Man", prevent="Dosing range in SOP-BUU-01; high outlet O2 alarm; operator training"),
    K("KB-0709", ["Scrubber"], ["analyser", "reading", "breakthrough"], "Outlet H2S alarm at 80 ppm but tube showed 5 ppm",
      "H2S analyser sample line full of condensate, sensor drift",
      "Drained sample line, calibrated analyser, fitted condensate pot",
      why=["Why false alarm? Analyser reading wrong",
           "Why wrong? Sample line wet and calibration overdue",
           "Why? Sample conditioning and calibration not in PM"],
      category="Measurement", prevent="Monthly span calibration; sample-line condensate pot and weekly drain"),
    K("KB-0710", ["Filter"], ["rupture", "particles", "element dp"], "Filter dP rose to 0.36 bar then fell to near zero",
      "Element collapsed and ruptured after change-out was deferred",
      "Tripped LP load line (CMP-01), replaced element and O-ring, cleaned compressor suction strainers",
      why=["Why dP collapse? Element pleats split",
           "Why split? dP well past the 0.30 bar limit",
           "Why not changed? No spare elements in stock"],
      category="Method", prevent="Two spare element sets in stock; high and high-high dP alarms"),
    K("KB-0711", ["Filter"], ["bypass"], "Filter bypass found open on morning round",
      "Bypass opened for element change and left open across shift change",
      "Closed and locked bypass, checked downstream strainers, briefed shifts",
      why=["Why open? Not closed after element change", "Why? Job spanned a shift change",
           "Why not caught? Handover sheet does not list open bypasses"],
      category="Man", prevent="Bypass register on handover sheet; limit switch with SCADA alarm"),
    K("KB-0712", ["Filter"], ["condensate", "wet", "element dp"], "Filter dP high with water in housing during monsoon",
      "Condensate from cooling gas line soaked the elements",
      "Drained housing, replaced wet elements, cleaned drain trap, added low-point drain",
      why=["Why high dP? Elements wet and swollen", "Why wet? Water condensed in the gas line",
           "Why? Line uninsulated with no drain point before the skid"],
      category="Environment", prevent="Insulate line; low-point drain pot; monsoon drain checks"),
    K("KB-0713", ["Chiller"], ["refrigerant", "sight glass", "gas outlet"], "Chiller outlet drifted to 9 °C over a week",
      "Refrigerant leak at a vibrating flare joint",
      "Leak-tested, re-made the joint, clamped the line, recharged; CHL-01 released at 3.5 °C",
      why=["Why warm outlet? Low refrigerant charge — bubbles in sight glass",
           "Why low? Flare joint leaking", "Why? Line unsupported and fatigued by vibration"],
      category="Machine", prevent="Clamp refrigerant lines; quarterly leak test; trend suction pressure"),
    K("KB-0714", ["Chiller", "Membrane"], ["icing", "setpoint", "methane purity"],
      "Chiller dP high, then water slug and purity dip to 93%",
      "Chiller setpoint lowered to 0 °C; exchanger iced and then shed water when it thawed",
      "Restored 3 °C setpoint, defrosted with reduced flow, drained separator, diverted product during the slug",
      why=["Why water slug? Ice in exchanger melted", "Why ice? Setpoint at 0 °C",
           "Why lowered? Operator chasing purity without diagnosing", "Why possible? HMI allowed sub-zero setpoint"],
      category="Method", prevent="HMI setpoint clamped to 2–5 °C; setpoint changes logged; operator training"),
    K("KB-0715", ["Membrane"], ["tail gas", "recycle", "methane purity"], "Purity swinging 93–97% every few minutes",
      "Recycle valve positioner hunting on wet instrument air",
      "Drained instrument air, replaced dryer desiccant, recalibrated positioner",
      why=["Why swings? Recycle valve hunting", "Why? Positioner fed wet air",
           "Why wet? Instrument air dryer desiccant spent"],
      category="Machine", prevent="Monthly instrument-air dew point check; quarterly valve stroke test"),
    K("KB-0716", ["Membrane"], ["permeate", "fouling", "oil", "methane purity"],
      "Purity slowly falling and permeate dP 40% above baseline",
      "Membrane fouling from compressor oil after guard bed exhaustion",
      "Replaced activated-carbon guard bed, overhauled LP compressor oil separator, OEM performance test",
      why=["Why falling purity? Fibres coated", "Why coated? Oil / VOC passed the guard bed",
           "Why? Carbon exhausted; change-out on calendar with no breakthrough check"],
      category="Material", prevent="Quarterly VOC check after the guard bed; weekly coalescer oil log"),
    K("KB-0717", ["Membrane"], ["analyser", "calibration", "methane purity"], "MEM-01 tripped on 94% purity; portable read 96.5%",
      "CH4 analyser drift — calibration overdue",
      "Calibrated analyser with certified gas, changed sample filter, released MEM-01",
      why=["Why trip? Analyser read low", "Why? Drift since last calibration 4 months ago",
           "Why? Analyser not on calibration schedule"],
      category="Measurement", prevent="Weekly zero/span; monthly calibration in PM"),
]
