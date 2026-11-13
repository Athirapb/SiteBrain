// A searchable drop-in for <select>: give it the same <option>/<optgroup> children, value and onChange(e).
// The list opens in a portal (so modals and scroll areas don't clip it) with a search box on top.
import { Children, isValidElement, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Icon } from "./ui";

const text = (node) => Children.toArray(node).map((c) => (typeof c === "string" || typeof c === "number" ? String(c) : isValidElement(c) ? text(c.props.children) : "")).join("");

// <option>/<optgroup> children → [{ value, label, group, disabled }]
function flatten(children, group = "") {
  const out = [];
  Children.toArray(children).forEach((c) => {
    if (!isValidElement(c)) return;
    if (c.type === "optgroup") out.push(...flatten(c.props.children, c.props.label));
    else if (c.type === "option") {
      const label = text(c.props.children);
      out.push({ value: String(c.props.value ?? label), label, group, disabled: !!c.props.disabled });
    } else if (c.type === Symbol.for("react.fragment") || c.props?.children) out.push(...flatten(c.props.children, group));
  });
  return out;
}

export default function SearchSelect({ value, onChange, children, className = "select", disabled, id, style,
                                       "aria-label": ariaLabel, placeholder = "Search…" }) {
  const options = useMemo(() => flatten(children), [children]);
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [hi, setHi] = useState(0);
  const [pos, setPos] = useState(null);
  const btn = useRef(null);
  const pop = useRef(null);
  const listRef = useRef(null);

  const current = options.find((o) => o.value === String(value ?? "")) || options[0];
  const shown = useMemo(() => {
    const words = q.trim().toLowerCase().split(/\s+/).filter(Boolean);
    return options.filter((o) => words.every((w) => `${o.label} ${o.group}`.toLowerCase().includes(w)));
  }, [options, q]);

  const place = () => {
    const r = btn.current?.getBoundingClientRect();
    if (!r) return;
    const below = window.innerHeight - r.bottom;
    const up = below < 280 && r.top > below;
    setPos({ left: r.left, width: Math.max(r.width, 220), top: up ? undefined : r.bottom + 4,
             bottom: up ? window.innerHeight - r.top + 4 : undefined, maxH: Math.min(320, (up ? r.top : below) - 12) });
  };
  useLayoutEffect(() => { if (open) place(); }, [open]);
  useEffect(() => {
    if (!open) return undefined;
    const outside = (e) => { if (!btn.current?.contains(e.target) && !pop.current?.contains(e.target)) setOpen(false); };
    const moved = (e) => { if (!pop.current?.contains(e.target)) place(); };
    document.addEventListener("mousedown", outside);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", moved, true);
    return () => {
      document.removeEventListener("mousedown", outside);
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", moved, true);
    };
  }, [open]);
  useEffect(() => { listRef.current?.querySelector(".hi")?.scrollIntoView?.({ block: "nearest" }); }, [hi, open]);

  const show = () => {
    if (disabled) return;
    setQ("");
    setHi(Math.max(0, options.indexOf(current)));
    setOpen(true);
  };
  const pick = (o) => {
    if (!o || o.disabled) return;
    setOpen(false);
    btn.current?.focus();
    if (o.value !== String(value ?? "")) onChange?.({ target: { value: o.value } });
  };
  const keys = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setHi((i) => Math.min(i + 1, shown.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi((i) => Math.max(i - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); pick(shown[hi]); }
    else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); e.nativeEvent.stopImmediatePropagation?.(); setOpen(false); btn.current?.focus(); }
    else if (e.key === "Tab") setOpen(false);
  };

  let lastGroup = null;
  return (
    <>
      <button type="button" ref={btn} id={id} style={style} disabled={disabled} aria-label={ariaLabel}
              aria-haspopup="listbox" aria-expanded={open} className={`${className} search-select ${open ? "open" : ""}`}
              onClick={() => (open ? setOpen(false) : show())}
              onKeyDown={(e) => { if (!open && ["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) { e.preventDefault(); show(); } }}>
        <span className="search-select-value">{current?.label ?? ""}</span>
        <Icon name={open ? "chevron-up" : "chevron-down"} size={18} />
      </button>
      {open && pos && createPortal(
        <div ref={pop} className="search-select-pop" onMouseDown={(e) => e.stopPropagation()}
             style={{ left: pos.left, width: pos.width, top: pos.top, bottom: pos.bottom }}>
          <div className="search-select-search">
            <Icon name="magnify" size={18} />
            <input autoFocus value={q} placeholder={placeholder} aria-label={`Search ${ariaLabel || "options"}`}
                   onChange={(e) => { setQ(e.target.value); setHi(0); }} onKeyDown={keys} />
          </div>
          <div ref={listRef} className="search-select-list" role="listbox" style={{ maxHeight: Math.max(pos.maxH - 50, 120) }}>
            {shown.map((o, i) => {
              const head = o.group && o.group !== lastGroup ? o.group : null;
              lastGroup = o.group;
              return [
                head && <div key={`g-${head}-${i}`} className="search-select-group">{head}</div>,
                <div key={`${o.group}|${o.value}`} role="option" aria-selected={o === current}
                     className={`search-select-opt ${i === hi ? "hi" : ""} ${o === current ? "on" : ""} ${o.disabled ? "disabled" : ""}`}
                     onMouseEnter={() => setHi(i)} onClick={() => pick(o)}>
                  <span className="grow">{o.label}</span>{o === current && <Icon name="check" size={16} />}
                </div>,
              ];
            })}
            {!shown.length && <div className="search-select-empty">No matches</div>}
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}
