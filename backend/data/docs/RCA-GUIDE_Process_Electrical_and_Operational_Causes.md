# RCA Guide — Process, Electrical and Operational Causes of Abnormal Conditions

An abnormal condition on a machine is not always a mechanical failure. Before opening anything up, sort the possible causes into five families and check the cheap, safe ones first:

| Family | What is wrong | Typical evidence |
|---|---|---|
| **Process** | What the equipment handles, or the process around it: feed solids / viscosity / grit / fibre, foam or gas in the liquid, tank level, gas holder level and suction pressure, gas quality (CH4, O2, H2S, moisture), temperature, upstream starving it or downstream restricting it | Follows the feed, the level, the gas or the weather; other equipment on the same stream is affected too; the machine is healthy when the process is normal |
| **Electrical** | Supply (low / unbalanced voltage, lost phase), motor winding or insulation, starter / VFD, protection settings, controls and interlocks | Trips, won't start, buzzing motor, hot or smelling motor, unequal phase currents, a fault code or alarm |
| **Operational** | Run outside its design duty, start-up / line-up not to the SOP, a recent change (setpoint, recipe, duty / standby, new crew), too many starts or trip resets | Began right after a change or a start-up; valves or setpoints not as per the line-up sheet |
| **Instrument** | A transmitter, switch or analyser reading wrong | Local gauge or a portable instrument disagrees with SCADA; the machine looks and sounds normal |
| **Mechanical** | The machine itself: bearings, seals, couplings, alignment, wear parts, lubrication | Noise, heat, vibration, leaks or wear you can see, hear or measure on the machine |

Two questions sort most problems before the first check:
1. **What state is it in now?** Running badly → mechanical or process first. Tripped → electrical, protection or overload from the process. Won't start → electrical / control interlock first, almost never mechanical wear. Stops and starts → control band, protection or a starved process.
2. **How did it start?** Suddenly → electrical, a process upset or an operating change. Slowly over days or weeks → wear, fouling, a drifting instrument. Right after maintenance or a change → the SOP step missed, the setting changed, the part fitted wrong.

## 1. Process causes by equipment

### Pumps
| Process cause | Signs | Check | First action |
|---|---|---|---|
| Gas or air in the suction (foam, gassy digestate, vortex at low level) — gas lock | Discharge pressure low and fluctuating, crackling noise, loses prime | Sample at the suction drain: foam / bubbles? Tank level vs minimum submergence | Stop before it runs dry; vent the suction high point (gas test first); restore level |
| Slurry too thick, sandy or fibrous (high TS / viscosity, sand settled in the line) | High current, low flow, recovers after a back-flush | Sample: thick / sandy? Feed TS today vs normal | Flush lines; clear the stone trap; dilute to design TS |
| Starved suction (tank low, suction valve part-shut, strainer blocked) — cavitation | Gravel noise, pressure swings | Tank level, suction valve, strainer dP | Restore level / open valve / clean strainer |
| Downstream restricted (valve shut, line blocked, receiving tank full) | High discharge pressure, low flow; on a PD pump: relief lifting or trips on high pressure | Walk the discharge line-up | Open / clear — never dead-head a PD pump |

### Agitators
| Process cause | Signs | Check | First action |
|---|---|---|---|
| Level too low — propeller near the surface | Vibration, current swinging every turn, splashing, vortex | Level vs the agitator's minimum submergence | Stop the agitator; restore level |
| Foaming (overloading, fat / protein-rich feed, rising FOS/TAC) | Foam in the sight glass or gas line, falling gas, unsteady current | Lab: FOS/TAC (watch at 0.3, cut feed above 0.4), pH, gas production | Cut feed; antifoam per SOP; clear traps |
| Thick contents, crust or settled sand | High, creeping current; crust on the surface | Surface through the sight glass; TS | Break crust per SOP; review feed recipe |
| Long fibre wrapping the propeller | Rhythmic knock, current swing each turn | Feed log: straw / napier length | Shorten fibre at the shredder; clean the propeller |

### Blowers and compressors
| Process cause | Signs | Check | First action |
|---|---|---|---|
| Not enough gas — holder low, production down | Blower surging / pulsing; compressor unloading, cycling, low-suction trips | Holder level, suction pressure, today's gas production | Match offtake to production; unload / stop a unit |
| Condensate in the gas | Pulsing, imbalance, water at the drains, liquid knock in a compressor | Knock-out pots, low-point drains | Drain; check trap operation |
| Particles from the scrubber / filter | Valve damage, scored cylinders, black powder at the suction strainer | Suction strainer, filter dP history | Stop; protect the compressor; fix the filtration |
| Hot inlet gas (summer, cooler fouled upstream) | High discharge temperature on all stages | Inlet gas temperature, upstream cooler | Clean coolers; reduce load in the afternoon peak |

