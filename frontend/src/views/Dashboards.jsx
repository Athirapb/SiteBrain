import { useState } from "react";
import { api } from "../api";
import { BarChart, HBars, LineChart, StackedBars } from "../components/charts";
import { Empty, Icon, PillTabs, Spinner, Stat, fmtDuration, fmtTime, useAsync } from "../components/ui";

const SEV_STYLE = {
  Low: ["#f2f2f2", "#6d6d6d", "information-outline"],
  Medium: ["#e8f2fd", "#3191ef", "alert-circle-outline"],
  High: ["#fff7e6", "#b36b00", "alert-outline"],
  Critical: ["#fdeceb", "#d93a32", "alert-octagon-outline"],
};
const HEALTH_STYLE = { Normal: SEV_STYLE.Low, Abnormal: SEV_STYLE.High, Critical: SEV_STYLE.Critical };

export default function Dashboards({ user }) {
  const [period, setPeriod] = useState("daily");
  const [scope, setScope] = useState("site");
  const fleetCapable = !user.site_code;
  const d = useAsync(() => api.get(`/api/analytics/${period}?scope=${scope}`), [period, scope]);
  return (
    <div className="page">
      <div className="row wrap">
        <PillTabs value={period} onChange={setPeriod} options={[["daily", "Daily Operations"], ["weekly", "Weekly Reliability"], ["monthly", "Monthly Executive"]]} />
        <span className="grow" />
        {fleetCapable && <PillTabs value={scope} onChange={setScope} options={[["site", "This Site"], ["fleet", "Whole Fleet"]]} />}
      </div>
      {d.loading && !d.data ? <Spinner /> : d.error ? <Empty icon="alert-outline" title={d.error.message} /> :
        period === "daily" ? <Daily a={d.data} /> : period === "weekly" ? <Weekly a={d.data} /> : <Monthly a={d.data} />}
    </div>
  );
}

function Daily({ a }) {
  return (
    <>
      <div className="stats">
        <Stat label="MTTD · symptom → root cause" value={a.mttd_min != null ? fmtDuration(a.mttd_min) : null} hint="last 24 h" />
        <Stat label="MTTR · symptom → resolved" value={a.mttr_min != null ? fmtDuration(a.mttr_min) : null} hint="last 24 h" />
        <Stat label="Diagnostic Sessions" value={a.sessions_today} hint={`${a.resolved_today} resolved today`} />
        <Stat label="Open Issues" value={a.open_issues} hint={`${a.area_level_today} reported at area level today`} />
      </div>
      <div className="grid-2">
        <div className="card">
          <div className="card-title">Active Anomaly Matrix · open sessions</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
            {a.anomaly_matrix.map((m) => {
              const [bg, fg, icon] = SEV_STYLE[m.severity];
              return (
                <div key={m.severity} style={{ background: bg, borderRadius: 8, padding: 12, display: "flex", flexDirection: "column", gap: 4 }}>
                  <div className="row" style={{ color: fg, fontSize: 12, fontWeight: 600 }}><Icon name={icon} size={16} />{m.severity}</div>
                  <div style={{ fontSize: 28, fontWeight: 500, color: "var(--t90)" }}>{m.count}</div>
                </div>
              );
            })}
          </div>
          <div className="card-title" style={{ paddingTop: 8 }}>Equipment Health · open issues</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
            {a.equipment_health.map((m) => {
              const [bg, fg, icon] = HEALTH_STYLE[m.status];
              return (
                <div key={m.status} style={{ background: bg, borderRadius: 8, padding: 12 }}>
                  <div className="row" style={{ color: fg, fontSize: 12, fontWeight: 600 }}><Icon name={icon} size={16} />{m.status}</div>
                  <div style={{ fontSize: 28, fontWeight: 500 }}>{m.count}</div>
                </div>
              );
            })}
          </div>
        </div>
        <div className="card">
          <div className="card-title">Issues Reported By Shift · last 24 h</div>
          <StackedBars data={a.issues_by_shift.map((s) => ({ label: `Shift ${s.shift}`, resolved: s.resolved, escalated: s.escalated, open: s.open }))}
                       series={[{ key: "resolved", label: "Resolved / closed", color: "#28a745" },
                                { key: "escalated", label: "With expert", color: "#3191ef" },
                                { key: "open", label: "Being troubleshot", color: "#ffa500" }]} />
        </div>
      </div>
      <div className="card">
        <div className="row"><div className="card-title grow">Interlock Event Log · last 24 h</div><span className="caption">{a.interlock_log.length} events</span></div>
        {a.interlock_log.length ? a.interlock_log.map((i) => (
          <div key={i.id} className="row wrap" style={{ borderBottom: "1px solid var(--t10)", padding: "6px 0" }}>
            <Icon name={i.category === "interlock" ? "shield-lock-outline" : "shield-alert-outline"} color={i.category === "interlock" ? "var(--gps-red)" : "var(--gps-orange)"} />
            <b style={{ width: 70 }}>{i.rule_id}</b>
            <span className="grow">{i.action}<div className="caption">{i.equipment}</div></span>
            <span className="caption">{i.status} · {fmtTime(i.created_at)}</span>
          </div>
        )) : <div className="caption">No interlocks engaged in the last 24 hours.</div>}
      </div>
    </>
  );
}

