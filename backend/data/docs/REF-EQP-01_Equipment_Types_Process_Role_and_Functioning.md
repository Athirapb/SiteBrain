# REF-EQP-01 — Equipment Types, Process Role and Functioning (Biogas / CBG Plant)

Before troubleshooting any equipment, know three things: **which type it is**, **what it does in the process** (what feeds it, what it feeds), and **how it works**. The same symptom means different things on different types — a positive-displacement pump must never get the shut-off test a centrifugal pump gets, and a submersible mixer has no gland or coupling to inspect. This reference lists the types found on the plant, how to tell them apart in the field, how each works, what normal looks like, and what must never be done to it.

Values are typical for biogas / CBG plants (OEM practice, FNR Biogas Guide, Hydraulic Institute pump guidance). The plant's own data sheets and commissioning records win where they differ.

## 1. Process flow — where each equipment sits

Feeding (shredder line → H1 / H2 feed tanks) → Primary Sludge Tank → Digesters D1–D4 (heated by the HWG through the recirculation loop) → raw biogas to the double-membrane gas holders → H2S scrubber → gas filtration skid → gas booster blowers → LP compressors → chiller (dehydration) → membrane upgrader → HP compressors → CBG cascade. Off-spec and surplus gas go to the flare. Digestate leaves the digesters by the transfer pumps to solid-liquid separation (decanters, screw presses) → cake to bagging / briquetting, liquid to the concentrated / liquid digestate tanks.

A fault often starts **upstream** (a tank ran low, the gas holder emptied, the feed got thicker, the gas got wetter) or **downstream** (a valve closed, the receiving tank is full, the receiving pressure rose). Always look one step up and one step down before stripping a machine.

| Equipment | What it does |
|---|---|
| H1 / H2 pumps | Pump mixed feed slurry from the feed tank into the digesters |
| Digester RC pumps | Recirculate digester contents (through the heat exchanger where fitted) to mix and heat |
| Transfer pumps | Draw digestate out of the digester to hold its level |
| Decanter feed pumps | Feed digestate at a steady rate to the decanters |
| Cooling water / chiller pumps | Circulate cooling water to the coolers and tower; chilled glycol to the gas cooler |
| Digester side-entry agitators | Mix the digester: feed meets bacteria, even temperature, gas escapes, no sand or scum layers |
| Digester / feed tank top agitators | Slow mixing of the whole tank from the roof |
| PST / CDT agitators (mixers) | Keep solids suspended so the pumps get an even slurry |
| Digester and LDT "blowers" | Support-air blowers for the double-membrane gas holder roof |
| Gas blowers | Boost raw biogas through the scrubber and filters to the LP compressors |
| Flare blower | Boosts surplus / off-spec gas to the flare |
| LP compressors | Compress clean biogas to about 12–15 bar for the chiller and membranes |
| HP compressors | Compress CBG (> 95 % CH4) to about 250 bar for the cascade |
| Plant air compressors | Instrument and service air |
| HWG 1 / 2 | Burn biogas to heat the digester heating water |
| Chiller | Cools compressed gas to 2–5 °C so water condenses out before the membranes |

## 2. Pumps

**How to tell them apart**
- **Centrifugal pump** — round spiral (volute) casing, suction on the end, discharge on top, motor coupled directly. Smooth, steady flow. Used for water, cooling water, chilled water and service water.
- **Rotary lobe pump** — square-ish pump head with a flat front cover, two shafts side by side, a timing-gear box behind, suction and discharge ports opposite each other. Flow pulses slightly. Common for digestate recirculation and transfer.
- **Progressive cavity (PC / eccentric screw / "mono") pump** — long and thin: a tubular stator housing between the suction chamber and the discharge, motor and gearbox at the far end. Very smooth flow. Used where a steady dose is needed — decanter feed, thick sludge.
- **Submersible / chopper pump** — sits under the slurry on guide rails; only the discharge pipe, lifting chain and cable are visible.