### HWG, chiller, gas cleaning, membranes
| Equipment | Process cause | Check |
|---|---|---|
| HWG | Low CH4 (below ~48 %), high O2, water in the gas, low gas pressure when the holder is low | Gas analyser CH4 / O2; gas train pressure; condensate traps |
| Chiller | Gas hotter, wetter or at higher flow than the rating; for water-cooled units: cooling water short | Inlet gas temperature and flow; CW pump / tower fan |
| H2S scrubber | Raw-gas H2S above bed design after a feed or digester change; air dosing wrong | Inlet H2S trend; dosing rotameter, outlet O2 |
| Filter skid | Wet gas loading the elements | Housing drain; upstream knock-out pots |
| Membranes | Air (N2 / O2) in the raw gas — membranes don't remove N2; moisture or oil reaching the fibres; feed pressure low | Raw-gas O2 / N2; dew point; guard bed and coalescer drains; feed pressure |

### Separation and feeding
| Equipment | Process cause | Check |
|---|---|---|
| Decanter | Feed solids or flow varying; polymer weak, old or wrongly dosed; sand and grit | Feed TS and flow trend; polymer make-up and pump; grit in the cake |
| Screw press | Feed too thin or too thick; long fibre, plastic or sand; wash water low | Feed look and TS; debris in the cake; wash pressure |
| Shredder | Wet, sticky or over-long feed; stones or metal | Hopper sample; magnet and stone trap |
| Bagging / briquetting | Solids too wet or too dry from separation | Squeeze test / moisture of the cake |

## 2. Electrical checks (safe for operators unless marked)

1. **Read the trip before anyone resets it:** overload flag in the MCC, VFD fault code and history, PLC alarm list. Overload → the machine or process loaded it, or the setting is wrong; VFD over-current / over-voltage / over-temperature → the drive or supply; earth fault → the motor or cable; phase loss / undervoltage → the supply; interlock → a control permissive.
2. **Phase currents** on the MCC ammeter or SCADA: balanced and near nameplate rules out most electrical faults; unbalance above 5 % points to the supply or the motor; high on all three phases points to overload (often process: thick slurry, low level, high back-pressure).
3. **Motor temperature and smell** (IR gun on the body, from outside the guard): above 90 °C or a varnish smell → winding, supply or overload. Stop it if it smells burnt.
4. **Electrician only:** insulation resistance (megger, 500 V for LV motors — above 100 MΩ is healthy, below 1 MΩ is a fault), terminal box (water, tracking, heat marks), overload / VFD current limit vs nameplate full-load amps, contactor contacts.
5. **One reset only.** After a second trip, stop and find the cause — repeated resets overheat the winding.

## 3. Operational checks

- Is it inside its **design window** (flow, load, speed, pressure) on the data sheet / HMI limits?
- Was the last **start-up / line-up / shutdown** done with the SOP checklist (valves, flushing, warm-up, sequence)?
- What **changed** recently — setpoint, speed, feed recipe, duty / standby switch, new or relief operator? Check the shift log and HMI change history.
- How many **starts or trips** in the last 24 h compared with normal?

## 4. Worked examples

**Pump losing flow, digestate foaming.** Discharge pressure low and fluctuating; suction sample full of bubbles; bearings, seal and current normal. Direct cause: gas lock from foaming digestate (process, Material). Why? The digester was foaming. Why? Feed was raised 30 % in a week. Root cause: loading raised faster than the digester can adapt (Method). Prevent: raise loading by no more than 10–15 % a week; act-on limits for FOS/TAC.

**Agitator vibrating after the level was lowered.** Vibration and current swinging every turn; gearbox temperature, oil and coupling normal; level 0.5 m above the propeller. Direct cause: level below the agitator's minimum submergence (process, Method). Root cause: tank-emptying SOP didn't say to stop the agitators (Man). Prevent: add the step to the SOP; interlock agitators on the minimum level.

**Membrane product purity at 93 %.** Feed pressure, dew point and temperature normal; analyser checked; raw-gas O2 1.4 %. Direct cause: air in the raw gas (process, Material). Why? Scrubber air dosing was turned up to fight high H2S. Root cause: air dosing not controlled on O2 (Method). Prevent: O2-controlled dosing with a 1 % alarm.

**Compressor tripping on low suction at night.** Valves, oil, cooling normal; gas holder at 15 %. Direct cause: not enough gas at the suction (process, Environment). Root cause: compressor loading not linked to the gas available (Method). Prevent: auto-unload on suction pressure / holder level.

**PC pump losing flow after the feed tank emptied.** Stator housing hot, rubber bits in the outlet strainer. Direct cause: stator burnt by dry running (Machine). Root cause: dry-run protection bypassed (Measurement). Prevent: test the dry-run sensor monthly; interlock the pump on the tank low level.
