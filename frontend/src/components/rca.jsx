// Root cause analysis visuals: the fishbone (Ishikawa, 6M) and the 5-Why chain.
import { Icon } from "./ui";

export const CATEGORIES = ["Man", "Machine", "Method", "Material", "Measurement", "Environment"];
export const CAT_LABEL = { Man: "People", Machine: "Machine", Method: "Method", Material: "Material", Measurement: "Measurement", Environment: "Environment" };
export const CAT_COLOR = { Man: "#8e44ad", Machine: "#d93a32", Method: "#1c6fc1", Material: "#b36b00", Measurement: "#00838f", Environment: "#2e7d32" };

export function CatChip({ category }) {
  return <span className="cat-chip" style={{ "--fb": CAT_COLOR[category] }}>{CAT_LABEL[category] || category}</span>;
}

// bones: [{category, label, causes: [{label, likelihood, ruled_out}]}]
export function Fishbone({ bones, problem, showPct = true, max = 4 }) {
  const byCat = Object.fromEntries((bones || []).map((b) => [b.category, b]));
  const top = Math.max(0, ...(bones || []).flatMap((b) => b.causes.map((c) => c.likelihood || 0)));
  const bone = (cat, bottom) => {
    const b = byCat[cat];
    return (
      <div key={cat} className={`fb-bone ${bottom ? "bottom" : ""} ${b ? "" : "empty"}`} style={{ "--fb": CAT_COLOR[cat] }}>
        <div className="fb-cat">{CAT_LABEL[cat]}</div>
        {b ? b.causes.slice(0, max).map((c) => (
          <div key={c.label} className={`fb-cause ${c.ruled_out ? "out" : top && c.likelihood === top ? "top" : ""}`}>
            <span>{c.label}</span>
            {showPct && c.likelihood != null && <span className="pct">{Math.round(c.likelihood * 100)}%</span>}
          </div>
        )) : <div className="caption">—</div>}
      </div>
    );
  };
  return (
    <div className="fishbone" role="img" aria-label={`Fishbone diagram of possible causes for ${problem}`}>
      {CATEGORIES.slice(0, 3).map((c) => bone(c, false))}
      <div className="fb-head"><span className="overline" style={{ color: "var(--gps-green-dark)" }}>Problem</span>{problem}</div>
      <div className="fb-spine" />
      {CATEGORIES.slice(3).map((c) => bone(c, true))}
    </div>
  );
}

// chain: [{why, because, own?}]
export function WhyChain({ direct, chain, root, category }) {
  return (
    <div className="why-chain">
      {direct && (
        <div className="why-step direct">
          <span className="why-n"><Icon name="alert-outline" size={14} /></span>
          <div><div className="caption">What failed</div><div style={{ color: "var(--t80)", fontWeight: 600 }}>{direct}</div></div>
        </div>
      )}
      {(chain || []).map((w, i) => (
        <div key={i} className="why-step">
          <span className="why-n">W{i + 1}</span>
          <div>
            <div className="caption">{w.why}</div>
            <div style={{ color: "var(--t80)" }}>{w.because}{w.own && <span className="caption"> · field operator's explanation</span>}</div>
          </div>
        </div>
      ))}
      {root && (
        <div className="why-step root">
          <span className="why-n"><Icon name="target" size={14} /></span>
          <div>
            <div className="row" style={{ gap: 8 }}><span className="caption">Root cause</span>{category && <CatChip category={category} />}</div>
            <div style={{ color: "var(--t90)", fontWeight: 600, lineHeight: 1.4 }}>{root}</div>
          </div>
        </div>
      )}
    </div>
  );
}
