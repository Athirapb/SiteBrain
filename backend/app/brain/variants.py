"""Equipment types (variants) within an equipment kind, and what SiteBrain must understand before troubleshooting.

"Pump" or "Agitator" is not enough to troubleshoot: a progressive cavity pump has a rubber stator that burns out in
seconds when run dry, and must never be run against a closed valve; a centrifugal pump is shut-off tested exactly
that way. A submersible mixer has no gland or coupling to inspect; a top-entry agitator has a roof seal that can leak
gas. So before any check, SiteBrain works out which type the equipment is (inferred from its name and area,
confirmed by the field operator, then remembered on the equipment), what it does in the process, and how it works.

  VARIANTS  per kind: the types found on biogas / CBG plants, each with
            look     how to tell it apart in the field
            works    how it works, in two plain sentences
            normal   what normal looks like (the few readings that matter)
            cautions what must never be done to this type (also given to the LLM)
            names    name patterns that identify it; areas: area codes where it is the usual type
            bias     prior multipliers for the kind's causes under this type (0 drops the cause)
            drop     checks that don't apply to this type, or are unsafe on it
            causes / checks  causes and checks only this type has (with their 5-Why trees)
            evidence what the kind's existing checks say about this type's own causes
  ROLES     what an equipment does in the process, by its name (the process-flow part of the understanding)

`apply(tree, variant)` gives the tree the engine uses for that type.
"""
import copy
import re

from .dsl import B, C, Q, R, W, is_normal_answer

# The type's own causes start as likely as a typical mechanical cause of the kind
PRIOR = 1.0


def V(id, label, look, works, normal, names=(), areas=(), cautions=(), bias=None, drop=(), causes=(), checks=(),
      evidence=None, default=False, sure=False):
    """sure: a name match settles the type (a "Bagging Machine" is a bagging machine) — no need to ask."""
    return {"id": id, "label": label, "look": look, "works": works, "normal": list(normal), "names": list(names),
            "areas": list(areas), "cautions": list(cautions), "bias": dict(bias or {}), "drop": list(drop),
            "causes": list(causes), "checks": list(checks), "evidence": list(evidence or []), "default": default,
            "sure": sure}


def _c(id, label, category, keys, steps, why, domain="mechanical"):
    c = C(id, label, category, keys, steps, why=why)
    c.update(domain=domain, prior=PRIOR)
    return c


PD_PUMP_CAUTION = ("Positive-displacement pump: never run it against a closed discharge valve (no shut-off test) — "
                   "pressure climbs until a pipe, seal or the pump gives way")