**How they work and what it means for troubleshooting**
- *Centrifugal:* an impeller throws the liquid outward. Flow falls as delivery pressure rises; it needs a flooded suction (NPSH) and should not run dry or against a shut valve for more than a few seconds. A short **shut-off test** (close the discharge valve for a few seconds, read the pressure) tells impeller wear from system problems.
- *Rotary lobe:* two lobed rotors, timed by gears, carry pockets of slurry round the casing. **Positive displacement — flow stays almost constant as pressure rises**, so a closed or blocked discharge drives pressure up until a pipe, seal or the pump fails. **Never shut-off test.** Wear shows as loss of flow at the same speed (lobe and wear-plate wear from sand); a knock or rub points to the timing gear or bearings.
- *Progressive cavity:* a helical rotor turns in a rubber stator. Positive displacement too — **never against a closed valve**. The rubber stator **burns out within seconds of dry running**; the dry-run protection (stator temperature or flow sensor) must work. Loss of flow with a warm stator or rubber in the outlet = stator damage.
- *Submersible:* sealed motor cooled by the liquid around it; protected by seal-leak (moisture) and thermal sensors. No external coupling, gland or bearing housing to check — read the protection relay instead. Lift only on the chain, power isolated.

**Normal:** discharge pressure steady at the duty point; seal / quench dry or a slight weep; bearings below 70 °C; current steady near (below) nameplate.

## 3. Agitators and mixers

- **Side-entry agitator** — motor and gearbox outside the tank wall; horizontal shaft through the wall at a **gland or mechanical seal**; propeller inside below the level. Gland should weep 10–20 drops / min (packing), never stream slurry and never run bone dry.
- **Top-entry agitator** — gearbox on the roof, long vertical shaft hanging into the tank, paddles / hydrofoils near the bottom, turning slowly. No bottom bearing: imbalance (fibre wraps, lost paddle) shows as shaft swing and vibration at the gearbox. A **roof seal** keeps biogas in — gas-test before working on the drive.
- **Submersible mixer** — motor and gearbox under the slurry on a guide mast with a winch; only the mast and cable are visible. Seal-leak and thermal sensors protect it.

**Process role:** mixing brings feed to the bacteria, evens out temperature, releases gas bubbles and stops floating crust and settled sand. Mixing that stops shows as falling gas production, crust and foam.

**Process conditions that look like agitator faults:** level too low (propeller near the surface → vortex, gas drawn in, vibration, current swinging every turn); thick, high-TS contents or a floating crust (overload, high current); foaming from a digester upset; long fibre wrapping the propeller.

**Normal:** gearbox output bearing below 70 °C; gearbox oil clean amber at level; current steady; the surface moving evenly.

## 4. Blowers

- **Biogas booster blower** (gas blowers, flare blower) — in the gas line, with a condensate knock-out pot and drains before it, usually in an enclosure with gas detection. Raises gas pressure by tens of mbar. Handles wet, corrosive, flammable gas: **drain condensate before it, keep every joint gas-tight**.
- **Membrane-roof support-air blower** (digester and LDT blowers) — a small radial fan feeding air between the outer and inner membranes of the double-membrane gas holder through a non-return flap; a relief valve sets the air pressure. Runs continuously. If it can't hold pressure, look at the **roof** (relief valve stuck open, torn membrane, loose clamping rail), not only the blower. **CH4 in the support-air exhaust means the inner membrane leaks — treat it as a gas hazard.**

**Process conditions that look like blower faults:** gas holder low / gas production down (blower starves and surges); valve part-closed or NRV stuck (high back-pressure); condensate in the line (pulsing, imbalance).

## 5. Compressors

