"""Electrical and operational causes shared by every equipment type.

The equipment trees (pumps.py, agitation.py, …) describe the mechanical and process failures of each machine. A
machine also stops or misbehaves because of its electrical system (supply, motor, starter / VFD, protection,
controls) or because of how it is operated (outside its design duty, SOP steps missed, a recent change, too many
starts). Those causes and their checks are the same for every motor-driven machine, so they are written once here
and added to each tree by extend():

  ELECTRICAL   added to motor-driven equipment
  OPERATIONAL  added to every equipment type (static gas-train units get the ones that apply to them)
  checks       added unless the tree already asks the same thing (its own motor-current or setting-change check)
  CROSS        evidence for these causes from answers the trees already have ("Unequal between phases", "Trips
               with normal current", "Yes, changed recently" …)

Each cause carries a `domain` (electrical / operational / mechanical / process / instrument) shown next to it in the
chat, so the field operator sees that electrical and operating causes are being considered too.
"""
import re

from .dsl import B, C, Q, R, W, is_normal_answer

MOTOR_KINDS = {"Pump", "Agitator", "Blower", "Compressor", "Decanter", "Machine", "Shredder", "WAM", "Chiller", "HWG"}
STATIC_KINDS = {"Scrubber", "Filter", "Membrane"}

# Before any check, an electrical or operating cause is about half as likely as a typical mechanical one
PRIOR = 0.35

E = ["e_supply", "e_motor", "e_drive", "e_protect", "e_control"]
O = ["o_duty", "o_sop", "o_change", "o_cycling"]


def _c(id, label, category, domain, keys, steps, why):
    c = C(id, label, category, keys, steps, why=why)
    c.update(domain=domain, prior=PRIOR)
    return c


