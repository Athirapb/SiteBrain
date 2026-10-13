# RCA Guide — Gas Movers (Blowers, Compressors) and Hot Water Generators

How to run a root cause analysis on blowers, LP / HP compressors, plant air compressors and HWG 1/2: a 6M fishbone to list the possible direct causes, field checks to narrow them down, then 5-Why to reach the systemic root cause. A root cause is something you can fix with a procedure, training, a spec or a design change — "the part broke" is never a root cause.

## 1. Fishbone (6M) — Blowers
| Bone | Typical direct causes |
|---|---|
| Man | Over-greasing; belts replaced singly; wrong gasket fitted |
| Machine | Flange gasket / shaft seal leak; bearing wear; line not sloped to a drain |
| Method | Running against a closed valve / stuck NRV; no re-tension after belt change; condensate traps not cleaned |
| Material | Condensate and sulphur deposits in the casing; H2S corrosion of impeller |
| Measurement | Faulty pressure switch / wet impulse line → false trips |
| Environment | Hot enclosure, blocked louvres, summer ambient |

## 2. Fishbone (6M) — Compressors (LP 1–4, HP 1–3, plant air)
| Bone | Typical direct causes |
|---|---|
| Man | Oil level not logged; valve fitted the wrong way round; gasket reused |
| Machine | Crankcase oil leak → bearing starvation; valve plate / spring failure; ring and packing wear; discharge gasket leak |
| Method | Start-up without draining pots / cylinders; valves overhauled only on failure; no re-torque after flange work |
| Material | Scrubber media / iron-sulphide particles; liquid carryover; siloxane silica; H2S |
| Measurement | Transmitter drift; low-oil trip not proof-tested |
| Environment | Fouled air coolers in dusty season; cold nights condensing gas in the suction line; high ambient |

## 3. Fishbone (6M) — HWG
| Bone | Typical direct causes |
|---|---|
| Man | Repeated lockout resets; burner tuned by untrained staff; louvres closed |
| Machine | ID fan bearing wear; circulation pump weak; damper linkage slipped |
| Method | ID fan belt slip (no re-tension / alignment); no combustion test after service; no loop venting |
| Material | Low / wet gas supply; silica and sulphur deposits; hard make-up water scaling |
| Measurement | Flame scanner / ionisation probe fault; regulator drift |
| Environment | Combustion air starved, wind / rain at the stack, hot boiler house |

## 4. Field checks that split the fishbone fast
- **Compressor:** where is the noise (crankcase knock vs valve-cover clatter vs hiss vs thud at start)? Oil level and leaks; suction strainer contents; gas detector at flanges vs packing vent; valve-cover IR; stage temperatures; cooler; breather blow-by; local gauge vs SCADA.
- **Blower:** gas detector; sound; bearing IR; casing drain and upstream trap; belts (LOTO); valve line-up; enclosure; gauge vs SCADA; motor current.
- **HWG:** lockout code (write it down before reset); gas pressure while firing; flame signal trend; probe condition; flue O2 / CO and temperature trend; belts / fan bearing; flow-return ΔT; louvres.

Always compare what you see with SCADA. If you say "normal" but SCADA shows vibration > 4.5 mm/s or oil < 60%, SiteBrain escalates — the instrument or the observation is wrong, and both matter.

## 5. Worked 5-Why examples

**A. LP 4 knocking with oil at 50% (KB-0389)**
1. Why the knock? Big-end bearing running short of oil.
2. Why short of oil? Crankcase level fell to 50%.
3. Why did it fall? Oil weeping from the drain-plug gasket.
4. Why was it leaking? The old washer was reused at the last oil change.
5. Why reused? The oil-change job card does not call for a new washer, and oil level is not logged on rounds.
**Root cause (Method):** oil-change procedure and shift checksheet gaps. **Prevent:** new washer on job card; log level every shift; SCADA alarm at 65%.

**B. Gas smell at Gas Blower 1 (KB-0501)**
1. Why the smell? Biogas leaking at the discharge flange (25% LEL).
2. Why? Gasket hardened and cracked; bolts under torque.
3. Why hardened? A non-specified rubber gasket was fitted.
4. Why? Stores have no line-class gasket list.
**Root cause (Material):** no gasket specification. **Prevent:** line-class gasket list; 24 h re-torque on flange jobs.

**C. HWG 2 flame-failure lockouts (KB-0510)**
1. Why lockouts? Flame signal below minimum.
2. Why low? Ionisation probe coated in white powder.
3. Why powder? Silica from siloxanes in biogas.
4. Why did it build up? Probe cleaned only at the yearly service.
**Root cause (Method / Material):** cleaning interval set for natural gas, siloxanes not monitored. **Prevent:** quarterly burner and probe cleaning, monthly flame-signal log, siloxane sampling.

**D. HWG ID fan belt squeal (KB-0270)**
1. Why squeal? Belts slipping at start-up.
2. Why? Tension low, pulleys 3 mm out of line.
3. Why? After a motor change, aligned by eye and never re-tensioned.
4. Why? Job card has no alignment tool or re-tension step.
**Root cause (Method).** **Prevent:** alignment laser; re-tension at 4 h and 24 h.

## 6. Writing up the RCA
Record in the incident log: symptom, direct cause, why chain (steps separated by " > "), 6M category of the root cause, resolution and preventive action — and give each preventive action an owner and a due date.
