import { useEffect, useRef, useState } from "react";

// Render at the container's real pixel width so axis text stays at its true size.
function useWidth(fallback = 560) {
  const ref = useRef(null);
  const [w, setW] = useState(fallback);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return undefined;
    const ro = new ResizeObserver(([e]) => setW(Math.max(240, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

// Shared chart conventions: one y-axis, recessive grid, 4px rounded data-ends,
// 2px surface gaps between adjacent fills, hover tooltip on every mark.
const GRID = "#ededed";
const AXIS = "#868686";

function niceMax(v) {
  if (v <= 0) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(v)));
  const n = v / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p;
}

function Tip({ tip }) {
  if (!tip) return null;
  return (
    <div className="tip" style={{ left: tip.x, top: tip.y }}>
      {tip.text}
    </div>
  );
}

function roundedTop(x, y, w, h, r = 4) {
  if (h <= 0) return "";
  r = Math.min(r, w / 2, h);
  return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
}

/** Vertical bars. data: [{label, value, color?, note?}] */
export function BarChart({ data, height = 200, color = "#5fa414", fmt = (v) => v, max }) {
  const [tip, setTip] = useState(null);
  const [ref, W] = useWidth();
  const H = height, padL = 36, padB = 26, padT = 10;
  const top = niceMax(max ?? Math.max(1, ...data.map((d) => d.value || 0)));
  const iw = W - padL, ih = H - padB - padT;
  const slot = iw / Math.max(1, data.length);
  const bw = Math.max(6, Math.min(40, slot * 0.55));
  const ticks = [0, 0.5, 1].map((t) => t * top);
  return (
    <div className="chart" ref={ref} onMouseLeave={() => setTip(null)}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="bar chart">
        {ticks.map((t) => {
          const y = padT + ih - (t / top) * ih;
          return (
            <g key={t}>
              <line x1={padL} x2={W} y1={y} y2={y} stroke={GRID} />
              <text x={padL - 6} y={y + 4} fontSize="11" textAnchor="end" fill={AXIS}>{fmt(t)}</text>
            </g>
          );
        })}
        {data.map((d, i) => {
          const h = ((d.value || 0) / top) * ih;
          const x = padL + slot * i + (slot - bw) / 2;
          const y = padT + ih - h;
          return (
            <g key={d.label}
               onMouseMove={(e) => {
                 const r = e.currentTarget.ownerSVGElement.getBoundingClientRect();
                 setTip({ x: ((x + bw / 2) / W) * r.width, y: (y / H) * r.height, text: `${d.label}: ${fmt(d.value ?? 0)}${d.note ? ` · ${d.note}` : ""}` });
               }}>
              <rect x={padL + slot * i} y={padT} width={slot} height={ih} fill="transparent" />
              <path d={roundedTop(x, y, bw, h)} fill={d.color || color} />
              <text x={x + bw / 2} y={H - 8} fontSize="11" textAnchor="middle" fill={AXIS}>{d.short ?? d.label}</text>
            </g>
          );
        })}
      </svg>
      <Tip tip={tip} />
    </div>
  );
}

/** Stacked vertical bars. series: [{key,label,color}], data: [{label, ...values}] */
export function StackedBars({ data, series, height = 200 }) {
  const [tip, setTip] = useState(null);
  const [ref, W] = useWidth();
  const H = height, padL = 44, padB = 26, padT = 10;
  const top = niceMax(Math.max(1, ...data.map((d) => series.reduce((a, s) => a + (d[s.key] || 0), 0))));
  const iw = W - padL, ih = H - padB - padT;
  const slot = iw / Math.max(1, data.length);
  const bw = Math.max(10, Math.min(56, slot * 0.5));
  return (
    <div className="chart" ref={ref} onMouseLeave={() => setTip(null)}>
      <div className="legend" style={{ marginBottom: 6 }}>
        {series.map((s) => (
          <span key={s.key}><i style={{ background: s.color }} />{s.label}</span>
        ))}
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="stacked bar chart">
        {[0, 0.5, 1].map((t) => {
          const y = padT + ih - t * ih;
          return (
            <g key={t}>
              <line x1={padL} x2={W} y1={y} y2={y} stroke={GRID} />
              <text x={padL - 6} y={y + 4} fontSize="11" textAnchor="end" fill={AXIS}>{Math.round(t * top)}</text>
            </g>
          );
        })}
        {data.map((d, i) => {
          const x = padL + slot * i + (slot - bw) / 2;
          let acc = 0;
          const total = series.reduce((a, s) => a + (d[s.key] || 0), 0);
          const segs = series.map((s, k) => {
            const v = d[s.key] || 0;
            const h = (v / top) * ih;
            const y = padT + ih - acc - h;
            acc += h;
            const isTop = series.slice(k + 1).every((n) => !(d[n.key] > 0));
            return v > 0 ? (
              isTop ? <path key={s.key} d={roundedTop(x, y, bw, Math.max(0, h - (k ? 2 : 0)))} fill={s.color} />
                : <rect key={s.key} x={x} y={y + (k ? 2 : 0)} width={bw} height={Math.max(0, h - (k ? 2 : 0))} fill={s.color} />
            ) : null;
          });
          return (
            <g key={d.label}
               onMouseMove={(e) => {
                 const r = e.currentTarget.ownerSVGElement.getBoundingClientRect();
                 setTip({ x: ((x + bw / 2) / W) * r.width, y: ((padT + ih - acc) / H) * r.height + 30,
                          text: `${d.label} · ` + series.map((s) => `${s.label} ${d[s.key] || 0}`).join(" · ") + ` · total ${total}` });
               }}>
              <rect x={padL + slot * i} y={padT} width={slot} height={ih} fill="transparent" />
              {segs}
              <text x={x + bw / 2} y={H - 8} fontSize="11" textAnchor="middle" fill={AXIS}>{d.label}</text>
            </g>
          );
        })}
      </svg>
      <Tip tip={tip} />
    </div>
  );
}

/** Single-series line with optional dashed target. data: [{label, value}] (value may be null) */
export function LineChart({ data, height = 200, color = "#5fa414", target, fmt = (v) => v, min = 0, max = 100 }) {
  const [hover, setHover] = useState(null);
  const [ref, W] = useWidth();
  const H = height, padL = 36, padB = 26, padT = 12, padR = 12;
  const iw = W - padL - padR, ih = H - padB - padT;
  const x = (i) => padL + (data.length === 1 ? iw / 2 : (i / (data.length - 1)) * iw);
  const y = (v) => padT + ih - ((v - min) / (max - min)) * ih;
  const pts = data.map((d, i) => (d.value == null ? null : [x(i), y(d.value)]));
  const path = pts.reduce((acc, p, i) => (p ? acc + `${acc && pts[i - 1] ? "L" : "M"}${p[0]},${p[1]}` : acc), "");
  return (
    <div className="chart" ref={ref}
         onMouseLeave={() => setHover(null)}
         onMouseMove={(e) => {
           const r = e.currentTarget.getBoundingClientRect();
           const px = ((e.clientX - r.left) / r.width) * W;
           const i = Math.round(((px - padL) / iw) * (data.length - 1));
           setHover(Math.max(0, Math.min(data.length - 1, i)));
         }}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="line chart">
        {[0, 0.5, 1].map((t) => {
          const v = min + t * (max - min);
          return (
            <g key={t}>
              <line x1={padL} x2={W - padR} y1={y(v)} y2={y(v)} stroke={GRID} />
              <text x={padL - 6} y={y(v) + 4} fontSize="11" textAnchor="end" fill={AXIS}>{fmt(v)}</text>
            </g>
          );
        })}
        {target != null && (
          <g>
            <line x1={padL} x2={W - padR} y1={y(target)} y2={y(target)} stroke="#3d3d3d" strokeDasharray="4 4" />
            <text x={W - padR} y={y(target) - 6} fontSize="11" textAnchor="end" fill="#3d3d3d">target {fmt(target)}</text>
          </g>
        )}
        <path d={path} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
        {pts.map((p, i) => p && <circle key={i} cx={p[0]} cy={p[1]} r={hover === i ? 5 : 4} fill={color} stroke="#fff" strokeWidth="2" />)}
        {hover != null && <line x1={x(hover)} x2={x(hover)} y1={padT} y2={padT + ih} stroke="#b6b6b6" />}
        {data.map((d, i) => (
          <text key={d.label} x={x(i)} y={H - 8} fontSize="11" textAnchor="middle" fill={AXIS}>{d.short ?? d.label}</text>
        ))}
      </svg>
      {hover != null && (
        <div className="tip" style={{ left: `${(x(hover) / W) * 100}%`, top: 0, transform: "translate(-50%, 0)" }}>
          {data[hover].label}: {data[hover].value == null ? "no data" : fmt(data[hover].value)}
        </div>
      )}
    </div>
  );
}

/** Small sparkline for telemetry tags. */
export function Sparkline({ values, color = "#3191ef", width = 120, height = 28 }) {
  const nums = values.filter((v) => typeof v === "number");
  if (!nums.length) return null;
  const lo = Math.min(...nums), hi = Math.max(...nums);
  const span = hi - lo || 1;
  const d = nums.map((v, i) => `${i ? "L" : "M"}${(i / Math.max(1, nums.length - 1)) * (width - 4) + 2},${height - 3 - ((v - lo) / span) * (height - 6)}`).join("");
  return (
    <svg width={width} height={height} aria-hidden="true">
      <path d={d} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

/** Horizontal bars with labels — used for Pareto (cumulative % shown as text, not a second axis). */
export function HBars({ data, color = "#5fa414", fmt = (v) => v, extra }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {data.map((d) => (
        <div key={d.label} title={`${d.label}: ${fmt(d.value)}`} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div className="row" style={{ fontSize: 14 }}>
            <span className="grow" style={{ color: "var(--t80)" }}>{d.label}</span>
            <span style={{ fontWeight: 600 }}>{fmt(d.value)}</span>
            {extra && <span className="caption" style={{ minWidth: 70, textAlign: "right" }}>{extra(d)}</span>}
          </div>
          <div className="bar"><div style={{ width: `${(d.value / max) * 100}%`, background: d.color || color }} /></div>
        </div>
      ))}
    </div>
  );
}