ELECTRICAL = [
    _c("e_supply", "Power supply problem — low or unbalanced voltage, or a lost phase (single-phasing)", "Environment",
       "electrical", ["voltage", "phase", "power cut", "power dip", "supply", "single phasing", "dg "], [
           "Stop the machine and call the shift electrician — do not keep resetting the trip",
           "Electrician: measure the three line voltages at the MCC incomer and at the motor terminals "
           "(unbalance should be below 2 %)",
           "Check fuses, MCB / MCCB and contactor contacts on all three phases; replace failed parts",
           "Restart and record the three phase currents — they should be within 5 % of each other"],
       W("Why was the supply wrong?", [
           B("A fuse or contact on one phase failed", R(
               "Loose or overheated connections in the MCC are not found before they fail", "Machine",
               prevent=["Thermographic scan of MCC panels every quarter",
                        "Re-torque power terminals during the annual shutdown"])),
           B("Grid or DG voltage was low or unbalanced", R(
               "No phase-failure / unbalance relay protecting the motor", "Machine",
               prevent=["Fit a phase-failure and unbalance relay on critical motors",
                        "Trend incomer voltages on SCADA with a low-voltage alarm"])),
           B("Many motors restarted together on a weak supply", R(
               "No staggered restart sequence after a power dip or DG changeover", "Method",
               prevent=["Add a staggered restart sequence to the PLC for when power returns"])),
       ])),
    _c("e_motor", "Motor winding or insulation fault (overheating, moisture, earth fault)", "Machine", "electrical",
       ["motor", "burning", "smell", "insulation", "earth fault", "winding", "smoke"], [
           "Isolate at the MCC, lock out and try-start to prove it dead (electrician)",
           "Electrician: insulation resistance test (megger) phase-to-earth and phase-to-phase, and winding "
           "resistance balance",
           "If insulation is low, dry the motor out or send it for rewinding; fit the standby motor if there is one",
           "Clean the cooling fins and fan cowl; restart and record current and motor temperature after 1 h"],
       W("What damaged the winding or its insulation?", [
           B("Water or moisture in the motor or terminal box", R(
               "Terminal boxes and glands not sealed against rain and washdown", "Environment",
               prevent=["Fit correct cable glands and gaskets; add canopies on outdoor motors",
                        "Megger outdoor motors before and after the monsoon; anti-condensation heaters on large motors"])),
           B("It ran overloaded or hot for a long time", R(
               "Motor current and temperature are not trended, so overloads go unnoticed", "Measurement",
               prevent=["Trend motor current on SCADA with a warning below the trip setting",
                        "Clean cooling fins and fan cowls on the weekly round"])),
           B("Too many starts in a short time", R(
               "Start / stop frequency exceeds the motor rating (no restart limit)", "Method",
               prevent=["Limit restarts per hour in the PLC to the motor datasheet value",
                        "Find the cause of repeated trips before resetting"])),
           B("Old motor — insulation aged out", R(
               "Insulation resistance is not tracked, so motors fail without warning", "Method",
               prevent=["Record yearly insulation resistance in the motor register; plan rewinds when it trends down"])),
       ])),
    _c("e_drive", "Starter or VFD fault — contactor, loose termination, or drive trip / wrong parameter", "Machine",
       "electrical", ["vfd", "drive fault", "contactor", "starter", "won't start", "fault code", "inverter"], [
           "Write down the fault code on the VFD / starter before anyone resets it",
           "Isolate the panel and lock out (electrician)",
           "Electrician: inspect contactor contacts, power terminals and control wiring for heat marks; check the VFD "
           "fan, filters and DC bus",
           "Compare VFD parameters (motor data, ramps, current limit) with the commissioning record; correct and restart",
           "Run for a shift and record current and the VFD fault log"],
       W("Why did the starter or drive fail?", [
           B("A terminal was loose or overheated", R(
               "No thermographic scan of MCC and VFD panels", "Machine",
               prevent=["Thermographic scan of MCC / VFD panels every quarter", "Re-torque terminals in PM"])),
           B("The drive overheated — panel hot, fan or filter blocked", R(
               "Panel ventilation and VFD fan filters are not in PM", "Environment",
               prevent=["Clean panel filters monthly; check panel AC / fans on rounds", "Alarm on panel temperature"])),
           B("Parameters changed or lost after a replacement", R(
               "Drive parameters are not backed up or verified after changes", "Measurement",
               prevent=["Keep a parameter backup for every VFD and verify it after a replacement or reset"])),
       ])),
    _c("e_protect", "Protection set wrong — overload relay or VFD current limit too low (nuisance trips)",
       "Measurement", "electrical", ["overload", "nuisance", "tripping", "trips", "relay"], [
           "Read the trip record: which protection operated, and the current at the time",
           "Electrician: compare the overload relay / VFD current limit with the motor nameplate full-load amps",
           "Correct the setting (or replace a drifting relay) with the shift engineer's approval and record it in "
           "the motor register",
           "Restart and watch current and trips for one shift"],
       W("Why was the protection set wrong?", [
           B("Set wrong after a motor or relay was replaced", R(
               "Protection settings not verified after a motor or relay replacement", "Measurement",
               prevent=["Record overload / VFD settings in the motor register; verify after every replacement"])),
           B("The relay has drifted or is faulty", R(
               "Protection relays are not tested periodically", "Method",
               prevent=["Test overload relays with a secondary-injection set during the annual shutdown"])),
           B("The machine now needs more power than its original duty", R(
               "The duty changed without reviewing the motor and protection rating", "Method",
               prevent=["Review the motor rating and protection whenever the duty or feed changes"])),
       ])),
    _c("e_control", "Control or interlock stopping it — PLC permissive, level / pressure switch, E-stop or "
       "local / remote selector", "Measurement", "electrical",
       ["interlock", "plc", "permissive", "won't start", "e-stop", "selector", "remote", "stops by itself"], [
           "Read the PLC / HMI alarm and event list: which interlock or permissive is not healthy",
           "Check E-stops, pull-cords, guard switches and the local / remote selector are reset and in the right "
           "position",
           "Check the switch or transmitter giving the permissive (level, pressure, flow, speed) against a local "
           "reading; clean or recalibrate it",
           "Never bypass an interlock to restart — a bypass must be authorised and logged by the shift engineer"],
       W("Why did the control stop it?", [
           B("A field switch or transmitter gave a false signal", R(
               "Permissive and trip instruments are not function-tested in PM", "Measurement",
               prevent=["Function-test trip and permissive switches in PM",
                        "Cross-check transmitters against local gauges on rounds"])),
           B("A selector or E-stop was left in the wrong position", R(
               "No start-up checklist covering selectors and E-stops", "Man",
               prevent=["Add selector and E-stop reset to the start-up checklist"])),
           B("PLC logic or a timer was changed", R(
               "PLC changes made without approval or a logic backup", "Method",
               prevent=["Approve PLC changes through MOC; keep dated logic backups"])),
       ])),
]

