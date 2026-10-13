# OEM Manual Extract — Digester Agitator Gearbox

Applies to: digester side-entry agitators (D1–D4 "Dx Agitator 1–4"), top-entry agitators ("Dx Top Agitator 1–2"),
feed-hall agitators (H1/H2 side and top, SBT top) and CDT / PST agitators.
Always stop and isolate under LOTO (SOP-ROT-01) before opening guards, sampling oil from the drain or touching the gland.

## Lubrication
- Oil: ISO VG 320 synthetic gear oil (PAO). Level at mid sight glass (60–80%). Never mix mineral and synthetic oil.
- Change interval: 8,000 running hours, or earlier when the oil darkens with metal fines or turns milky.
- Take an oil sample every quarter: check colour, water (crackle test / milky look) and fines on a magnet.
- Milky oil indicates water ingress through the breather or the output shaft seal.
- Fit a desiccant breather with a rain hood; change it when the crystals change colour.
- Grease the motor bearings per the motor nameplate (quantity and interval); do not over-grease.

## Bearing temperatures
- Normal output bearing housing: 55–70°C.
- Alert: 70–85°C — check oil level, alignment, and load (motor current, digester TS, crust).
- Trip: above 85°C — stop under LOTO; bearing failure imminent.
- Measure with an IR gun on painted metal at the output bearing housing; compare with the fixed sensor.

## Vibration
- Measure in mm/s RMS at the gearbox output bearing and motor bearings (ISO 10816, class II).
- Good: below 2.8 mm/s. Acceptable: up to 4.5 mm/s. Alert: 4.5–7.1 mm/s. Stop and inspect: above 7.1 mm/s.
- A rise of 50% over the last monthly reading is an alert even if the value is still "acceptable".
- Bearing wear usually shows in the vibration trend 4–6 weeks before failure — trend it, do not just spot-check.
- Fixed sensors must be stud-mounted on a spot-faced pad. A magnet on paint gives false high readings.

## Coupling alignment
- Laser align motor to gearbox: offset ≤ 0.05 mm, angularity ≤ 0.05 mm/100 mm.
- Check for soft foot (≤ 0.05 mm) before final alignment; record the result on the work order.
- Replace elastomer coupling element every 2 years or when cracked, hardened or shedding black dust.
- Re-torque base bolts quarterly.

## Gland packing
- 5 rings of braided PTFE-graphite packing, joints staggered 90°.
- Seat each ring separately; tighten the follower evenly, finger-tight plus a quarter turn, then adjust running.
- Allow slight weep (10–20 drops/min) on slurry duty. A dry, hot gland is over-tightened and will score the sleeve.
- Major leakage indicates sleeve scoring. Check shaft run-out with a dial gauge (limit 0.1 mm) at every repack.
- Use a hard-coated sleeve where the slurry carries sand (press mud, dung).

## Impeller and shaft
- Inspect impeller blades, hub bolts and blade angle at every tank outage.
- Ragging (fibre and twine wrap) gives a once-per-revolution knock and a current that swings every turn.
  If the drive and VFD allow it, a short reverse run often sheds the wrap.
- Long-shaft top-entry agitators: check the shaft for bending and the steady bearing (if fitted) for wear.

## Process load on the agitator
- Contents above about 12% TS, a thick floating crust, or settled sand raise motor current and gearbox load.
- After any long stop (> 2 h) restart agitators one at a time and watch the current; break crust before full feeding.
- Foam reaching the sight glass: reduce feed and follow SOP-DIG-01 before running agitators at full speed.

## Preventive maintenance schedule
| Interval | Task |
|---|---|
| Every shift | Noise, gland weep, oil level at sight glass, digester surface via sight glass |
| Weekly | IR temperature at output bearing, breather colour, motor current trend |
| Monthly | Handheld vibration route, gland adjustment, motor bearing grease |
| Quarterly | Oil sample, coupling element inspection, base-bolt torque, sensor mounting check |
| 8,000 h / yearly | Oil change, laser alignment check, megger test of motor (before monsoon) |
| Tank outage | Impeller, hub bolts, shaft and sleeve inspection |

## Typical failure modes
- Gearbox output bearing wear: rising vibration, rhythmic growl, hot bearing, metal fines in oil.
- Coupling misalignment: vibration at 2× running speed, worn coupling element, warm coupling, clunk at start.
- Impeller fouling with fibres: vibration varying with tank level and feed consistency; current swinging per turn.
- Gland packing wear: slurry stream at the shaft; scored sleeve.
- Water in oil: milky oil, rising bearing temperature after rain or washdown.
- Overload: high current and trips with crust, sediment or high-TS contents.
- False alarm: SCADA vibration high but handheld reading and sound normal — check sensor mounting and cable.
