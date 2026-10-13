# RCA Guide — Agitators and Feeding (Fishbone and 5-Why)

How to use: first find the DIRECT CAUSE with the fishbone (what failed), then ask "why?" until you reach a
ROOT CAUSE that is a system gap (procedure, PM, training, feed quality control, calibration, environment).
A root cause is good when fixing it stops the problem happening on any machine, not just this one.

## Fishbone — digester and feed-hall agitators

| 6M | Common direct causes / contributors |
|---|---|
| Man (People) | Gearbox oil level not checked on rounds; wrong oil grade topped up; gland over-tightened to stop every drip; mixing schedule cut to save power |
| Machine | Gearbox output bearing wear; worn gland packing / scored sleeve; motor or VFD fault; weak nozzle bracket |
| Method | No laser alignment after drive work; calendar-based oil changes; no base-bolt torque check; no contingency mixing plan when one agitator is down |
| Material | Long fibres (napier, straw, twine) ragging the impeller; high-TS feed; sand from press mud and dung settling; floating crust |
| Measurement | Loose vibration sensor giving false alarms; wrong SCADA scaling; TS tested too rarely; FOS/TAC not trended |
| Environment | Water in gearbox oil through open breathers in the monsoon; moisture in motor terminal boxes; heat on roof-mounted drives |

## Fishbone — shredders, conveyors, bagging and briquetting

| 6M | Common direct causes / contributors |
|---|---|
| Man (People) | Loader overfeeding the hopper; lube points missed; single belt replaced instead of a matched set |
| Machine | Blunt blades; drive bearing / gearbox wear; worn belts and chains; worn screw / die on the briquetting machine |
| Method | No tonnage-based blade schedule; no scraper or skirt checks in PM; no alignment after belt or motor change |
| Material | Stones and metal in loads; wet press mud or rain-soaked grass; twine and plastic; sand in digestate solids |
| Measurement | Dusty zero-speed sensor causing trips; weigher zero drift; overload set below motor rating |
| Environment | Uncovered feed yard in the monsoon; fibre dust in bearings; dry-season dust emission |

## Worked 5-Why example 1 — agitator bearing (KB-0412)
Problem: D1 Top Agitator 2 — high vibration, growl, output bearing at 88 °C.
1. Why the vibration and noise? The gearbox output bearing outer race is spalled.
2. Why did it fail early? Oil was dark with metal fines and 3,000 h past its change.
3. Why was the oil not changed? Oil changes were calendar-based and this agitator was missed.
4. Why was it missed? There is no running-hour schedule in the CMMS for agitator gearboxes.
Root cause (Method): no hour-based lubrication schedule.
Preventive actions: 8,000 h oil change in CMMS; quarterly oil sample; monthly vibration route.

## Worked 5-Why example 2 — agitator overload trips (KB-0402)
Problem: D3 Agitators 1 and 3 tripping on overload; crust in the sight glass.
1. Why the trips? Motor current above FLA.
2. Why the high current? Thick contents (TS 14 %) and a floating crust.
3. Why so thick? Feed switched to more press mud without extra dilution.
4. Why no dilution? The feeding SOP had no TS limit and TS was tested only weekly.
Root cause (Method): feed recipe without a TS limit or dilution rule.
Preventive actions: TS target ≤ 12 %, daily TS test at the feed hall, dilution rule in the feeding SOP.

## Worked 5-Why example 3 — shredder choking (KB-0408)
Problem: Shredder 1 Full Line choking repeatedly in July.
1. Why choking? Fibre wrapped on the rotor and bridged in the hopper.
2. Why wrapping? Napier grass was soaked and still tied with twine.
3. Why soaked? The feedstock pad is uncovered and floods in heavy rain.
4. Why twine? No picking step at reception.
Root causes: Environment (uncovered yard) and Man (no picking duty).
Preventive actions: cover and drain the pad; wet : dry blending rule; assign a picker at the tipping floor.

## Worked 5-Why example 4 — bagging machine under-weight (KB-0426)
1. Why under-weight bags? The weigher read 0.6 kg high.
2. Why? Caked manure on the weigh hopper added weight at zero.
3. Why? No shift cleaning or zero check.
Root cause (Measurement / Method): no calibration and zero-check routine.
Preventive actions: shift-start zero check; monthly calibration with certified test weights.

## Tips for a good RCA
- Use evidence: keep the failed part, oil sample, photos and SCADA trends.
- Stop at a cause you can act on across the plant. "Bearing failed" is not a root cause.
- Check whether the same root cause appears on other equipment (e.g. all gearboxes without desiccant breathers).
- Every root cause needs an owner and a due date for the preventive action.
- Record the case in the incident log with the why chain separated by " > ".