OPERATIONAL = [
    _c("o_duty", "Operated outside its design duty — overloaded, throttled, or run at the wrong speed / setpoint",
       "Method", "operational", ["capacity", "output", "throttled", "speed", "setpoint", "overloaded", "pushed"], [
           "Compare the present flow / load / speed / pressure with the data sheet and the normal operating window",
           "With the shift engineer, bring it back inside the window (reduce feed or load, open the throttled valve, "
           "restore the setpoint)",
           "Share the load with the standby unit if demand is above one unit's rating",
           "Watch current, temperature and vibration for one shift after the change"],
       W("Why was it run outside its design duty?", [
           B("Production needed more than its rating", R(
               "Throughput raised without checking the equipment rating", "Method",
               prevent=["Review equipment ratings before raising throughput (MOC)",
                        "Show the design limits on the HMI next to the live value"])),
           B("Operators didn't know the design limits", R(
               "The operating window is not defined in the SOP or on the HMI", "Man",
               prevent=["Add the operating window (min / max) to the SOP and the HMI",
                        "Train operators on the limits of each machine"])),
           B("A valve or setting was left wrong", R(
               "No line-up check of valves and setpoints at shift handover", "Method",
               prevent=["Add valve line-up and key setpoints to the shift handover checklist"])),
       ])),
    _c("o_sop", "Start-up, shutdown or line-up not done to the SOP (a valve, flushing, warm-up or sequence step missed)",
       "Man", "operational", ["after maintenance", "start-up", "startup", "restart", "line-up", "lineup", "shutdown"], [
           "Stop and make it safe if it is running wrongly",
           "Go through the start-up / line-up SOP step by step with the shift in-charge: valves, flushing, "
           "lubrication, warm-up, sequence",
           "Correct the missed step and restart to the SOP",
           "Record what was missed in the shift log"],
       W("Why was the SOP step missed?", [
           B("Done from memory — no checklist used", R(
               "The SOP is not used as a checklist at the machine", "Method",
               prevent=["Put a laminated start-up checklist at the machine and sign it at every start"])),
           B("The SOP is missing the step or out of date", R(
               "The SOP was not reviewed after equipment or process changes", "Method",
               prevent=["Revise the SOP to include the missed step and re-train the crew"])),
           B("A new or relief operator wasn't trained on it", R(
               "No competency sign-off before operating this machine alone", "Man",
               prevent=["Add this machine to the operator competency matrix with a supervised first start"])),
       ])),
    _c("o_change", "Recent operating change — setpoint, speed, feed recipe, duty / standby switch or a new crew",
       "Method", "operational", ["changed", "change", "recipe", "switched", "new operator"], [
           "Find out what changed and when: shift logbook, HMI change history, feed log, duty / standby record",
           "Go back to the last known-good setting or arrangement, with the shift engineer's OK",
           "If the change is needed, re-introduce it slowly while watching current, temperature and output",
           "Record the change and its effect in the shift log"],
       W("Why did the change cause the problem?", [
           B("It was changed without checking the effect", R(
               "Operating changes are made without a review of their effect (no MOC)", "Method",
               prevent=["Route setpoint and recipe changes through a simple MOC",
                        "Log every setpoint change with name and reason"])),
           B("The next shift wasn't told", R(
               "Changes are not handed over between shifts", "Man",
               prevent=["Add 'changes made this shift' to the handover sheet"])),
           B("The standby unit wasn't in good order when switched in", R(
               "Standby equipment is not run and checked regularly", "Method",
               prevent=["Rotate duty / standby weekly and check the standby before switching"])),
       ])),
    _c("o_cycling", "Too many starts and stops, or repeated trip resets (no duty / standby rotation)", "Method",
       "operational", ["frequent", "restart", "reset", "starts", "stop-start", "cycling", "again and again"], [
           "Count the starts and trips in the last 24 h from the PLC / MCC log",
           "Stop resetting trips until the reason for the trip is found",
           "Smooth the control (wider level band, minimum run / stop timers) so it doesn't start and stop so often",
           "Rotate duty / standby so one unit doesn't take all the starts"],
       W("Why does it start and stop so often?", [
           B("The level / pressure control band is too narrow", R(
               "Control band and timers are set too tight for the process", "Method",
               prevent=["Widen the control band and add minimum run / stop timers (MOC)"])),
           B("Trips are reset without finding the cause", R(
               "No rule on how many resets are allowed before investigating", "Man",
               prevent=["Allow one reset; after a second trip, stop and call the electrician / engineer"])),
           B("Only one unit is used; the standby never runs", R(
               "No duty / standby rotation schedule", "Method",
               prevent=["Rotate duty / standby weekly and log it"])),
       ])),
]