VARIANTS: dict[str, list[dict]] = {
    "Pump": [
        V("centrifugal", "Centrifugal pump",
          look="Round spiral (volute) casing, suction on the end and discharge on top; impeller inside, motor "
               "coupled directly. Smooth, steady flow.",
          works="A spinning impeller throws the liquid outward and builds pressure. Flow drops as the delivery "
                "pressure rises; it needs a flooded suction and must not run dry.",
          normal=["discharge pressure steady at the duty point", "seal dry or a slight weep",
                  "bearings below 70 °C"],
          names=[r"water", r"cooling", r"chiller", r"service"],
          cautions=["Don't run it dry or with the discharge valve shut for more than a few seconds"],
          bias={"imp": 0.6}),
        V("lobe", "Rotary lobe pump",
          look="Square-ish pump head with a flat front cover; two shafts side by side behind it, a timing-gear box, "
               "and suction and discharge ports opposite each other. Flow pulses slightly.",
          works="Two lobed rotors, timed by gears, turn in opposite directions and carry pockets of slurry from "
                "suction to discharge. It's positive displacement: flow stays almost the same as the pressure rises.",
          normal=["discharge pressure steady, no knocking", "quench / seal chamber clean, no slurry",
                  "timing-gear oil at level and clean"],
          names=[r"\bRC\b", r"transfer", r"intermediate", r"\bLDT\b", r"\bSBT\b", r"^H[12] "], default=True,
          cautions=[PD_PUMP_CAUTION, "Fit or check the pressure relief / high-pressure switch before running"],
          bias={"imp": 0.3, "wear": 1.6, "cav": 0.8}, drop=["shutoff"],
          causes=[_c("v_timing", "Timing gear or shaft bearing worn — lobes touch each other or the casing", "Machine",
                     ["timing", "lobes touching", "knock", "rubbing", "gear"], [
                         "Stop and isolate under LOTO",
                         "Check the timing-gear oil level and colour; drain a sample for metal",
                         "Open the front cover: look for lobe-to-lobe or lobe-to-casing rub marks",
                         "Replace the worn gears / bearings and re-time the lobes to the OEM clearances"],
                     W("Why did the timing gear or bearings wear?", [
                         B("Gear oil low, old or contaminated", R(
                             "Timing-gearbox oil is not in the PM plan", "Method",
                             prevent=["Add the gear oil level and change to the PM plan",
                                      "Check the gearbox oil on the weekly round"])),
                         B("Slurry got past the seal into the gearbox", R(
                             "Seal / quench chamber is not checked, so leaks reach the gearbox", "Method",
                             prevent=["Check the quench chamber every shift; change seals at the first slurry "
                                      "trace"])),
                         B("Run against high pressure or a blockage", R(
                             "No high-pressure protection on the PD pump", "Machine",
                             prevent=["Fit a high discharge-pressure trip and relief valve"])),
                     ]))],
          checks=[Q("v_lobes", "With the pump stopped under LOTO, look at the timing-gear oil and, if the front cover "
                               "is open, the lobes. What do you find?", [
              ("Normal — oil clean, lobes even, no rub marks", {"v_timing": 0.15, "wear": 0.6}),
              ("Rub marks or lobes touching, or metal in the gear oil", {"v_timing": 7.0}),
              ("Lobes and wear plates worn thin or grooved", {"wear": 4.0, "v_timing": 1.3}),
              ("Slurry in the quench chamber or gear oil", {"seal": 3.0, "v_timing": 2.0}),
          ], ["timing", "lobes", "knock", "rubbing"],
              how="Under LOTO with the lines isolated and drained: check the gear oil sight glass, take a small oil "
                  "sample, then open the front cover and look at the lobe tips and the wear plates.",
              purpose="Worn timing lets the lobes touch — it knocks, wears fast and loses flow.")],
          evidence=[("noise", r"rhythmic thump", {"v_timing": 2.5}),
                    ("noise", r"grinding|whine", {"v_timing": 2.0}),
                    ("dp", r"low but steady", {"v_timing": 1.3})]),
        V("pc", "Progressive cavity pump",
          look="Long, thin pump: a tube-shaped stator housing between the suction chamber and the discharge, with "
               "the motor and gearbox at the far end. Very smooth flow.",
          works="A single helical rotor turns inside a rubber stator and moves sealed cavities of slurry along. It's "
                "positive displacement and gives steady, pulse-free flow, ideal for dosing thick slurry.",
          normal=["discharge pressure steady", "stator housing barely warm", "output matches the speed setting"],
          names=[r"decanter feed", r"mud", r"dosing"],
          cautions=[PD_PUMP_CAUTION,
                    "Never run it dry — the rubber stator burns out in seconds; the dry-run protection must work"],
          bias={"imp": 0.3, "wear": 1.6}, drop=["shutoff"],
          causes=[_c("v_stator", "Stator damaged by dry running or over-pressure (rubber burnt, torn or swollen)",
                     "Machine", ["stator", "dry run", "ran dry", "rubber", "burnt"], [
                         "Stop the pump; don't restart until the stator is checked",
                         "Isolate under LOTO, drain, and pull the stator: look for burnt, torn or swollen rubber",
                         "Replace the stator (and rotor if scored); check the dry-run protection works",
                         "Restart with the suction flooded and the discharge valve open"],
                     W("Why did the stator get damaged?", [
                         B("It ran dry — tank empty or suction blocked", R(
                             "Dry-run protection missing, bypassed or not tested", "Measurement",
                             prevent=["Fit / test the stator temperature or flow dry-run sensor monthly",
                                      "Interlock the pump on the suction tank low level"])),
                         B("It ran against a closed valve", R(
                             "No high-pressure trip, and valve line-up not checked before starting", "Method",
                             prevent=["Fit a high discharge-pressure trip",
                                      "Add the valve line-up to the pump start checklist"])),
                         B("The rubber swelled — wrong elastomer for the slurry", R(
                             "Stator elastomer not chosen for the slurry's temperature and oils", "Material",
                             prevent=["Specify the stator elastomer for the slurry with the OEM"])),
                     ]))],
          checks=[Q("v_dryrun", "Has it run dry or against a closed valve recently — and how is the stator housing?", [
              ("Normal — no dry run, housing barely warm", {"v_stator": 0.15}),
              ("It ran dry or against a closed valve", {"v_stator": 7.0, "o_sop": 1.5}),
              ("Output low, stator hot, or rubber bits in the outlet", {"v_stator": 5.0, "wear": 2.0}),
          ], ["stator", "dry run", "rubber"],
              how="Ask the operators and look at the trip / alarm log for dry-run or high-pressure trips. Feel the "
                  "stator housing with the back of your hand or use the IR gun; look for rubber in the outlet strainer.",
              purpose="A few seconds of dry running destroys the rubber stator, and the pump then loses flow.")],
          evidence=[("dp", r"low but steady", {"v_stator": 2.0}),
                    ("dp", r"low and fluctuating", {"v_stator": 1.5})]),
        V("submersible", "Submersible / chopper pump",
          look="Sits under the slurry in a pit or tank, lowered on guide rails; only the discharge pipe, lifting "
               "chain and power cable are visible.",
          works="A sealed motor directly drives a centrifugal impeller (often with a chopper / cutter) under the "
                "slurry. The motor is cooled by the liquid around it and protected by seal-leak and temperature "
                "sensors.",
          normal=["discharge pressure steady", "no seal-leak or over-temperature alarm",
                  "current steady near nameplate"],
          names=[r"submersible", r"sump", r"pit"],
          cautions=["Lift it out only on the chain with the power isolated and locked off — never by the cable"],
          bias={"mis": 0}, drop=["flush", "align", "oil"]),
    ],
    "Agitator": [
        V("side_entry", "Side-entry agitator",
          look="Motor and gearbox outside the tank wall, with a horizontal shaft going through the wall at a gland "
               "or seal. The propeller is inside, below the level.",
          works="A propeller on a horizontal shaft through the tank wall pushes the contents round the tank. A motor "
                "and gearbox outside drive it, and the shaft passes through a gland (packing or mechanical seal) "
                "that keeps the slurry in.",
          normal=["gearbox bearing below 70 °C", "gland weeping 10–20 drops a minute", "current steady"],
          names=[r"side agitator", r"^D\d agitator"], default=True),
        V("top_entry", "Top-entry agitator",
          look="Motor and gearbox on the tank roof with a long vertical shaft hanging down into the tank; paddles or "
               "hydrofoils near the bottom. Turns slowly.",
          works="A long vertical shaft hangs from a roof gearbox and its paddles turn slowly to mix the whole tank. "
                "There's no bottom bearing, so imbalance shows as shaft swing and vibration at the gearbox; a roof "
                "seal keeps the gas in.",
          normal=["gearbox bearing below 70 °C", "no gas at the roof seal", "current steady, no swing"],
          names=[r"top agitator"],
          cautions=["Gas-test at the roof seal before working on the drive — the roof is in the gas zone"],
          bias={"gland": 0, "sed": 1.3, "rag": 1.3}, drop=["drip"],
          causes=[_c("v_roofseal", "Roof shaft seal leaking gas (worn seal or shaft run-out)", "Machine",
                     ["roof seal", "gas smell", "gas at the roof", "shaft seal"], [
                         "Keep clear and gas-test around the roof seal; tell the control room",
                         "Isolate the agitator under LOTO and depressurise the digester gas space as per the permit",
                         "Check shaft run-out at the seal; replace the seal (and fix run-out) to the OEM procedure",
                         "Gas-test again after restart"],
                     W("Why did the roof seal start leaking?", [
                         B("Seal worn out — past its life", R(
                             "Roof seals are not on a gas-check round or replacement plan", "Method",
                             prevent=["Gas-test roof seals on the weekly round",
                                      "Replace roof seals on a planned interval"])),
                         B("Shaft runs out — swinging from imbalance", R(
                             "Paddle build-up / imbalance is not checked at shutdowns", "Method",
                             prevent=["Measure shaft run-out yearly; clean the paddles when the tank is emptied"])),
                         B("Seal fluid / water seal ran dry", R(
                             "Seal liquid level is not checked", "Man",
                             prevent=["Add the seal liquid level to the daily round"])),
                     ]), domain="mechanical")],
          checks=[Q("v_roofgas", "Sweep the roof seal and gearbox flange with the gas detector. What does it read?", [
              ("0% LEL at the seal", {"v_roofseal": 0.1}),
              ("Gas detected at the roof seal", {"v_roofseal": 9.0}, ["gas_leak"]),
          ], ["gas", "roof", "seal", "smell"],
              how="Approach upwind with the portable detector on; hold it at the roof seal and gearbox flange for "
                  "10 s each. Don't climb the roof alone.",
              purpose="A leaking roof seal releases biogas — a safety problem first and a seal problem second.")]),
        V("submersible", "Submersible mixer",
          look="Nothing outside the tank but a mast / guide rail, a winch and the power cable; the motor and "
               "propeller are under the slurry.",
          works="A sealed motor and gearbox under the slurry turn a propeller directly; it's raised and lowered on a "
                "guide mast to set the height and angle. Seal-leak (moisture) and motor temperature sensors protect "
                "it.",
          normal=["no seal-leak or over-temperature alarm", "current steady", "even surface movement"],
          names=[r"submersible", r"mixer"], areas=["PST", "CDT"],
          cautions=["Raise it only with the winch, power isolated and locked off — never by the cable"],
          bias={"mis": 0, "gland": 0, "lube": 0, "sensor": 0},
          drop=["coupling", "drip", "oil", "temp", "leak", "handheld"],
          causes=[_c("v_subseal", "Seal failure — slurry / water into the motor (seal-leak or over-temperature "
                                  "alarm)", "Machine", ["seal leak", "moisture alarm", "leakage sensor", "thermal"], [
                         "Stop the mixer and isolate it at the MCC under LOTO",
                         "Raise it on the mast; check the oil chamber for water and the cable entry for damage",
                         "Electrician: insulation test the motor",
                         "Replace the mechanical seals / dry out or send the motor for repair"],
                     W("Why did the seal let water in?", [
                         B("Seals worn — past their service interval", R(
                             "Submersible mixers are not lifted for seal service on time", "Method",
                             prevent=["Lift and service each mixer at the OEM interval (oil chamber, seals)"])),
                         B("Rags or fibre wrapped the shaft and damaged the seal", R(
                             "Feed is not screened for long fibre and rags", "Material",
                             prevent=["Screen out rags / plastic; inspect the propeller when lifting"])),
                         B("Seal-leak alarm was ignored or not wired", R(
                             "Seal-leak sensor alarm is not wired to the control room", "Measurement",
                             prevent=["Wire the seal-leak sensor to SCADA and act on the first alarm"])),
                     ]))],
          checks=[Q("v_sensors", "What does the mixer's control box show for the seal-leak (moisture) and motor "
                                 "temperature sensors?", [
              ("Normal — no alarms", {"v_subseal": 0.15}),
              ("Seal-leak / moisture alarm", {"v_subseal": 8.0}),
              ("Motor over-temperature tripped", {"v_subseal": 3.0, "sed": 1.5, "e_motor": 2.0}),
          ], ["seal leak", "moisture", "thermal", "alarm"],
              how="Look at the mixer's protection relay in the MCC or local panel (seal-leak / moisture and thermal "
                  "lamps or codes), or ask the control room.",
              purpose="The seal-leak sensor gives early warning before water reaches the motor windings.")]),
    ],
    "Blower": [
        V("gas_booster", "Biogas booster blower",
          look="A blower in the gas line with condensate drains and a knock-out pot before it, often in an enclosure "
               "with gas detection; flanged gas pipes in and out.",
          works="An impeller (single or multistage) raises the biogas pressure by tens of millibar to push it "
                "through the gas train or to the flare. It handles wet, corrosive, flammable gas, so condensate must "
                "be drained before it and every joint and seal must be gas-tight.",
          normal=["0% LEL around it", "bearings below 70 °C", "suction and discharge pressure steady"],
          names=[r"gas blower", r"flare blower"], default=True),
        V("support_air", "Membrane-roof support-air blower",
          look="A small radial fan beside the digester or tank feeding air into the double-membrane roof through a "
               "non-return flap; an air relief valve on the roof.",
          works="It blows air into the space between the outer and inner membranes of the double-membrane gas "
                "holder, keeping the outer membrane taut and setting the gas pressure. It runs continuously; a "
                "non-return flap stops backflow and a relief valve sets the air pressure.",
          normal=["support-air pressure steady at its setting", "outer membrane taut, not flapping",
                  "no CH4 in the exhaust air"],
          names=[r"^D\d blower", r"top blower", r"support"],
          cautions=["Gas in the support air means the inner membrane leaks — treat as a gas hazard"],
          bias={"gasket": 0, "cond": 0, "p_suction": 0}, drop=["drain", "trap", "p_holder"],
          causes=[_c("v_airleak", "Outer membrane or air system leaking — relief valve stuck open, torn membrane or "
                                  "loose clamping (blower can't hold pressure)", "Environment",
                     ["membrane", "roof", "flapping", "slack", "air pressure", "relief valve"], [
                         "Tell the control room; keep the standby blower running if pressure is falling",
                         "Check the air relief valve and the non-return flap are seating",
                         "Walk the clamping rail and look at the outer membrane for tears (from the ground or a safe "
                         "platform)",
                         "Repair the membrane / clamping with the OEM; re-check the support pressure holds"],
                     W("Why is the roof losing air?", [
                         B("Relief valve or non-return flap stuck open", R(
                             "Roof air valves are not checked on the rounds", "Method",
                             prevent=["Check relief valve and flap seating weekly"])),
                         B("Membrane torn by wind or ageing", R(
                             "Membranes are not inspected after storms or by age", "Environment",
                             prevent=["Inspect the membrane after high winds; plan replacement by age"])),
                         B("Clamping rail loose", R(
                             "Clamping rail bolts are not re-torqued", "Method",
                             prevent=["Re-torque the clamping rail yearly"])),
                     ]), domain="process")],
          checks=[Q("v_roofair", "How is the support-air pressure holding, and how does the outer membrane look?", [
              ("Normal — pressure steady, membrane taut", {"v_airleak": 0.15}),
              ("Pressure low or falling, membrane slack or flapping", {"v_airleak": 6.0, "brg": 0.8}),
              ("Air escaping at the relief valve or clamping rail", {"v_airleak": 8.0}),
          ], ["membrane", "roof", "slack", "flapping", "air pressure"],
              how="Read the support-air pressure on the HMI or the roof manometer, and look at the membrane from the "
                  "ground: taut and smooth is normal.",
              purpose="If the roof loses air the blower can't keep up — the fault is in the roof, not the blower.")]),
    ],
    "Compressor": [
        V("recip", "Reciprocating compressor",
          look="Crankcase with cylinders on top or to the side, valve covers on each cylinder, a flywheel or "
               "coupling to the motor, coolers between stages. Rhythmic beat when running.",
          works="Pistons draw gas in through suction valves and push it out through discharge valves, in one or "
                "more stages with coolers between. Crankcase oil lubricates the running gear and rod packing seals "
                "the gas at each piston rod.",
          normal=["crankcase oil 60–80 %", "stage discharge temperatures at the usual values",
                  "0% LEL at flanges and packing vent"],
          names=[r"^LP \d", r"^HP \d"], default=True),
        V("screw", "Oil-injected screw air compressor",
          look="A packaged box with a control panel, a separator tank (oil/air receiver) inside, an air-cooled oil "
               "cooler and an intake filter. Continuous hum, no beat.",
          works="Two meshing helical rotors squeeze air continuously; injected oil seals, cools and lubricates, then "
                "is separated from the air in the separator tank. It loads and unloads on pressure through an inlet "
                "valve.",
          normal=["oil / element temperature 75–95 °C", "loads and reaches the set pressure",
                  "separator dP below the change limit"],
          names=[r"plant air", r"air comp", r"instrument air"],
          bias={"oilleak": 0, "valve": 0, "particle": 0, "liquid": 0, "rings": 0, "gasket": 0, "p_suction": 0, "cooling": 0},
          drop=["knock", "oil", "strainer", "gasdet", "valvetemp", "breather", "upstream", "interstage", "dischtemp",
                "p_supply"],
          causes=[
              _c("v_sep", "Oil separator element choked, or oil carry-over into the air", "Material",
                 ["separator", "oil in air", "oil carryover", "separator dp"], [
                     "Stop and depressurise; isolate under LOTO",
                     "Replace the separator element and check the scavenge line orifice / strainer",
                     "Check the oil level isn't overfilled and the oil grade is right",
                     "Drain the air receiver and line drains; restart and check separator dP"],
                 W("Why did the separator choke or carry over?", [
                     B("Element past its change interval", R(
                         "Separator element is not changed by hours", "Method",
                         prevent=["Change the separator element at the OEM hours; log it"])),
                     B("Wrong or old oil, or overfilled", R(
                         "Oil grade / level not controlled at top-up", "Material",
                         prevent=["Label the oil grade on the machine; top up only to the mark"])),
                     B("Scavenge line blocked", R(
                         "Scavenge orifice is not cleaned in PM", "Method",
                         prevent=["Clean the scavenge orifice / strainer at every separator change"])),
                 ])),
              _c("v_inlet", "Inlet / unloader valve or intake filter fault — won't load, or low output", "Machine",
                 ["inlet valve", "unloader", "won't load", "low pressure", "intake filter"], [
                     "Check the intake filter and replace it if dirty",
                     "Watch the inlet valve open on load; check its solenoid and control air",
                     "Service or replace the inlet valve kit",
                     "Check the air demand isn't simply above the compressor's capacity (leaks!)"],
                 W("Why did it stop loading properly?", [
                     B("Intake filter choked", R(
                         "Intake filter is not on a change schedule", "Method",
                         prevent=["Change intake filters at the OEM interval, more often in dusty areas"])),
                     B("Inlet valve worn or solenoid failed", R(
                         "Inlet valve kits are not serviced by hours", "Method",
                         prevent=["Service the inlet valve kit at the OEM hours"])),
                     B("Air leaks downstream exceed its capacity", R(
                         "Compressed-air leaks are not surveyed", "Method",
                         prevent=["Quarterly leak survey of the air network"])),
                 ])),
              _c("v_oiltemp", "Oil too hot — thermostatic valve, oil cooler fouled or oil low (high-temperature "
                              "trip)", "Environment", ["high temperature", "oil temperature", "overheat", "cooler"], [
                     "Let it cool; check the oil level and top up with the right grade",
                     "Blow out / clean the oil cooler fins; check the cooling fan runs",
                     "Check the thermostatic valve opens (cooler gets hot when the oil is hot)",
                     "Improve room ventilation if the compressor room is hot"],
                 W("Why did the oil run hot?", [
                     B("Cooler fins clogged with dust", R(
                         "Cooler cleaning is not in the PM plan", "Method",
                         prevent=["Clean the oil cooler monthly"])),
                     B("Thermostatic valve stuck", R(
                         "Thermostatic valve is not checked at service", "Method",
                         prevent=["Check / replace the thermostatic element at each major service"])),
                     B("Hot, poorly ventilated room", R(
                         "Compressor room ventilation is inadequate", "Environment",
                         prevent=["Duct hot air out; keep louvres clear"])),
                 ])),
          ],
          checks=[
              Q("v_temp", "What does the controller show for the oil / element discharge temperature?", [
                  ("Normal, 75–95 °C", {"v_oiltemp": 0.15}),
                  ("High, above 100 °C, or high-temperature trip", {"v_oiltemp": 6.0}),
              ], ["temperature", "hot", "overheat", "trip"],
                  how="Read the element / oil temperature on the compressor controller display and the trip history.",
                  purpose="High oil temperature is the commonest screw-compressor trip and points to cooling."),
              Q("v_load", "Does it load and build up to the set pressure normally?", [
                  ("Normal — loads and reaches the set pressure", {"v_inlet": 0.15}),
                  ("Runs loaded, but the pressure won't build", {"v_inlet": 4.0, "v_sep": 1.5, "o_duty": 2.0}),
                  ("Won't load, or loads and unloads rapidly", {"v_inlet": 6.0, "e_control": 1.5}),
              ], ["load", "pressure", "won't load", "low pressure"],
                  how="Watch the controller: load / unload status and the line pressure for a few minutes.",
                  purpose="Loading problems point to the inlet valve, the intake or more demand than it can supply."),
              Q("v_sepdp", "On the controller, what do the separator dP and the oil level look like?", [
                  ("Normal — separator dP and oil level OK", {"v_sep": 0.15, "v_oiltemp": 0.8}),
                  ("Separator dP high, or oil in the air lines", {"v_sep": 7.0}),
                  ("Oil level low", {"v_oiltemp": 3.0, "v_sep": 1.5}),
              ], ["separator", "oil", "oil in air"],
                  how="Read the separator dP on the controller (or the gauge across the separator) and the oil sight "
                      "glass with the compressor unloaded.",
                  purpose="A choked separator wastes power and pushes oil into the air network."),
          ],
          evidence=[("cooler", r"weak flow|fouled", {"v_oiltemp": 2.5})]),
    ],
    "Chiller": [
        V("air_cooled", "Air-cooled chiller (gas dehydration)",
          look="Packaged unit with condenser coils and fans on top or on the sides; a gas–glycol heat exchanger and "
               "condensate separator on the gas line.",
          works="A refrigeration circuit chills glycol / water, which cools the compressed biogas in a heat exchanger "
                "to 2–5 °C so the water condenses and drains out before the membranes. The heat is rejected to air by "
                "the condenser fans.",
          normal=["gas outlet 2–5 °C", "condensate drain cycling", "sight glass clear"], default=True),
        V("water_cooled", "Water-cooled chiller (gas dehydration)",
          look="Packaged unit without condenser fans; water pipes from the cooling tower / cooling water pumps go to "
               "a shell-and-tube condenser.",
          works="A refrigeration circuit chills glycol / water, which cools the compressed biogas to 2–5 °C so the "
                "water condenses out. The heat is rejected to the cooling-water circuit and cooling tower.",
          normal=["gas outlet 2–5 °C", "cooling water flowing, tower fan running", "condensate drain cycling"],
          bias={"filter": 0}, drop=["cond"],
          causes=[_c("v_cw", "Condenser cooling water short — cooling tower or cooling water pump problem (high "
                             "condensing pressure)", "Environment",
                     ["cooling water", "cooling tower", "condenser", "high pressure"], [
                         "Check the cooling water pumps and the cooling tower fan are running",
                         "Clean the tower basin strainer; check the tower fill isn't blocked",
                         "Check / descale the condenser tubes if the approach temperature is high",
                         "Restart the chiller and watch the condensing pressure"],
                     W("Why was the condenser short of cooling water?", [
                         B("CW pump tripped or tower fan off", R(
                             "Cooling-water system faults are not alarmed to the chiller operator", "Measurement",
                             prevent=["Alarm CW flow / pressure low at the chiller"])),
                         B("Condenser tubes scaled", R(
                             "Cooling water treatment is not controlled", "Material",
                             prevent=["Dose and test cooling water weekly; descale yearly"])),
                         B("Tower basin strainer blocked", R(
                             "Tower basin is not cleaned on schedule", "Method",
                             prevent=["Clean the basin and strainer monthly"])),
                     ]), domain="process")],
          checks=[Q("v_cwcheck", "Check the condenser cooling water: are the CW pumps and the cooling tower fan running, "
                                 "and is the return warm?", [
              ("Flow good, tower fan running, return a few degrees warmer", {"v_cw": 0.15}),
              ("Low flow, CW pump tripped or tower fan off", {"v_cw": 7.0}),
              ("Return very hot / big approach, though flow is OK", {"v_cw": 3.0, "refrig": 1.3}),
          ], ["cooling water", "tower", "condenser"],
              how="Look at the CW pumps (one running, pressure normal), the tower fan, and feel or read the condenser "
                  "inlet and outlet water temperatures.",
              purpose="A water-cooled chiller can't reject heat without cooling water — the fault is outside the "
                      "chiller.")]),
    ],
    "Machine": [
        V("bagging", "Bagging machine",
          look="Hopper and auger / gravity filler over a spout, a weighing platform or load cells, and a bag "
               "clamp; often a conveyor or sealer after it.",
          works="An auger or gate meters solids from the hopper into a clamped bag while load cells weigh it, then "
                "releases the bag to the sealer / conveyor.",
          normal=["bag weights within ±0.5 %", "material flows freely from the hopper", "drive runs smoothly"],
          names=[r"bagging", r"packing", r"filling"], default=True, sure=True),
        V("briquetting", "Briquetting machine",
          look="Heavy frame with a feed hopper and screw, a ram or extrusion screw and a die where the briquettes "
               "come out; a big flywheel or gearbox drive.",
          works="A screw or ram forces dried solids through a heated or tapered die at high pressure, so the "
                "material binds into dense briquettes.",
          normal=["firm, dense briquettes", "feed moisture in the target band", "die temperature steady"],
          names=[r"briquett"], bias={"weigh": 0}, drop=["testwt"], sure=True),
    ],
    # one usual type here: shown in the understanding for the operator to confirm or correct
    "Decanter": [V("decanter", "Decanter centrifuge (solid-bowl, 2-phase)",
                   look="Horizontal machine with a long bowl in a casing, the main motor on one side and a gearbox / "
                        "back-drive at the other end; cake chute and centrate outlet underneath.",
                   works="The bowl spins at about 3,000 rpm so solids settle against its wall, and a scroll turning "
                         "slightly slower (the differential speed) pushes them out as cake while the liquid "
                         "(centrate) overflows at the other end. Polymer flocculates the solids first.",
                   normal=["dry cake and clear centrate", "torque and differential steady",
                           "main bearings below 75 °C"], default=True)],
    "WAM": [V("screw_press", "Screw press separator",
              look="Horizontal cylinder with a screen, an inlet on top from the feed pump, a gearmotor at one end "
                   "and the cake outlet with counter-pressure flaps at the other.",
              works="A screw turning inside a cylindrical screen squeezes the digestate: liquid (filtrate) passes "
                    "through the screen, the fibre is pressed into a plug against weighted outlet flaps and leaves "
                    "as cake.",
              normal=["steady cake of normal dryness", "filtrate with fines but no fibre",
                      "wash spray even, ≥2 bar"], default=True)],
    "Shredder": [V("twin_shaft", "Twin-shaft shredder line",
                   look="Two slow counter-rotating cutter shafts under a hopper, a heavy gearbox, and a conveyor "
                        "after it.",
                   works="Two slow, high-torque shafts with interlocking cutter discs tear and cut the feedstock; it "
                         "reverses automatically when it meets something hard. A conveyor carries the shredded "
                         "material on to the feed tanks.",
                   normal=["current steady near rated while feeding", "few auto-reverses", "belt centred, no slip"],
                   default=True)],
    "HWG": [V("biogas_hwg", "Biogas-fired hot water generator",
              look="Boiler shell with a forced-draft burner and gas train on the front, an ID fan and stack, flow and "
                   "return water pipes to the digester heating loop.",
              works="The burner fires biogas in the furnace; the hot flue gas heats the water, which is pumped to "
                    "the digester heat exchangers and back. The burner controller proves the air, gas pressure and "
                    "flame before and during firing.",
              normal=["flow–return ΔT about 8–12 °C", "flue O2 3–6 %, CO low", "gas pressure steady"],
              default=True)],
    "Scrubber": [V("dry_media", "Dry-media H2S scrubber",
                   look="Tall vessel in the raw-gas line with a top manhole and distributor; air / O2 dosing line "
                        "and an H2S analyser at the outlet.",
                   works="Raw biogas flows through a bed of iron-oxide (or impregnated) media that binds the H2S; a "
                         "little air dosed into the gas regenerates the media. The media is spent and changed when "
                         "the outlet H2S breaks through.",
                   normal=["outlet H2S below 10 ppm", "steady dP", "outlet O2 0.3–0.5 %"], default=True)],
    "Filter": [V("cartridge", "Cartridge gas filter skid",
                 look="Duty and guard filter housings with dP gauges, a locked bypass and drains, between the "
                      "scrubber and the blowers / compressors.",
                 works="Gas passes through cartridge elements that catch media fines, dust and droplets before the "
                       "compressors; dP rises as the elements load and they're changed at the limit.",
                 normal=["element dP steady at the usual value", "bypass closed and locked", "guard filter in service"],
                 default=True)],
    "Membrane": [V("hollow_fibre", "Hollow-fibre membrane upgrader",
                   look="Skid of long membrane modules (tubes) with feed, product (retentate) and permeate headers, a "
                        "tail-gas recycle valve and CH4 analysers.",
                   works="Compressed, dried gas flows along hollow fibres; CO2 passes through the fibre wall faster "
                         "than methane, so the gas left inside becomes CBG above 95 % CH4. The CO2-rich permeate goes "
                         "to vent / flare and part of it is recycled to raise recovery.",
                   normal=["product CH4 above 95 %", "feed 12–15 bar, 2–5 °C dew point", "permeate dP at baseline"],
                   default=True)],
}

