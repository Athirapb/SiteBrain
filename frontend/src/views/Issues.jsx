import { useMemo, useState } from "react";
import { api } from "../api";
import { Empty, Icon, PillTabs, Spinner, URGENCY_BG, fmtDate, useAsync, usePoll } from "../components/ui";

const OPEN = new Set(["active", "escalated"]);
// a reporter's issue in plain words
const issueStatus = (r) =>
  r.status === "escalated" && r.expert_replied ? ["Expert replied", "var(--gps-info)", "message-reply-text-outline"]
    : r.status === "escalated" ? ["With expert", "var(--gps-info)", "account-clock-outline"]
    : r.status === "active" ? ["In progress", "var(--gps-orange-dark)", "progress-wrench"]
    : r.status === "resolved" ? ["Resolved", "var(--gps-green-mid)", "check-circle-outline"]
    : ["Closed", "var(--t50)", "archive-check-outline"];
// an escalation as the expert sees it
const escStatus = (e) =>
  e.status === "Resolved" ? ["Resolved", "var(--gps-green-mid)", "check-circle-outline"]
    : !e.claimed_by ? ["New", "var(--gps-error)", "bell-ring-outline"]
    : e.awaiting_expert ? ["Waiting for your reply", "var(--gps-orange-dark)", "message-alert-outline"]
    : ["Answered", "var(--gps-info)", "message-check-outline"];

const COPY = {
  mine: ["My Past Issues", "Issues you reported. Open ones are still being worked on."],
  queue: ["Issues Queue", "Issues the plant teams escalated. Answer when you can: the reporter is notified of your reply."],
  resolved: ["My Past Resolutions", "Issues you answered."],
};

export default function Issues({ mode, nav }) {
  const [scope, setScope] = useState("mine"); // reporter: mine | plant
  const [tab, setTab] = useState("open");
  const [query, setQuery] = useState("");
  const url = mode === "mine" ? `/api/sessions?limit=300${scope === "mine" ? "&mine=true" : ""}`
    : `/api/escalations?scope=fleet&limit=300${mode === "queue" ? "&status=open" : "&mine=true"}`;
  const data = useAsync(() => api.get(url), [url]);
  usePoll(() => data.reload(), 15000, [url]);
  const rows = mode === "mine" ? data.data || [] : data.data?.items || [];

  const isOpen = (r) => (mode === "mine" ? OPEN.has(r.status) : r.status !== "Resolved");
  const listed = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((r) => mode === "queue" || (tab === "open" ? isOpen(r) : !isOpen(r)))
      .filter((r) => !q || [r.id, r.ticket, r.symptom, r.summary, r.eq_name, r.unit_name, r.project, r.reported_by, r.root_cause]
        .join(" ").toLowerCase().includes(q));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, tab, query, mode]);
  const nOpen = rows.filter(isOpen).length;
  const [title, sub] = COPY[mode];

  return (
    <div className="page narrow">
      <div>
        <div className="page-title">{title}</div>
        <div className="page-sub">{sub}</div>
      </div>
      <div className="row wrap" style={{ gap: 12 }}>
        {mode !== "queue" && (
          <PillTabs value={tab} onChange={setTab} options={[["open", `Open · ${nOpen}`], ["closed", `Closed · ${rows.length - nOpen}`]]} />
        )}
        {mode === "mine" && (
          <PillTabs value={scope} onChange={setScope} options={[["mine", "Reported by me"], ["plant", "Whole plant"]]} />
        )}
        <div className="search grow" style={{ minWidth: 200 }}>
          <Icon name="magnify" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find an issue" aria-label="Find an issue" />
        </div>
      </div>

      {!data.data ? <Spinner /> : (
        <div className="hist-list">
          {listed.map((r) => {
            const [label, color, icon] = mode === "mine" ? issueStatus(r) : escStatus(r);
            const sid = mode === "mine" ? r.id : r.session_id;
            const issue = r.symptom || r.summary || "Reported issue";
            const flagged = mode === "mine" ? r.expert_replied && r.status === "escalated" : r.status !== "Resolved" && (!r.claimed_by || r.awaiting_expert);
            return (
              <button key={r.ticket || r.id} className={`hist-card ${flagged ? "flagged" : ""}`} style={{ "--accent": color }}
                      disabled={!sid} onClick={() => nav("issue", { sessionId: sid, from: mode === "mine" ? "issues" : mode === "queue" ? "queue" : "resolutions" })}>
                <div className="hist-top">
                  <span className="hist-title">{mode !== "mine" && !r.area_level && r.eq_name ? `${r.eq_name} — ${issue}` : issue}</span>
                  <span className="hist-status" style={{ color }}><Icon name={icon} size={16} />{label}</span>
                </div>
                <div className="hist-meta">
                  <span className="hist-chip">
                    <Icon name={r.area_level ? "map-marker-question-outline" : "cog-outline"} size={14} />
                    <b>{r.area_level ? "Equipment not identified" : r.eq_name}</b>· {r.unit_name}
                  </span>
                  {mode !== "mine" && r.project && <span className="hist-chip"><Icon name="factory" size={14} /><b>{r.project}</b></span>}
                  {(r.severity || r.urgency) && (
                    <span className="tag" style={{ background: URGENCY_BG[r.severity || r.urgency], color: "#fff", alignSelf: "center" }}>{r.severity || r.urgency}</span>
                  )}
                  <span className="hist-chip"><Icon name="calendar-outline" size={14} />{mode === "mine" ? fmtDate(r.created_at) : r.age}</span>
                  {r.reported_by && (mode !== "mine" || scope === "plant") && (
                    <span className="hist-chip"><Icon name="account-outline" size={14} />{r.reported_by}</span>
                  )}
                </div>
                {r.root_cause && !isOpen(r) && (
                  <div className="hist-cause"><span className="overline">Cause</span><span>{r.root_cause}</span></div>
                )}
              </button>
            );
          })}
          {!listed.length && (
            <div className="card">
              <Empty icon={mode === "queue" ? "inbox-outline" : "clipboard-check-outline"}
                     title={query ? "Nothing matches" : mode === "queue" ? "No issues waiting" : tab === "open" ? "No open issues" : "Nothing here yet"}>
                {mode === "queue" ? "When a plant team escalates an issue, it shows up here and you get an email."
                  : mode === "mine" && !query ? "Issues you report show up here." : ""}
              </Empty>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