_EOFF = {c: 0.5 for c in E}

CHECKS = {
    "e_fault": Q("e_fault", "What does the panel show — MCC, VFD or PLC — for the last stop or trip?", [
        ("No trip — it's running", {**_EOFF, "o_cycling": 0.6}),
        ("Overload relay tripped", {"e_protect": 3.0, "e_motor": 2.0, "o_duty": 2.5, "o_cycling": 1.5, "e_drive": 1.2}),
        ("VFD fault code (overcurrent, overvoltage, overheat)", {"e_drive": 4.0, "e_supply": 1.8, "e_motor": 1.6,
                                                                 "o_duty": 1.5}),
        ("Earth fault / insulation alarm", {"e_motor": 5.0, "e_drive": 1.3}),
        ("Phase loss / undervoltage alarm", {"e_supply": 5.0, "e_drive": 1.3}),
        ("Stopped by an interlock or permissive", {"e_control": 5.0, "o_sop": 1.3}),
    ], ["trip", "fault", "won't start", "vfd", "overload", "stops"],
      how="Look at the overload relay flag in the MCC, the VFD display and fault history, and the PLC alarm list. "
          "Write the fault down before anyone resets it. Don't open panels — that's for the electrician.",
      purpose="The trip record shows which protection stopped it — electrical, a control interlock, or the machine "
              "overloading the motor."),
    "e_current": Q("e_current", "Ask the control room or read the MCC ammeter: how are the three phase currents "
                                "compared with the motor nameplate?", [
        ("Normal and balanced", {**{c: 0.4 for c in E}, "o_duty": 0.6}),
        ("High on all three phases", {"o_duty": 3.0, "e_motor": 1.5, "e_supply": 1.3}),
        ("Unbalanced — phases differ by more than 5 %", {"e_supply": 4.5, "e_motor": 2.5, "e_drive": 2.0}),
        ("Not running — it won't start", {"e_drive": 3.0, "e_control": 3.0, "e_supply": 2.0, "e_protect": 1.5}),
    ], ["current", "amps", "trip", "motor"],
      how="Read the ammeter on the MCC door or the SCADA current for each phase and compare with the full-load amps "
          "on the motor nameplate. Ask the electrician to clamp each phase if there is only one ammeter.",
      purpose="Balanced current near nameplate rules out most electrical faults; unbalance points to the supply or "
              "the motor."),
    "e_motortemp": Q("e_motortemp", "Use the IR gun on the motor body and smell the air off the fan cowl. How is it?", [
        ("Warm, below 80 °C, no smell", {"e_motor": 0.4, "e_supply": 0.7, "o_duty": 0.7, "o_cycling": 0.7}),
        ("Hot, above 90 °C on the body", {"e_motor": 2.5, "o_duty": 2.5, "e_supply": 2.0, "o_cycling": 2.0,
                                          "e_drive": 1.2}),
        ("Burning or varnish smell, or smoke", {"e_motor": 5.0, "e_drive": 1.5}, ["rotating_critical"]),
    ], ["motor", "hot", "smell", "burning", "overheat"],
      how="Stay outside the guard. Aim at the motor body (not the fan cowl) from about 30 cm. A sudden rise or a "
          "burning smell is the warning sign. If you smell burning or see smoke, stop the motor with the local stop "
          "and call the electrician.",
      purpose="A hot or smelling motor points to the winding, the supply or overloading — not the driven machine."),
    "e_megger": Q("e_megger", "Electrician check, with the motor isolated and locked out: insulation resistance and "
                              "the terminal box?", [
        ("IR above 100 MΩ, terminals clean and tight", {"e_motor": 0.2, "e_drive": 0.6, "e_supply": 0.8}),
        ("IR low (below 1 MΩ) or water in the terminal box", {"e_motor": 6.0}),
        ("Loose, burnt or discoloured terminal", {"e_drive": 3.5, "e_supply": 3.0, "e_motor": 1.5}),
    ], ["insulation", "earth fault", "megger", "terminal", "motor"],
      how="Electrician only. Isolate at the MCC, lock out and prove dead. Megger phase-to-earth at 500 V (LV motors) "
          "for one minute, then open the terminal box and look for water, tracking or heat marks.",
      purpose="Low insulation or a burnt terminal confirms an electrical fault before any mechanical strip-down."),
    "e_setting": Q("e_setting", "Electrician check: how is the overload relay or VFD current limit set, compared "
                                "with the motor nameplate full-load amps?", [
        ("Matches the nameplate", {"e_protect": 0.15}),
        ("Set below the nameplate", {"e_protect": 6.0, "o_cycling": 1.2}),
        ("Not recorded — can't tell what it should be", {"e_protect": 2.0}),
    ], ["overload", "nuisance", "trips", "relay", "setting"],
      how="Electrician, at the MCC or VFD keypad: read the overload dial or the VFD motor current limit and compare "
          "with the full-load amps on the motor nameplate and the setting recorded in the motor register.",
      purpose="An overload set below the motor's rating trips a healthy machine; set right, the trips are real."),
    "o_change": Q("o_change", "Has anything about how it's run changed recently — setpoint, speed, feed recipe, "
                              "duty / standby switch or a new crew?", [
        ("No change", {"o_change": 0.2}),
        ("Setpoint, speed or feed changed", {"o_change": 6.0, "o_duty": 2.0}),
        ("Switched to the other unit, or restarted after a stop", {"o_change": 4.0, "o_sop": 3.0}),
        ("New or relief operator this week", {"o_sop": 4.0, "o_change": 2.5}),
    ], ["changed", "change", "recipe", "setpoint", "switched"],
      how="Check the shift logbook, the HMI change history and the feed log, and ask the previous shift.",
      purpose="Most problems that start suddenly follow a change in how the equipment is run."),
    "o_duty": Q("o_duty", "Is it running inside its design window right now — flow, load, speed or pressure against "
                          "the data sheet or the HMI limits?", [
        ("Within the design window", {"o_duty": 0.2}),
        ("Above design — pushed for more output", {"o_duty": 6.0, "e_motor": 1.3}),
        ("Well below design — throttled, starved or idling", {"o_duty": 5.0}),
    ], ["capacity", "output", "load", "throttled", "speed", "setpoint"],
      how="Compare the live flow, current, speed or pressure on the HMI with the design values on the data sheet or "
          "the HMI limits. Ask the shift engineer if you are not sure of the window.",
      purpose="Equipment run beyond (or far below) its design duty overheats, overloads and wears fast."),
    "o_sop": Q("o_sop", "Was the last start-up, line-up or shutdown done with the SOP checklist?", [
        ("Yes, done to the checklist", {"o_sop": 0.2}),
        ("Done from memory — no checklist", {"o_sop": 3.5}),
        ("A step was missed (valve, flushing, warm-up or sequence)", {"o_sop": 8.0}),
    ], ["start-up", "startup", "restart", "line-up", "after maintenance", "shutdown"],
      how="Ask the operator who did the last start-up and look at the signed checklist or the shift log.",
      purpose="A missed valve, flush or warm-up step at start-up is a common cause of early failures."),
    "o_starts": Q("o_starts", "How many times has it started or tripped in the last 24 hours, compared with normal?", [
        ("The usual few", {"o_cycling": 0.15, "e_protect": 0.7}),
        ("A few more than usual", {"o_cycling": 1.5, "e_protect": 1.5, "e_control": 1.3}),
        ("Many — repeated restarts or trip resets", {"o_cycling": 7.0, "e_protect": 1.8, "e_motor": 1.4,
                                                     "e_control": 1.4}),
    ], ["frequent", "restart", "reset", "starts", "cycling"],
      how="Count the starts and trips on the PLC event log or the MCC counter, or ask the control room.",
      purpose="Frequent starts and trip resets overheat the motor and point to a control or protection problem."),
}

