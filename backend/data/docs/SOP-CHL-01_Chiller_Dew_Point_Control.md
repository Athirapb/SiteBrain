# SOP-CHL-01 — Chiller & Dehydration Unit: Dew Point Control

Applies to: Chiller (gas-to-glycol/water exchanger, condensate separator with auto-drain, refrigeration circuit with
air-cooled condenser and filter) and Chiller Pumps 1 / 2.

## Normal baseline
- Gas outlet temperature 2–5°C; condensate auto-drain cycling 4–8 times per hour (about 6).
- Chiller setpoint 3 °C — never below 1 °C (gas-side icing).
- Chilled-water supply cold, return a few degrees warmer; one Chiller Pump running, the other on auto standby.
- Refrigerant sight glass clear with the compressor running; glycol strength 25–30%.
- Gas is reheated after the chiller so it reaches the membranes at least 10 °C above its dew point.

## Limits and interlocks
- Gas temperature above 8°C or water carryover downstream: interlock CHL-01 halts feed to the separation membranes.
- Methane purity below 95% at the membrane outlet: interlock MEM-01 diverts off-spec gas to flare / recycle loop and prevents pipeline injection.
- Release CHL-01 only after dew point is back within 2–5 °C and the drain has cycled normally for 30 minutes.

## Shift checks
1. Read gas outlet temperature (local gauge and SCADA) and dew point.
2. Watch the auto-drain for 5 minutes — it must discharge.
3. Look at the refrigerant sight glass and the condenser filter.
4. Check Chiller Pump discharge pressures and the run lamps.
5. Note ambient temperature and BUU gas flow.

## Troubleshooting
1. Condenser-side filter choked: clean filter, check refrigerant pressures, schedule weekly cleaning (daily in dusty / harvest season).
2. Auto-drain not cycling: manually drain separator, clean or replace the drain trap and its Y-strainer, verify cycling.
3. Bubbles in refrigerant sight glass: low charge — leak test and recharge (certified refrigeration technician only). Oily patches on joints show where it leaks.
4. Chilled water supply and return almost the same temperature: check Chiller Pumps (tripped / air-locked), vent the high points, check glycol level.
5. Frost on the exchanger outlet or setpoint below 1 °C: restore 3 °C setpoint, reduce flow, defrost and drain the separator well while the ice melts — a water slug follows.
6. Outlet warm only on hot afternoons or at high flow: heat load above rating — shade the condenser, check the compressor after-cooler, reduce flow.
7. SCADA and local readings disagree: check with a calibrated probe in the spare thermowell; recalibrate the sensor.
8. Membranes exposed to moisture must be dried per OEM procedure before returning to service.

## Safety
- Isolate and lock out the condenser fan before cleaning — it starts automatically on head pressure.
- Opening the separator or drain trap: depressurise, gas-test, wear an H2S monitor; condensate is acidic and smells of H2S.
- Refrigerant work only by certified technicians; never vent refrigerant.

## Preventive maintenance
| Interval | Task |
|---|---|
| Weekly | Clean condenser filter; clean drain-trap Y-strainer |
| Monthly | Strip and test auto-drain; test Chiller Pump auto-changeover; vent air |
| Quarterly | Refrigerant leak test; glycol strength by refractometer |
| 6-monthly | Calibrate outlet temperature / dew point sensors; test anti-freeze cut-out |
| Yearly | Chemical clean of coils; refrigeration compressor service |

## Alarms recommended in SCADA
- Drain cycles below 2 per hour; separator high level.
- Gas outlet temperature above 5.5 °C (pre-alarm) and 8 °C (CHL-01).
- Setpoint changes logged with user name; setpoint clamped to 2–5 °C.