- **Reciprocating compressor** (LP 1–4, HP 1–3) — crankcase with cylinders and valve covers, coolers between stages, rhythmic beat. Pistons draw gas in through suction valves and push it out through discharge valves; crankcase oil lubricates the running gear; rod packing seals gas at each piston rod. Watch: crankcase oil 60–80 %, stage discharge temperatures, interstage pressures, gas at the packing vent.
- **Oil-injected screw air compressor** (plant air) — packaged unit with a separator tank, oil cooler and intake filter, continuous hum. Two rotors squeeze air; injected oil seals and cools and is separated out again. Loads / unloads on pressure through the inlet valve. Typical faults: oil too hot (cooler fouled, thermostatic valve, low oil), separator choked (oil carry-over, high separator dP), inlet / unloader valve or intake filter (won't load, low pressure).

**Process conditions that look like compressor faults:** low suction pressure (blowers or gas holder can't supply — unloading, cycling, low-suction trips); liquid or particles arriving from upstream (scrubber media, condensate); hot inlet gas in summer.

## 6. Hot water generator (HWG)

Forced-draft biogas burner and gas train on a boiler shell, ID fan and stack, flow / return to the digester heating loop. The burner controller proves air, gas pressure and flame before and during firing. **Burner lockouts are often the gas, not the burner:** low methane (below ~48 %), high O2 from air dosing, water in the gas line, or low gas pressure when the holder is low. Normal: flow–return ΔT about 8–12 °C, flue O2 3–6 % with low CO, steady gas pressure.

## 7. Chiller (gas dehydration)

- **Air-cooled** — condenser coils and fans on the unit; dusty / matted condenser filter is the classic summer fault.
- **Water-cooled** — no fans; a shell-and-tube condenser fed by the cooling water pumps and the cooling tower. If the cooling water is short (pump tripped, tower fan off, basin strainer blocked, scaled tubes) the chiller trips on high condensing pressure.
Both chill glycol / water that cools the compressed gas to 2–5 °C so water condenses and drains out before the membranes. **Process load:** hot afternoons and high gas flow push the outlet temperature up; a setpoint below 1 °C freezes the gas-side exchanger.

## 8. Separation, feeding and gas cleaning

- **Decanter centrifuge (solid-bowl, 2-phase)** — bowl at ~3,000 rpm settles solids on its wall; the scroll, turning slightly slower (the differential), pushes them out as cake; centrate overflows at the other end. Polymer flocculates the solids first. Feed solids, flow and polymer are process causes of wet cake and dirty centrate.
- **Screw press separator (WAM)** — a screw squeezes digestate against a cylindrical screen; filtrate passes the screen, fibre leaves as a plug of cake against weighted outlet flaps. Feed consistency, fibre and sand, wash water and outlet counter-pressure set the performance.
- **Twin-shaft shredder line** — two slow, high-torque cutter shafts; auto-reverse on hard objects; conveyor to the feed tanks. Wet, sticky or over-long feed and foreign objects are process causes.
- **Dry-media H2S scrubber** — iron-oxide (or impregnated) media binds H2S; a little dosed air regenerates it; changed when outlet H2S breaks through. **Air dosing adds O2 and N2 to the gas.**
- **Cartridge gas filter skid** — duty and guard filters with dP gauges and a locked bypass; elements load with fines and are changed at the dP limit.
- **Hollow-fibre membrane upgrader** — CO2 permeates the fibre wall faster than methane, so the retentate becomes CBG > 95 % CH4. Needs dry (dew point 2–5 °C), clean, oil-free gas at 12–15 bar and the design temperature. **Nitrogen is not separated from methane** — air in the raw gas caps the product purity whatever the membranes do.

## 9. Never do

| Type | Never |
|---|---|
| Rotary lobe / PC pump | Run against a closed discharge valve (no shut-off test) |
| PC pump | Run dry, even for seconds |
| Centrifugal pump | Run dry or dead-headed for more than a few seconds |
| Submersible pump / mixer | Lift by the cable; work on it with power not locked off |
| Top-entry agitator | Work on the drive without a gas test at the roof seal |
| Support-air blower | Ignore CH4 in the support-air exhaust |
| Any interlocked equipment | Bypass an interlock to restart without an authorised, logged bypass |