# What each kind gets. Static gas-train units get the operational causes that apply to process equipment.
CAUSES_FOR = {k: E + O for k in MOTOR_KINDS} | {k: ["o_duty", "o_sop", "o_change"] for k in STATIC_KINDS}
SKIP = {  # (kind, id) already covered by the tree's own cause or check
    ("Shredder", "e_protect"), ("Shredder", "o_duty"), ("WAM", "o_duty"), ("Blower", "o_duty"), ("Filter", "o_duty"),
    ("Decanter", "o_change"), ("Filter", "o_change"), ("WAM", "o_change"),
}
CHECKS_FOR = {"e_fault": E, "e_current": E, "e_motortemp": ["e_motor"], "e_megger": ["e_motor"],
              "e_setting": ["e_protect"],
              "o_change": ["o_change"], "o_duty": ["o_duty"], "o_sop": ["o_sop"], "o_starts": ["o_cycling"]}
HAS_CURRENT = {"Pump", "Agitator", "Blower", "Shredder", "WAM", "Machine"}  # their own motor-current check

# The trees' own causes that are electrical / operational / instrument; the rest are mechanical or process
DOMAIN = {("Shredder", "trip"): "electrical", ("Shredder", "overfeed"): "operational",
          ("WAM", "overload"): "operational", ("WAM", "press"): "operational", ("Blower", "backpr"): "operational",
          ("Decanter", "solids"): "operational", ("Decanter", "diff"): "operational", ("Decanter", "feed"): "operational", ("Chiller", "icing"): "operational",
          ("Membrane", "press"): "operational", ("Scrubber", "air"): "operational", ("Filter", "bypass"): "operational"}

