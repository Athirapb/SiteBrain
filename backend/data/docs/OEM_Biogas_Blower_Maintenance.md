# OEM Guidance — Biogas and Air Blower Maintenance

Covers: BUU Gas Blower 1/2 (raw biogas booster after the H2S scrubber / filter, feeding the LP compressors), digester D1–D4 Blower 1/2 (air dosing for biological desulphurisation, membrane-roof support air), Flare Blower and LDT Top Blower 1/2 in the HWG area. Compiled from ATEX side-channel blower OEM manuals, centrifugal / roots blower manuals and plant experience.

## Blower types on site
- **Side-channel (regenerative)** — direct drive, sealed-for-life bearings on most models, up to ≈ 400 mbar differential. Very sensitive to condensate in the casing.
- **Centrifugal** — gas boosters; flow falls quickly with back-pressure.
- **Roots / rotary lobe** — belt-driven, oil-lubricated gears and bearings; relief valve on discharge is essential.

Gas blowers must be ATEX-rated (zone 1/2 inside, zone 2 around) with gas-tight shaft seals; air blowers dosing digesters must never be able to push air above the O2 limit.

## Typical operating data
| Item | Typical value |
|---|---|
| Gas blower suction | ≈ 5–20 mbar(g), never negative |
| Differential pressure | ≈ 80–250 mbar (OEM curve, nameplate max) |
| Gas discharge temperature | < 60–70 °C (OEM max) |
| Bearing housing temperature | < 80 °C |
| Vibration | < 4.5 mm/s |
| Desulphurisation air dosing | O2 in biogas ≈ 0.3–1% (never above the plant limit) |

## Preventive maintenance
| Interval | Task |
|---|---|
| Shift | Listen for noise; check dP, motor current, enclosure ventilation; drain casing and upstream condensate traps |
| Weekly | Gas-detector sweep of flanges, shaft seal and drains; check belts (roots units, stopped under LOTO) |
| Monthly | Vibration and bearing temperature; clean inlet filter (air blowers); clean condensate traps; grease per OEM |
| Quarterly | Open inspection cover — sulphur deposits and corrosion on impeller; check NRV and relief valve; check gearbox oil (roots) |
| 6-monthly | Calibrate pressure switches / transmitters; drain impulse lines |
| OEM hours (≈ 20,000 h side-channel) | Replace sealed bearings and shaft seals; balance impeller |

## Common failures
1. **Gas leak at flange or shaft seal** — wrong gasket grade, lost bolt load from vibration, pipe strain. Use the line-class gasket, re-torque after 24 h, support pipework. Any detector reading → GAS-01.
2. **Condensate in the casing** — saturated biogas cools and condenses; line not sloped to a drain; trap blocked. Water unbalances and corrodes the impeller; can lock a side-channel rotor.
3. **Sulphur deposits** — elemental sulphur from biological desulphurisation forms a yellow crust in the side channel. Control air dosing; clean quarterly.
4. **Bearing failure** — end of life on sealed bearings, over-greasing, wet gas past the shaft seal.
5. **Overheating** — blower running against a closed valve / stuck NRV / choked filter, or a hot enclosure. Side-channel blowers heat the gas strongly at high dP.
6. **Belt slip (roots)** — low tension, misalignment, mixed belts. Matched sets, laser alignment, re-tension at 4 h and 24 h.
7. **False trips** — wet impulse lines on pressure switches, out-of-calibration transmitters.

## Safe work
- LOTO per SOP-ROT-01; for gas blowers also isolate suction and discharge, vent to flare and purge with nitrogen, gas-test before opening.
- Drained condensate can release H2S — wear a personal monitor, drain to the closed drain.
- Never adjust a running belt. Never bypass the relief valve.

## Restart checklist
- Valve line-up per start-up sheet (suction, discharge, NRV free, bypass as required).
- Casing drained, condensate traps empty.
- Guards fitted, LOTO removed by the person who applied it.
- After start: dP and current within the OEM curve, vibration < 4.5 mm/s, no gas at joints.
