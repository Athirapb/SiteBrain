# SOP-HWG-01 — Hot Water Generator Operation and Burner Troubleshooting

Applies to: HWG 1 and HWG 2 (biogas-fired hot water generators heating digesters D1–D4).
Related: SOP-ROT-01 (LOTO), interlocks GAS-01, advisory BELT-01.

## 1. Normal operating window
| Parameter | Normal |
|---|---|
| Flow / return temperature | ≈ 70–80 °C / 60–70 °C (ΔT 8–12 °C) |
| Digester temperature | 37–40 °C, change < 1 °C per day |
| Gas pressure at burner train inlet | ≈ 20–50 mbar (burner data plate) |
| Flue gas O2 / CO | 3–6% / < 100 ppm |
| Flue gas temperature | ≈ 160–220 °C (a steady rise = fouling) |
| Flame signal | stable, above burner manual minimum |
| ID fan vibration / bearing temperature | < 4.5 mm/s / < 80 °C |
| Loop pressure | ≈ 1.5–3 bar, circulation pump running |

## 2. Start-up
1. Check loop: valves open, pressure OK, circulation pump running, air vented.
2. Drain the gas-line condensate trap; check gas holder level and inlet gas pressure.
3. Check boiler-house louvres open and the stack clear.
4. Start the ID fan; confirm the air pressure switch makes.
5. Let the burner run its pre-purge — never shorten it.
6. After light-off check flame through the sight glass and the flame signal; check flue O2 / CO after 10 minutes.

## 3. Shutdown and isolation for work
1. Switch over to the standby HWG first so digester temperature stays steady.
2. Stop the burner; let the fan post-purge.
3. Close and lock the manual gas valve; isolate burner and fan power (LOTO, SOP-ROT-01).
4. Check for gas with a detector before opening the burner. Allow to cool.

## 4. Lockout troubleshooting
**Rule: never reset more than twice. After the second lockout, find the cause.** Write the lockout code down before reset.

| Lockout / symptom | Check first | Likely cause |
|---|---|---|
| Flame failure, signal falling over weeks | Probe / electrode for white powder | Silica (siloxanes) or sulphur deposits — clean probe, electrode, burner head |
| Flame failure, sudden drop-outs | Scanner lens, probe position, cable and earth | Scanner / probe fault |
| Low gas pressure | Inlet gauge while firing; condensate trap; filter dP; holder level | Low or unstable gas supply |
| Air pressure switch | ID fan belts, fan running, louvres, flue | Belt slip, fan bearing, blocked air / flue |
| High water temperature limit | Circulation pump, loop strainer, air in loop, ΔT | Low circulation or scale |
| Rumble / pulsing flame | Flue O2 / CO, damper linkage | Air–fuel ratio out of tune or short of air |

## 5. ID fan belts (BELT-01)
- Stop the ID fan and apply LOTO. Never adjust a running belt.
- Squeal at start-up and shiny glazed belts = low tension; frayed edges / one-side wear = misalignment.
- Replace as a matched set, align with a laser / straight edge, tension to OEM deflection (≈ 15 mm per metre of span), re-check at 4 h and 24 h (case KB-0270).

## 6. Cleaning intervals for biogas service
- Probe / scanner: monthly, log the flame signal.
- Burner head, electrode, fire-side surfaces: quarterly (biogas silica), yearly is not enough.
- Flue and stack: 6-monthly. Water-side descale: yearly, or when ΔT drops with rising flue temperature.

## 7. Combustion tuning
- Only trained technicians adjust the burner. Use a flue gas analyser; target O2 3–6%, CO < 100 ppm.
- Re-tune when the gas CH4 content changes by more than ~5%, and after any burner work.
- Mark and lock the damper linkage; record settings on the burner card.

## 8. Gas safety
- Any gas smell in the boiler house: stop the burner, close the manual gas valve, ventilate, confirm with a portable detector (GAS-01). No switches operated, no hot work.
- Annual valve-proving / solenoid leak test.
