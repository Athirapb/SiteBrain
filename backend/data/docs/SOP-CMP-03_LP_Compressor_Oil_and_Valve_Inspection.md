# SOP-CMP-03 — LP / HP Gas Compressor Oil and Valve Inspection

Applies to: BUU LP 1–4 (raw biogas, reciprocating) and HP 1–3 (CBG to ~250 bar cascade).
Related: SOP-ROT-01 (LOTO), SOP-SCR-02 (scrubber media), OEM_HP_CBG_Compressor_Maintenance, interlocks OIL-01, CMP-01, GAS-01.

## 1. Normal operating window (check every shift)
| Parameter | LP 1–4 | HP 1–3 |
|---|---|---|
| Suction pressure | ≈ 1.0–1.3 bar(g) | ≈ 6 bar(g) |
| Final discharge pressure | ≈ 5.8–6.5 bar(g) | up to 250 bar(g) |
| Stage discharge temperature | < 150 °C | < 150 °C per stage |
| Crankcase oil level | 60–80% sight glass | 60–80% sight glass |
| Oil pressure | ≈ 2–4 bar, up within 10 s | ≈ 2–4 bar |
| Valve-cover temperature spread | < 15 °C between like valves | < 15 °C |
| Frame vibration | < 4.5 mm/s | < 4.5 mm/s |

## 2. Oil level
- Crankcase oil 60–80% of sight glass. Interlock OIL-01 blocks restart below 60%.
- Read the level with the machine stopped a few minutes (or as the OEM data plate says). Log it on the shift checksheet; SCADA alarm at 65%.
- Low level with knocking: suspect crankcase leak and big-end bearing starvation (case KB-0389). Inspect bearings before restart.
- Low level without a visible leak: check crankcase breather for blow-by / oil mist (ring or packing wear) and oil carried into the gas.
- Rising level or milky oil: water / condensate is getting in — drain knock-out pots, change oil, check valves for impact damage.
- Always use the specified grade (sour-gas compressor oil). New drain-plug washer and cover gasket at every oil change.

## 3. Leak tracing (crankcase)
1. Stop, LOTO (SOP-ROT-01). Wipe the crankcase clean.
2. Check drain plug, crankcase doors, crankshaft oil seal, oil cooler and filter fittings.
3. Dust suspect areas with talc and turn by hand / run the pre-lube pump — the leak path shows up.
4. Fix, top up, restart unloaded, confirm oil pressure within 10 s and no knock.

## 4. Suction vessel strainer & valve assemblies
- Normal baseline: clean gas passage; uniform valve cover temperature; strainer dP < 0.1 bar.
- Fault indicators: particle build-up in suction vessel, black iron-sulphide powder, one suction valve hotter by >15 °C.
- If solid particle risk is flagged upstream (scrubber media carryover, filter element rupture), interlock CMP-01 trips the compressor load line. Release only after the upstream fix is verified.
- Iron-sulphide powder can self-heat in air — keep it wet and bag it.

## 5. Valve plate inspection
1. Permit to work. Stop, isolate suction and discharge, vent to flare, purge with nitrogen, gas-test (0% LEL) before opening.
2. Mark each valve and its pocket (suction / discharge) before removal.
3. Remove valve covers, inspect plates, springs, seats and guards.
4. Read the damage: clean fatigue crack = age; impact marks / bent plates = liquid or debris; uneven seat wear = wrong lift or springs.
5. Replace broken plates and springs as a set with OEM parts; lap seats if scored; always new cover gaskets.
6. Second person checks the orientation (a suction valve in a discharge pocket destroys the cylinder).
7. Torque cover bolts per OEM chart; leak test with soap solution at operating pressure.
8. Restart, compare interstage pressures and valve-cover temperatures with baseline. Re-torque covers after 24 h.

## 6. Liquids
- Drain suction knock-out pot and interstage separators every shift (more often in cold weather).
- Test auto-drains monthly. Before a start after a long stop: drain cylinders and pot, bar over by hand.
- A heavy thud / bang just after start is liquid in the cylinder — stop immediately.

## 7. Cooling
- Check cooling-water flow and return temperature, or air-cooler fan and fins. All stages hot = cooling problem; one stage hot = valve or rings in that stage.

## 8. Gas leak response
- Any gas smell: isolate, ventilate, confirm with a portable gas detector (alarm at 10% LEL / 10 ppm H2S). No hot work. GAS-01 interlock.
- Readings at the rod packing vent / distance piece mean packing wear — plan packing replacement.