# What each equipment does in the process, by name (first match wins), then by kind
ROLES = [
    (r"decanter feed pump", "Feeds digestate at a steady rate into the decanter centrifuge."),
    (r"^D\d RC pump", "Recirculates the digester contents — draws slurry from the digester and returns it (through "
                      "the heat exchanger where fitted) to keep it mixed and at temperature."),
    (r"RC pump", "Recirculates the tank contents to keep the solids suspended and the feed even."),
    (r"transfer pump", "Transfers digestate out of the digester to hold its level (on to the next tank or to "
                       "separation)."),
    (r"^H[12] pump", "Pumps mixed feed slurry from the feed tank into the digesters."),
    (r"PST pump", "Pumps primary sludge from the primary sludge tank to the digesters."),
    (r"intermediate pump", "Moves digestate between the separation stages."),
    (r"mud pump", "Pumps thickened digestate out of the concentrated digestate tank."),
    (r"SBT pump", "Pumps slurry out of the SBT."),
    (r"LDT pump", "Pumps liquid digestate out of the liquid digestate tank (LDT)."),
    (r"service water", "Supplies service water for washing, seal flushing and make-up."),
    (r"cooling water pump", "Circulates cooling water through the compressor and process coolers and the cooling "
                            "tower."),
    (r"chiller pump", "Circulates chilled glycol / water between the chiller and the gas cooler."),
    (r"^D\d (top )?agitator", "Mixes the digester so fresh feed meets the bacteria, the temperature stays even, gas "
                              "escapes and sand and scum don't build up."),
    (r"^(H[12]|SBT) .*agitator", "Keeps the feed slurry mixed and the solids suspended before it's pumped to the "
                                 "digesters."),
    (r"agitator|mixer", "Keeps the solids in suspension so the pumps get an even slurry."),
    (r"^D\d blower|top blower", "Keeps the outer membrane of the double-membrane gas holder inflated with support "
                                "air."),
    (r"flare blower", "Boosts surplus or off-spec gas to the flare so it's burnt safely."),
    (r"gas blower", "Boosts raw biogas from the gas holders through the H2S scrubber and filters to the LP "
                    "compressors."),
    (r"^LP \d", "Compresses cleaned biogas to about 12–15 bar for the chiller and membrane upgrader."),
    (r"^HP \d", "Compresses the upgraded CBG (above 95 % CH4) to about 250 bar for the cascade / dispatch."),
    (r"plant air", "Supplies compressed air for instruments, actuated valves and the separation equipment."),
    (r"bagging", "Fills and weighs bags of the solid product."),
    (r"briquett", "Presses dried solids into briquettes."),
]
KIND_ROLE = {
    "Decanter": "Separates digestate into dry cake and liquid centrate, with polymer.",
    "WAM": "Separates digestate into fibre cake and liquid filtrate.",
    "Shredder": "Cuts the incoming feedstock to size and conveys it to the feed tanks.",
    "HWG": "Burns biogas to heat the water that keeps the digesters at temperature.",
    "Chiller": "Cools the compressed biogas to 2–5 °C so the water condenses out before the membranes.",
    "Scrubber": "Removes H2S from the raw biogas before the blowers and compressors.",
    "Filter": "Catches dust, media fines and droplets in the gas before the compressors.",
    "Membrane": "Separates CO2 from the biogas to make CBG above 95 % methane.",
}


