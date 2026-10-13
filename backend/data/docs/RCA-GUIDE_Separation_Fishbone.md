# RCA Guide — Solid-Liquid Separation Fishbone (6M) and 5-Why Examples

Use this guide when a decanter or WAM separator fails or separation performance drops. First find the
**direct cause** on the fishbone, then ask "why?" until you reach a **systemic root cause** (procedure, PM,
feed quality, training, calibration, environment) that a preventive action can fix.

## Fishbone — Decanter centrifuge (high vibration / wet cake / dirty centrate)
| 6M | Typical causes |
|---|---|
| Man | Operator not trained on shutdown flush; lubricator level not checked; settings changed by trial and error |
| Machine | Main bearing wear; scroll tile wear; gearbox / back-drive fault; lubricator pump failure |
| Method | Stop without flush; regreasing not tied to running hours; no setpoint log; no retune when feed changes |
| Material | Wrong / mixed grease; lumpy or old polymer; feed TS swings; grit and sand in digestate |
| Measurement | Loose vibration sensor; feed flowmeter not calibrated; torque sensor drift |
| Environment | Power failures without backup flush water; humid polymer storage; washdown water in connectors |

## Fishbone — WAM screw-press separator (low flow / choking / wet cake)
| 6M | Typical causes |
|---|---|
| Man | Counter-pressure changed without guidance; nozzles not watched; high-pressure lance on screen |
| Machine | Worn brush / flights; torn screen; wash solenoid failure; gearmotor fault |
| Method | Overfeeding when one separator is down; strainer not cleaned; wash timer shortened |
| Material | Long fibres, plastics, rope in feed; grit; dirty or hard wash water |
| Measurement | No feed flowmeter; counter-pressure gauge faulty; no high-current warning |
| Environment | Shared water header pressure drops; washdown water into motor boxes |

## Worked 5-Why example 1 — Decanter 1 high vibration
1. Why did Decanter 1 trip on high vibration? The feed-end main bearing was running hot and rough.
2. Why was the bearing hot? It had no fresh grease — lubrication starvation.
3. Why no grease? The auto-lubricator reservoir had been empty for about a week.
4. Why was that not noticed? Reservoir level is not on the shift round and there is no alarm.
5. Root cause (Man / Method): no routine check or alarm on the lubricator.
- Preventive actions: add level to the shift checklist; wire the lubricator fault contact to SCADA.

## Worked 5-Why example 2 — Decanter 3 vibration at restart
1. Why did vibration trip at run-up? The bowl was out of balance.
2. Why? Solids had set unevenly in the bowl.
3. Why? The machine stopped on a power failure and was not flushed.
4. Why not flushed? The flush pump was also without power.
5. Root cause (Environment / Method): flush water not on backup power; no auto-flush on trip recovery.
- Preventive actions: put flush pump on the DG board; add a PLC flush step before restart after trips.

## Worked 5-Why example 3 — WAM 2 low flow / choking
1. Why is WAM 2 choking? The screen is blinded with matted fibres.
2. Why? The wash spray is weak along the whole bar.
3. Why? Wash water pressure is 0.8 bar instead of ≥ 2 bar.
4. Why? The wash line strainer is blocked.
5. Root cause (Method): strainer cleaning is not on any schedule.
- Preventive actions: weekly strainer cleaning in PM; pressure gauge after the strainer.

## Worked 5-Why example 4 — Wet cake on all decanters
1. Why is the cake wet and the centrate dirty? Flocs are not forming.
2. Why? The polymer solution is full of fish-eyes.
3. Why? The powder had absorbed moisture and lumped.
4. Why? Bags were stored open on the floor of the humid SLS building.
5. Root cause (Environment / Material): uncontrolled polymer storage.
- Preventive actions: sealed dry storage on pallets, FIFO, daily make-up check.

## Tips for a good RCA
- Confirm the direct cause with evidence (temperature, trend, photo, oil sample) before asking "why".
- Stop at a cause you can control with a procedure, PM task, training, calibration or specification.
- Every root cause needs an owner, a preventive action and a due date. Record the case in the incident log.
- If several machines show the same problem, look for a shared cause (feed, polymer, water, power).
