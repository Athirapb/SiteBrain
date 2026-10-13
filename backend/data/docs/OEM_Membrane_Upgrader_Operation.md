# Membrane Upgrader — Operation and Troubleshooting (OEM guidance)

Equipment: Membrane Upgrader — multi-stage (typically three-stage) hollow-fibre polyimide membranes separating CO2
(fast gas, passes to the permeate) from CH4 (stays in the retentate / product). Includes feed reheater, activated-carbon
guard bed for oil / VOC, tail-gas / permeate recycle valve back to compressor suction, product CH4 analyser and
off-spec divert to flare / recycle.

Source types: membrane OEM product literature (e.g. Evonik SEPURAN Green), upgrading skid OEM manuals (Air Liquide,
DMT/Pentair), IEA Bioenergy Task 37 upgrading reviews, IS 16087:2016.

## 1. Product specification
| Parameter | IS 16087 CBG | Plant target |
|---|---|---|
| CH4 | ≥ 90% | > 95% (MEM-01 trips below 95%) |
| CO2 | ≤ 4% (cylinder filling) | ≤ 3% |
| CO2 + N2 + O2 | ≤ 10% | — |
| H2S | ≤ 30.3 mg/m³ | — |
| Moisture | ≤ 16 mg/m³ | — |

## 2. Normal operating window
| Parameter | Normal |
|---|---|
| Feed pressure | 12–15 bar g |
| Feed temperature | 20–40 °C and at least 10 °C above the gas dew point |
| Feed dew point (from chiller) | 2–5 °C |
| Permeate dP | ≈ 0.9 bar (commissioning baseline) |
| Tail-gas recycle flow | ≈ 40–45 Nm³/h |
| Methane slip in off-gas | < 1% of feed CH4 |

## 3. What the membrane does not tolerate
- **Liquid water:** condenses in the fibres, blocks them and drops purity. Fibres must be dried before return to service.
- **Compressor oil, VOC, siloxanes, terpenes:** coat the fibres permanently; the activated-carbon guard bed is their only protection.
- **Particles:** plug fibre bores — filters upstream must be intact.
- **Temperature swings:** permeability changes with temperature; too cold allows condensation, too hot lowers selectivity and can exceed the module rating.

## 4. Start-up
1. Confirm chiller dew point 2–5 °C and drain cycling, reheater on and feed temperature in band.
2. Product valve on divert (flare / recycle). Pressurise slowly (≤ 1 bar per minute) to avoid fibre damage.
3. Put the recycle valve in auto once stage pressures are stable.
4. Release to the CBG cascade only after CH4 > 95% for 15 minutes on a verified analyser.

## 5. Troubleshooting purity drop
| Check | Normal | If not |
|---|---|---|
| Chiller dew point / drain | 2–5 °C, cycling | Moisture — CHL-01, dry the membranes |
| Inlet low-point drain | Dry | Water = moisture; oily = fouling |
| Feed pressure | At setpoint | Compressor unloaded / setpoint changed |
| Feed temperature | In band | Reheater TCV, container ventilation |
| Recycle valve stroke | Smooth | Positioner / instrument air |
| Permeate dP vs baseline | Within 30% | Fouling — guard bed, compressor oil |
| Analyser vs portable | Within 1% | Calibrate analyser before anything else |

## 6. Methane slip
High CH4 in the off-gas means product loss and emissions. Causes: recycle valve open too far or hunting, pressure
ratio wrong, damaged module (fibre breakage) or wrong stage cut. Measure off-gas CH4 weekly.

## 7. Drying wet membranes
1. Divert product, isolate the wet stage.
2. Purge with dry gas (dew point below –20 °C) at low pressure until outlet dew point is stable; follow the OEM time.
3. Re-test performance against baseline before return.

## 8. Maintenance
- Weekly: analyser zero/span, coalescer and low-point drains, off-gas CH4.
- Monthly: full analyser calibration, instrument-air dew point, sample filter.
- Quarterly: stroke-test recycle and retentate valves; VOC / siloxane check after guard bed.
- Guard bed: replace on breakthrough or OEM hours — keep one charge in stock.
- Yearly: performance test against commissioning baseline with the OEM.

## 9. Safety
Feed is at 12–15 bar with flammable gas and CO2-rich permeate. Use permits for any drain or sample work, keep a gas
monitor on, and never loosen fittings under pressure. Off-spec product must never be sent to the cascade (MEM-01).