def variants(kind: str | None) -> list[dict]:
    return VARIANTS.get(kind or "", [])


def get(kind: str | None, vid: str | None) -> dict | None:
    return next((v for v in variants(kind) if v["id"] == vid), None)


def role(eq: dict) -> str:
    name = eq.get("name") or ""
    for pat, text in ROLES:
        if re.search(pat, name, re.I):
            return text
    return KIND_ROLE.get(eq.get("kind"), f"{eq.get('kind') or 'Equipment'} in {eq.get('unit_name') or 'this area'}.")


def infer(eq: dict) -> tuple[dict | None, str]:
    """The most likely type of an equipment, and why: ('name' — its name suggests it, 'area' — the usual type in that
    area, 'usual' — the usual type for this kind, 'only' — the kind has one type here). None when the kind has none."""
    vs = variants(eq.get("kind"))
    if not vs:
        return None, ""
    if len(vs) == 1:
        return vs[0], "only"
    name = eq.get("name") or ""
    by_name = [v for v in vs if any(re.search(p, name, re.I) for p in v["names"])]
    if by_name:
        return by_name[0], "name"
    by_area = [v for v in vs if eq.get("unit") in v["areas"]]
    if by_area:
        return by_area[0], "area"
    return next((v for v in vs if v["default"]), vs[0]), "usual"


