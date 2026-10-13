# SOP-BUU-01 — Biogas Quality and Gas Train Operating Envelope

Applies to the Biogas Upgradation Unit (BUU) gas train:
Digesters → H2S Scrubber Vessel → Gas Filtration Skid → Gas Blowers → LP Compressors → Chiller → Membrane Upgrader →
HP compressors → CBG cascade. Off-spec / tail gas goes to flare or recycle.

## 1. Why the envelope matters
Each stage protects the next. A fault upstream usually shows up downstream first: wet gas shows as membrane purity
loss, scrubber fines show as filter dP, high H2S shows as compressor corrosion. When a parameter leaves its band,
look one or two stages upstream before adjusting the stage that alarmed.

## 2. Operating envelope
| Stage | Parameter | Normal | Out-of-range action |
|---|---|---|---|
| Raw gas | CH4 | 52–62% | Below 50%: check digester VFA/alkalinity, air ingress |
| Raw gas | CO2 | 35–45% | High: digester upset — inform process team |
| Raw gas | H2S | 500–2,000 ppm | Above design: hold sulfur-rich feed, boost in-digester desulfurisation |
| Raw gas | O2 | < 0.5% (≤ 1% with air dosing) | Above 1%: cut air dosing, find air ingress |
| Scrubber | Bed dP | 0.04–0.06 bar | > 0.10 de-choke; < 0.02 channeling — SCR-01 |
| Scrubber | Outlet H2S | < 10 ppm | > 30 ppm breakthrough — SCR-02, tube-check |
| Scrubber | Outlet O2 (air dosing) | 0.3–0.5% | > 1%: cut dosing, check shell for hot spots |
| Filter skid | Element dP | 0.05–0.10 bar | 0.20 change; sudden drop = rupture — CMP-01 |
| Filter skid | Bypass | Closed and locked | FLT-01 / FLT-02 |
| LP compressors | Discharge | ≈ 6 bar g | See Compressor tree |
| Chiller | Gas outlet / dew point | 2–5 °C | > 8 °C: CHL-01 halts membrane feed |
| Chiller | Drain cycling | 4–8 per hour | None: manual drain, fix trap |
| Membrane | Feed pressure | 12–15 bar g | Low: setpoint / compressor loading |
| Membrane | Feed temperature | 20–40 °C, ≥ 10 °C above dew point | Reheater TCV, ventilation |
| Membrane | Permeate dP | ≈ 0.9 bar | > 30% above baseline: fouling |
| Membrane | Product CH4 | > 95% | < 95%: MEM-01 divert |
| Membrane | Methane slip | < 1% of feed CH4 | Recycle valve, pressure ratio, module |
| Product | CO2 / moisture / H2S | ≤ 4% / ≤ 16 mg/m³ / ≤ 30.3 mg/m³ | Divert; trace failing stage |

## 3. Air / O2 dosing rule
Small air dosing (outlet O2 0.3–0.5%) helps regenerate iron-oxide media in place. Too much air heats the bed (fire
risk with pyrophoric iron sulfide), deposits elemental sulfur that cakes the bed, and carries O2 into the CBG
(CO2 + N2 + O2 ≤ 10% in IS 16087). Dosing setpoint changes are a management-of-change item and must be written in the
shift log with the reason.

## 4. Shift round (BUU gas cleaning)
1. Raw gas CH4 / CO2 / H2S / O2 on the digester analyser.
2. Scrubber dP, outlet H2S, outlet O2; drain the knock-out pot; touch / IR-scan the shell.
3. Filter skid dP (local vs SCADA), bypass locked, guard filter in service, housing drains.
4. Chiller outlet temperature, drain cycling, sight glass, condenser filter, Chiller Pumps.
5. Membrane feed pressure / temperature, permeate dP, recycle flow, product CH4, off-gas CH4.
6. Record everything on the round sheet; anything out of band goes to the shift engineer and into SiteBrain.

## 5. Change control
Any of the following needs shift-engineer approval and a log entry: feedstock recipe changes that add sulfur-rich or
VOC-rich material, air-dosing setpoint, chiller setpoint, membrane feed pressure setpoint, BUU throughput increase,
opening any bypass.

## 6. Safety
- Every opening of a vessel, housing, drain or sample point: isolate, depressurise, purge, gas-test, permit, H2S
  personal monitor.
- Spent scrubber media and filter fines: keep wet, bag or drum closed, never leave dry.
- Off-spec gas is never sent to the CBG cascade — MEM-01 diverts automatically; do not override.
