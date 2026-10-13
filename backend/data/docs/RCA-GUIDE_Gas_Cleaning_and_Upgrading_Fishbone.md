# RCA Guide — Gas Cleaning and Upgrading (Fishbone + 5-Why)

Scope: H2S Scrubber Vessel, Gas Filtration Skid, Chiller, Membrane Upgrader.
Method: list possible causes on the 6M fishbone, use field checks to narrow to one direct cause, then ask "why?"
until you reach a systemic root cause (usually a Method, Man or Material gap) and fix that with a preventive action.

## 1. Fishbone — effect: "BUU product off-spec / gas train abnormal"

### Man (people)
- Filter bypass left open across a shift change; bypass used to beat high dP.
- Air-dosing rotameter opened to "stretch" media life.
- Chiller setpoint lowered below 1 °C to chase purity (icing).
- Reheater bypass not restored after maintenance.
- Contract crew fitting the scrubber mesh without a vessel briefing.

### Machine
- Scrubber top distributor mesh misaligned / perimeter seal gap (channeling).
- Filter element rupture / collapse.
- Chiller auto-drain trap stuck; refrigerant leak; Chiller Pump trip or air lock.
- Membrane recycle valve positioner hunting; compressor oil carry-over.

### Method
- Media change-out on calendar instead of sulfur loading.
- No mesh acceptance check / torque sign-off in SOP-SCR-02.
- No dP-based filter change-out limit; no spare elements.
- Element fitted without second-person check; HMI allows sub-zero chiller setpoints.
- Feed pressure setpoint changed without MOC.

### Material
- Raw-gas H2S above design after a sulfur-rich feed change (press mud, protein waste).
- Free water reaching the scrubber; media grade not suited to wet gas.
- Scrubber fines and pipe scale loading filters.
- VOC / siloxanes / oil reaching the membranes; spent guard bed carbon.

### Measurement
- H2S analyser drift / wet sample line.
- Filter dP impulse lines wet; transmitter out of calibration.
- Chiller outlet temperature / dew point sensor drift.
- CH4 analyser drift — false MEM-01 trips or hidden off-spec.

### Environment
- Cold / monsoon weather condensing water in uninsulated gas lines.
- Dusty harvest season choking the chiller condenser filter.
- Peak summer ambient beating the chiller and overheating the membrane container.
- H2S-laden air corroding copper refrigerant joints.

## 2. Worked 5-Why examples

### A. Scrubber dP sudden drop and black powder at the filter skid (KB-0702)
1. Why did dP drop? Gas channeled down the wall past the bed.
2. Why? Perimeter seal gap at the top distributor mesh.
3. Why? Mesh refitted after media change without a torque or contact check.
4. Why? SOP-SCR-02 had no mesh acceptance step.
5. Root cause (Method): change-out procedure lacks an acceptance check.
Preventive action: signed mesh-contact and 25 N·m torque check; photo of the perimeter before closing the manway.

### B. Methane purity 92% (KB-0706)
1. Why purity drop? Liquid water reached the membrane fibres.
2. Why? Chiller separator flooded.
3. Why? Auto-drain trap blocked with sludge.
4. Why not noticed? No strainer before the trap and no alarm on drain cycling.
5. Root cause (Machine / Measurement): unprotected, unmonitored drain.
Preventive action: Y-strainer before the trap, SCADA alarm on drain cycles < 2/h, monthly trap PM.

### C. Filter dP rose to 0.36 bar, then fell (KB-0710)
1. Why the fall? Element pleats split.
2. Why? dP far above the 0.30 bar high-high limit.
3. Why not changed? No spare elements in stock.
4. Why? No re-order point for filter elements.
5. Root cause (Method): spares planning.
Preventive action: two element sets in stock, re-order point, high / high-high dP alarms.

### D. Outlet H2S rising two months early (KB-0707)
1. Why? Media used up twice as fast as planned.
2. Why? Raw-gas H2S doubled.
3. Why? Press-mud share raised for gas yield.
4. Why not caught? Feed recipe changes are not reviewed for sulfur impact on the BUU.
5. Root cause (Material / Method): no sulfur check in feed change control.
Preventive action: sulfur impact check for recipe changes; agreed maximum press-mud share; daily sulfur-loading log.

## 3. Good root-cause habits
- Stop at a cause you can fix with a procedure, PM task, design change, spec or training — not at "the part failed".
- One direct cause can have several roots: write each with its own preventive action and owner.
- Check the stage upstream first: most membrane problems start at the chiller or guard bed; most filter problems
  start at the scrubber.
- Verify before you blame: cross-check analysers with a tube or portable meter.
- Record the RCA in SiteBrain so the next technician sees the case.
