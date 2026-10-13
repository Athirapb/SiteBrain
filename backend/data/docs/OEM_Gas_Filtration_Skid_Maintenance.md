# Gas Filtration Skid — Operation and Maintenance (OEM guidance)

Equipment: Gas Filtration Skid downstream of the H2S Scrubber Vessel. Duty / standby housings with particulate and
coalescing elements, a bypass valve (normally locked closed), housing drains with traps, local dP gauge and SCADA dP
transmitter, and a secondary guard filter ahead of the Gas Blowers / LP Compressors.

## 1. Purpose
Stop scrubber media fines, pipe scale and liquid droplets before they reach blowers and compressors. Particles in
compressor suction score cylinders and valves within hours.

## 2. Normal operating values
| Parameter | Normal | Action |
|---|---|---|
| Element dP (clean) | 0.05–0.10 bar | Trend daily |
| Change-out dP | 0.20 bar | Change over to standby and replace |
| High-high dP | 0.30 bar | Risk of element collapse — change immediately |
| Bypass valve | Closed and locked | Open only under permit |
| Secondary guard filter | In service, small positive dP | Must stay active whenever bypass is open |
| Housing drain | Dry or a few drops | Lots of water = liquid loading |

## 3. Interlocks and advisories
- FLT-01 (interlock): bypass open while the secondary guard filter is not active — bypass execution is invalid.
- FLT-02 (advisory): bypass open with guard active — allowed only under permit; log the bypass window.
- CMP-01 (interlock): particles found downstream or element rupture — LP compressor load line tripped.
- SCR-01: during scrubber channeling the bypass is locked closed.

## 4. Reading the dP trend
- Rising steadily: normal loading, or faster loading from scrubber fines / wet gas.
- Rose then suddenly dropped: element ruptured or collapsed — treat as particle ingress.
- Flat near zero from the start: element unseated, wrong element, bypass open or the instrument is faulty.
- Local gauge and SCADA disagree: blow down impulse lines, zero the transmitter.

## 5. Element change-out procedure
1. Get the permit. Confirm the secondary guard filter is in service.
2. Line up the standby housing slowly (open inlet, then outlet) and confirm flow on its dP.
3. Isolate the duty housing inlet and outlet; vent to flare; gas-test (LEL and H2S) at the vent.
4. Open the housing; wear gloves and an H2S monitor. Bag the old element wet — it may hold pyrophoric scrubber fines.
5. Note what loaded the element: black granules (scrubber media), brown flakes (pipe scale), wet / oily (liquid).
6. Clean the housing seat. Fit the new element with a new O-ring; check the OEM part number and micron rating.
7. Second-person check of seating; close the housing; torque the lid bolts to the OEM value.
8. Pressurise slowly; leak-test with soap; confirm clean dP (0.05–0.08 bar).
9. Check the bypass is closed and locked; sign the work order. Record the dP before and after.

## 6. Bypass rules
- The bypass is a permit item. Never open it to "beat" a high dP — change elements instead.
- Bypass only with the secondary guard filter active and logged in the bypass register.
- List every open bypass on the shift handover sheet. A limit switch alarms in SCADA when the valve is open.

## 7. Common failure modes
| Failure | Signs | Typical root cause |
|---|---|---|
| Element loading | dP rising steadily | Unscreened new scrubber media; pipe scale |
| Rupture / collapse | dP rises then falls; particles downstream | Change-out deferred, no spares; start-up surge |
| Bypass left open | dP flat; valve open | No close-out sign-off; shift change |
| Liquid loading | Water in drain; swollen elements | Cold uninsulated line; drain trap stuck |
| Wrong fit | dP low from new; particles | Missing O-ring; wrong grade from stores |
| Instrument fault | Gauge and SCADA differ | Wet impulse lines; calibration overdue |

## 8. Preventive maintenance
- Shift: element dP, bypass locked, guard in service.
- Weekly: drain housings; test drain traps; compare local and SCADA dP.
- Monthly: blow down dP impulse lines; inspect compressor suction strainers.
- 6-monthly: calibrate dP transmitter; inspect housing internals.
- Stores: keep two complete element sets with O-rings; bins labelled by OEM part number.
