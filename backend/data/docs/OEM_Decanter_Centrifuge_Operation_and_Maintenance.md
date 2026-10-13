# OEM Manual Extract — Decanter Centrifuge (Digestate Dewatering)

Applies to: SLS Decanter 1, 2, 3. Compiled from decanter OEM operation & maintenance manuals (Alfa Laval,
Flottweg, GEA style), ISO 10816-3 vibration guidance and plant experience. Always follow the nameplate / OEM
recipe for your specific machine where it differs.

## How it works
- The bowl spins at high speed (typically 2,500–3,500 rpm, 2,000–3,500 g). Solids settle against the bowl wall.
- The scroll (screw conveyor) turns slightly slower than the bowl. The difference is the **differential speed**
  (typically 2–15 rpm on digestate), set by the gearbox and back-drive motor / VFD.
- The scroll pushes cake up the conical beach to the solids ports; clarified liquid (centrate) leaves over the
  weir / pond plates at the other end.
- Polymer is dosed into the feed (or feed tube) to flocculate fine solids.

## Start-up
1. Confirm guards fitted, lubricator full, gearbox oil at level, flush water available.
2. Start the bowl empty and let it reach full speed; vibration must be < 4.5 mm/s before feeding.
3. Start polymer dosing first, then feed at 50 % of recipe flow; increase in steps over 15–20 min.
4. Check torque settles at 50–70 % of maximum and the centrate is clear.

## Shutdown (normal)
1. Stop feed, keep polymer off.
2. Run the **flush sequence**: hot or service water at reduced bowl speed until centrate runs clear (10–20 min).
3. Stop the bowl. It can coast for **10–20 minutes**. Do not open any cover until it has stopped completely and
   LOTO is applied (SOP-ROT-01).

## After a trip or power failure
- Solids left in a stopped bowl set unevenly → heavy imbalance at the next start.
- Always flush at low speed before restarting. If vibration trips during run-up, stop and clean the bowl manually.

## Lubrication
- Main bearings: grease-lubricated, usually by an automatic lubricator. Use only the OEM high-speed bearing grease.
- Regreasing quantity and interval come from the OEM table (bearing size and speed) — typically every 100–400
  running hours. Over-greasing makes the bearing run hot; under-greasing destroys it.
- Check monthly that grease actually reaches each bearing (disconnect the line and pump a shot).
- Gearbox: oil-lubricated. Check level weekly, sample every 3 months (wear metals, water), change per OEM hours.

## Condition monitoring limits
| Parameter | Normal | Alarm | Action |
|---|---|---|---|
| Vibration (bearing housing) | < 4.5 mm/s | ≈ 7 mm/s | Trip ≈ 11 mm/s; stop and investigate |
| Main bearing temperature | < 75 °C | 85 °C | Stop above 90 °C |
| Scroll torque | 50–70 % max | 85 % | High-torque trip protects gearbox |
| Gearbox oil | Clean, at level | Dark / metal / milky | Sample and plan overhaul |

- Trend torque at the same feed rate weekly: a slow upward creep means the scroll flights are wearing.
- A rise in 1× running-speed vibration = imbalance (cake build-up, lost tile). High-frequency rise = bearing damage.

## Scroll and wear parts
- Scroll flights are protected by tungsten-carbide tiles or hard-facing. Grit in the digestate wears them.
- Inspect every 4,000–8,000 h (or per OEM): flight tip wear, cracked or missing tiles, feed zone and solids
  discharge port wear.
- Re-tiling or hard-facing must be followed by **dynamic balancing** of the rotating assembly at an approved
  workshop. Never replace tiles on one side only.

## Process adjustment
- Lower differential speed → longer residence of cake → drier cake, but higher torque and plugging risk.
- Higher differential → wetter cake, lower torque.
- Deeper pond → clearer centrate, wetter cake. Shallower pond → drier cake, dirtier centrate.
- Change one thing at a time, in small steps (0.5–1 rpm), and wait 15 min before judging.

## Typical failure modes
- Main bearing failure: rising temperature, then vibration; cause usually lubrication starvation.
- Imbalance after an unflushed stop: sudden high vibration at start-up.
- Scroll wear: wet cake, rising torque, gradual vibration increase.
- Gearbox / back-drive faults: torque hunting, whine, metal in the oil, encoder / VFD faults.
- Poor flocculation: dirty centrate and wet cake with the machine mechanically healthy.

## Safety
- Never open covers, reach into the solids chute or remove guards while the bowl is turning.
- LOTO the main motor AND the back-drive motor before any intervention.
- Polymer spills are extremely slippery — clean them immediately.
