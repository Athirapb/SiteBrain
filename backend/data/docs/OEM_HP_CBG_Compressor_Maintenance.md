# OEM Guidance — HP CBG Compressor Maintenance (HP 1–3)

Multi-stage (typically 3–4 stage), lubricated reciprocating compressor taking upgraded biomethane at ≈ 6 bar(g) from the membrane unit and delivering CBG to the ~250 bar storage cascade / dispenser. Compiled from typical CNG/CBG compressor OEM manuals, gas-compressor association guidance on valve and packing failures, and plant experience. Always follow the data sheet of the specific machine where values differ.

## Typical operating data
| Item | Typical value |
|---|---|
| Suction pressure | 5–7 bar(g) |
| Final discharge | up to 250 bar(g) (relief ≈ 275 bar) |
| Compression ratio per stage | 2.5–4 |
| Stage discharge temperature | < 150 °C, trip ≈ 160–170 °C |
| After-cooler outlet | < ambient + 15 °C |
| Oil pressure | 2–4 bar |
| Crankcase oil level | 60–80% |
| Frame vibration | < 4.5 mm/s |

Interstage pressures depend on the stage ratio; record the commissioning baseline on the panel. A change of more than ±10% points to the stage with the problem: if stage-2 inlet pressure rises, stage-2 valves or rings are leaking (it is not taking its gas); if it falls, stage-1 is not delivering.

## Preventive maintenance schedule
| Interval | Task |
|---|---|
| Shift | Log pressures, temperatures, oil level & pressure; drain separators; listen for knock; check for gas at packing vents |
| Weekly | IR valve covers; check lubricator feed rate; clean air-cooler fins in dusty season; test cascade priority panel |
| Monthly | Change suction filter at dP limit; vibration readings; test auto-drains |
| Quarterly | Proof-test trips: low oil pressure, low oil level, high discharge temperature, high final pressure; re-torque flanges |
| 4,000 h | Valve overhaul (plates, springs, seats); oil and oil-filter change |
| 8,000 h | Piston rings, rider bands, rod packing; check liner and rod wear |
| 16,000 h | Bearings, crosshead, crankshaft seals; full overhaul |

## Failure modes and what to look for
- **Valve failure** — clatter at a cover, one cover >15 °C hotter, interstage shift. Causes: fatigue, liquid slugs, debris, wrong lift / springs, reversed valve.
- **Ring / rider band wear** — rising blow-by at the breather, falling capacity, a hotter stage. Silica (siloxanes) and iron-sulphide fines make it worse.
- **Rod packing leak** — gas reading at the packing vent / distance piece; vent flow increases. Replace packing; polish or replace the rod if scored.
- **Lubrication failure** — low oil pressure, knock, high bearing temperature. Check level, filter dP, pump and relief valve.
- **High discharge temperature** — fouled coolers, failed fan belt, high ratio from a leaking valve upstream.
- **Flange / fitting leaks** — at 250 bar, use only rated fittings; never tighten a fitting under pressure.

## Safe work at high pressure
1. Permit to work; isolate and **depressurise every stage** to flare; lock the bleed valve open.
2. Purge with nitrogen; gas-test to 0% LEL before opening.
3. Never stand in line with a pressurised fitting or relief valve outlet.
4. LOTO the motor (SOP-ROT-01); try the start button before work.
5. After work: leak test with nitrogen or soap at stages up to working pressure, then return to service.

## Gas quality limits at HP suction
- H2S < 5 ppm (upgraded gas), water dew point well below the lowest ambient at 250 bar, no liquids, particles < 5 µm.
- Off-spec gas from the membrane (MEM-01) must be diverted — never compress wet or sour gas into the cascade.

## Torque and parts
- Use OEM valve kits by part number only; record valve lift and spring set.
- Valve cover bolts: torque in a cross pattern to the OEM chart, re-torque after 24 h hot.
- New gaskets and O-rings every time a joint is opened.