function Weekly({ a }) {
  return (
    <>
      <div className="stats">
        <Stat label="L2/L3 Escalation Rate" value={a.escalation_rate_pct} unit="%" hint={`${a.sessions} sessions this week`} />
        <Stat label="Mean Time To Escalate" value={a.mtte_min != null ? fmtDuration(a.mtte_min) : null} hint="session start → expert dispatch" />
        <Stat label="Context Package Compile" value={a.payload_compile_ms != null ? Math.round(a.payload_compile_ms) : null} unit="ms" hint="SRS target < 30 s" />
        <Stat label="SOP Compliance Index" value={a.sop_compliance_pct} unit="%" hint="closed via structured CAPA workflow" />
      </div>
      <div className="grid-2">
        <div className="card">
          <div className="card-title">Sub-System Failure Distribution · Pareto</div>
          {a.failure_pareto.length ? (
            <HBars data={a.failure_pareto.map((p) => ({ label: p.subsystem, value: p.count }))}
                   extra={(d) => `cum. ${a.failure_pareto.find((p) => p.subsystem === d.label).cumulative_pct}%`} />
          ) : <div className="caption">No faults this week.</div>}
        </div>
        <div className="card">
          <div className="card-title">Daily Sessions · resolution path</div>
          <StackedBars data={a.daily.map((d) => ({
                         label: new Date(d.date).toLocaleDateString(undefined, { weekday: "short" }),
                         copilot: d.resolved_by_copilot, expert: d.escalated, other: Math.max(0, d.sessions - d.resolved_by_copilot - d.escalated),
                       }))}
                       series={[{ key: "copilot", label: "Resolved by SiteBrain", color: "#5fa414" },
                                { key: "expert", label: "Escalated to expert", color: "#3191ef" },
                                { key: "other", label: "Open / closed", color: "#b6b6b6" }]} />
        </div>
      </div>
    </>
  );
}

function Monthly({ a }) {
  const lastFcr = [...a.fcr_trend].reverse().find((m) => m.fcr_pct != null)?.fcr_pct;
  return (
    <>
      <div className="stats">
        <Stat label="Fleet Production Uptime" value={a.fleet_uptime_pct} unit="%" hint={`${a.fleet_uptime.reduce((s, u) => s + u.operational_hours, 0).toLocaleString()} operational hours · 30 d`} />
        <Stat label="Critical Incidents Avoided" value={a.critical_incidents_avoided} hint="interlocks that protected equipment · 30 d" />
        <Stat label="Particulate Ingress Events" value={a.particulate_ingress_events} hint="into gas compressors · 30 d" />
        <Stat label="First-Contact Resolution" value={lastFcr} unit="%" hint={`target > ${a.fcr_target_pct}%`} />
      </div>
      <div className="grid-2">
        <div className="card">
          <div className="card-title">First-Contact Resolution Trend</div>
          <LineChart data={a.fcr_trend.map((m) => ({ label: m.month, short: m.month.split(" ")[0], value: m.fcr_pct }))}
                     target={a.fcr_target_pct} fmt={(v) => `${Math.round(v)}%`} min={50} max={100} />
        </div>
        <div className="card">
          <div className="card-title">Knowledge Base Expansion · RCA packages indexed per month</div>
          <BarChart data={a.fcr_trend.map((m) => ({ label: m.month, short: m.month.split(" ")[0], value: m.kb_new }))} />
          <div className="caption">{a.kb_expansion.total_packages} packages · {a.kb_expansion.documents} documents ({a.kb_expansion.chunks} indexed passages)</div>
        </div>
        <div className="card">
          <div className="card-title">Production Uptime By Site · 30 d</div>
          <HBars data={a.fleet_uptime.map((u) => ({ label: u.name, value: u.uptime_pct }))} fmt={(v) => `${v}%`}
                 extra={(d) => `${a.fleet_uptime.find((u) => u.name === d.label).downtime_hours} h down`} />
        </div>
        <div className="card">
          <div className="card-title">Critical Incidents Avoided By Interlock</div>
          {a.avoided_by_rule.length ? <HBars data={a.avoided_by_rule.map((r) => ({ label: r.rule_id, value: r.count }))} color="#3191ef" />
            : <div className="caption">No protective trips this month.</div>}
        </div>
      </div>
    </>
  );
}