# Evidence for the shared causes from answers the trees already have (first matching rule per option wins)
CROSS = [
    (r"unequal|unbalanced|phases? differ", {"e_supply": 4.0, "e_drive": 2.5, "e_motor": 2.0}),
    (r"trips with normal current", {"e_protect": 3.5, "e_control": 2.5, "e_drive": 2.0}),
    (r"trips or won't start|won't start", {"e_drive": 3.0, "e_control": 3.0, "e_supply": 2.0, "e_protect": 2.0,
                                           "e_motor": 2.0}),
    (r"stops at random|no fault shown", {"e_control": 3.0, "e_drive": 2.0, "e_supply": 2.0}),
    (r"trips? (on|or) overload|trips or phases|high current or trips",
     {"e_protect": 2.5, "e_motor": 1.8, "e_drive": 1.8, "o_duty": 1.8, "o_cycling": 1.5}),
    (r"electrical (hum|buzz)|motor buzz", {"e_motor": 3.0, "e_supply": 3.0, "e_drive": 2.0}),
    (r"higher than (nameplate|usual)|high, creeping|stays high|swings high",
     {"o_duty": 2.5, "e_motor": 1.3, "e_supply": 1.3}),
    (r"^normal and steady|^normal current|^steady near rated|^starts and runs normally",
     {**{c: 0.35 for c in E}, "o_duty": 0.6}),
    (r"yes, changed|changed in the last|changed recently|turned up", {"o_change": 3.5, "o_duty": 1.5}),
    (r"flow surging|much thicker|above design|above (the )?rating|overflowing", {"o_duty": 2.5}),
    (r"refitted|oil changed", {"o_sop": 2.0, "o_change": 1.5}),
    (r"^no work|^no change|same settings|^no, same", {"o_change": 0.3}),
]