def match(kind: str | None, text: str) -> dict | None:
    """The type a reply names: its label, or most of the label's words ('lobe', 'PC pump', 'progressive cavity')."""
    t = (text or "").lower()
    vs = variants(kind)
    exact = next((v for v in vs if v["label"].lower() == t.strip() or t.strip() == f"yes, {v['label'].lower()}"),
                 None)
    if exact:
        return exact
    aliases = {"pc": ["pc pump", "progressive", "mono pump", "eccentric screw", "helical rotor"],
               "lobe": ["lobe", "roots"], "centrifugal": ["centrifugal", "end suction", "volute"],
               "submersible": ["submersible", "chopper", "sump pump", "under the slurry", "mixer on a mast"],
               "side_entry": ["side entry", "side-entry", "through the wall", "horizontal shaft"],
               "top_entry": ["top entry", "top-entry", "vertical shaft", "roof mounted", "on the roof", "paddle"],
               "support_air": ["support air", "membrane roof", "roof blower", "air blower"],
               "gas_booster": ["booster", "gas blower"], "recip": ["reciprocating", "piston"],
               "screw": ["screw compressor", "rotary screw", "screw air"],
               "water_cooled": ["water cooled", "water-cooled", "cooling tower"],
               "air_cooled": ["air cooled", "air-cooled", "condenser fan"],
               "bagging": ["bagging", "bag filler"], "briquetting": ["briquett"]}
    hits = [v for v in vs if any(a in t for a in aliases.get(v["id"], []))]
    return hits[0] if len(hits) == 1 else None


def apply(tree: dict, v: dict | None) -> dict:
    """The tree for one type: its causes dropped or re-weighted, its own causes and checks added, unsafe or
    irrelevant checks removed."""
    if not v:
        return tree
    t = copy.deepcopy(tree)
    gone = {c for c, m in v["bias"].items() if m == 0}
    t["causes"] = [c for c in t["causes"] if c["id"] not in gone]
    for c in t["causes"]:
        if c["id"] in v["bias"]:
            c["prior"] = c.get("prior", 1.0) * v["bias"][c["id"]]
    own = [copy.deepcopy(c) for c in v["causes"]]
    t["causes"] += own
    ids = {c["id"] for c in t["causes"]}
    t["questions"] = [q for q in t["questions"] if q["id"] not in v["drop"]]
    for q in t["questions"]:
        for o in q["options"]:
            for cid in gone:
                o["lik"].pop(cid, None)
            hit = next((lik for qid, pat, lik in v["evidence"] if qid == q["id"] and re.search(pat, o["label"], re.I)),
                       None)
            for c in own:
                if hit and c["id"] in hit:
                    o["lik"][c["id"]] = hit[c["id"]]
                else:
                    o["lik"].setdefault(c["id"], 1.3 if is_normal_answer(o["label"]) else 0.7)
    t["questions"] += [{**copy.deepcopy(q), "options": [{**o, "lik": {c: x for c, x in o["lik"].items() if c in ids}}
                                                        for o in q["options"]]} for q in v["checks"]]
    t["variant"] = v["id"]
    return t