# The trees' old catch-all electrical cause, now split into the shared electrical causes
REPLACED = {"Pump": "elec", "Agitator": "elec", "Machine": "elec"}


def extend(trees: dict[str, dict]) -> None:
    """Add the shared electrical and operational causes and checks to every tree, in place."""
    for kind, tree in trees.items():
        if "category" not in tree["causes"][0]:
            continue
        motor = kind in MOTOR_KINDS
        for c in tree["causes"]:
            c.setdefault("domain", DOMAIN.get((kind, c["id"])) or
                         ("instrument" if c.get("category") == "Measurement" else "mechanical" if motor else "process"))
        want = [cid for cid in CAUSES_FOR.get(kind, []) if (kind, cid) not in SKIP]
        if not want:
            continue
        old = REPLACED.get(kind)
        if old:
            tree["causes"] = [c for c in tree["causes"] if c["id"] != old]
            tree.setdefault("aliases", {})[old] = "e_drive"
        lib = {c["id"]: c for c in ELECTRICAL + OPERATIONAL}
        tree["causes"] += [dict(lib[cid]) for cid in want]
        # evidence from the tree's own checks
        for q in tree["questions"]:
            for o in q["options"]:
                was = o["lik"].pop(old, None) if old else None
                if was is not None and abs(was - 1.0) > 0.15:
                    for cid in E:
                        if cid in want:
                            o["lik"].setdefault(cid, was)
                for pat, lik in CROSS:
                    if re.search(pat, o["label"], re.I):
                        for cid, v in lik.items():
                            if cid in want:
                                o["lik"][cid] = v
                        break
                else:  # a mechanical / process reading: healthy is more likely under an electrical or operating fault
                    ok = is_normal_answer(o["label"])
                    for cid in want:
                        o["lik"].setdefault(cid, (1.4 if ok else 0.6) if cid in E else (1.4 if ok else 0.5))
        # the shared checks, unless the tree already asks the same thing
        have = {q["id"] for q in tree["questions"]}
        for qid, tests in CHECKS_FOR.items():
            if qid in have or not any(cid in want for cid in tests):
                continue
            if qid == "e_current" and kind in HAS_CURRENT:
                continue
            if qid == "o_change" and (kind, "o_change") in SKIP:
                continue
            q = CHECKS[qid]
            tree["questions"].append({**q, "options": [{**o, "lik": {c: v for c, v in o["lik"].items() if c in want}}
                                                       for o in q["options"]]})