# ---------------------------------------------------------------------------
# Clarifying questions before troubleshooting: its state now, and how the problem started
# ---------------------------------------------------------------------------
# Each answer re-weights the fishbone by the kind of cause it points to (domain), with a few causes named outright.

STATIC_KINDS = {"Scrubber", "Filter", "Membrane"}
STATE = {
    "rotating": [
        ("Running, but not right", {"electrical": 0.6, "mechanical": 1.2, "process": 1.2}, {"e_control": 0.4}),
        ("Stopped — it tripped", {"electrical": 1.8, "mechanical": 0.9, "operational": 1.2, "instrument": 1.5},
         {"o_cycling": 1.5}),
        ("Won't start", {"electrical": 2.5, "mechanical": 0.5, "process": 0.6, "instrument": 1.5},
         {"e_control": 3.0, "o_sop": 1.5}),
        ("Keeps stopping and starting", {"electrical": 1.5, "mechanical": 0.7, "process": 1.5, "operational": 1.5},
         {"o_cycling": 3.0, "e_control": 2.0, "e_protect": 2.0, "p_conn": 1.5}),
    ],
    "static": [
        ("In service, but performing badly", {}, {}),
        ("Bypassed or taken offline", {"operational": 1.5}, {"bypass": 2.0, "o_sop": 1.5}),
    ],
}
ONSET = [
    ("Suddenly", {"electrical": 1.3, "process": 1.2, "operational": 1.2}, {}),
    ("Got worse over days or weeks", {"electrical": 0.7, "mechanical": 1.4, "operational": 0.6, "instrument": 1.2}, {}),
    ("Right after maintenance or a change", {"operational": 1.5},
     {"o_sop": 3.0, "o_change": 3.0, "mis": 2.5, "install": 2.5, "bypass": 2.0}),
]


def state_options(kind: str | None) -> list[tuple]:
    return STATE["static" if kind in STATIC_KINDS else "rotating"]


def reweigh(tree: dict, post: dict, picked: list[tuple]) -> dict:
    """The fishbone's starting likelihoods after the clarifying answers (each a (label, domain ×, cause ×) entry)."""
    dom = {c["id"]: c.get("domain") or "mechanical" for c in tree["causes"]}
    out = dict(post)
    for _, by_domain, by_cause in picked:
        for cid in out:
            if cid in dom:
                out[cid] *= by_cause.get(cid, by_domain.get(dom[cid], 1.0))
    t = sum(out.values()) or 1.0
    return {k: v / t for k, v in out.items()}
