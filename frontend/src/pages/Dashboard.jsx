import { useEffect } from "react";

export default function Dashboard({ state, onRefresh, goto }) {
  useEffect(() => {
    onRefresh();
  }, []);

  if (!state) {
    return <div className="card">Loading…</div>;
  }

  const steps = [
    {
      key: "newcycle",
      title: "1 · Start new month",
      desc: "Archive the last month, roll meters over, and set the billing month & date.",
      done: state.has_basic_info,
      badge: null,
    },
    {
      key: "meters",
      title: "2 · Enter meter readings",
      desc: "Type every room's water & electric values (or paste a CSV).",
      done: state.current_has_values,
      badge: state.current_rooms_count ? `${state.current_rooms_count} rooms` : null,
    },
    {
      key: "drc",
      title: "3 · Run DRC checks",
      desc: "Catch negative or over-500-unit readings before billing.",
      done: state.current_has_values && state.drc_issues === 0,
      badge: state.drc_issues > 0 ? `${state.drc_issues} issues` : null,
    },
    {
      key: "billing",
      title: "4 · Bill, upload & send",
      desc: "Generate the PDF, convert to JPEGs, upload to ImgBB, and send via LINE.",
      done: state.urls_uploaded,
      badge: state.uploaded_count ? `${state.uploaded_count} uploaded` : null,
    },
  ];

  return (
    <div className="dash">
      <div className="row between">
        <h2>Billing workflow</h2>
        <button className="ghost" onClick={onRefresh}>Refresh</button>
      </div>

      <div className="cards">
        {steps.map((s) => (
          <div className={`card step ${s.done ? "done" : ""}`} key={s.key}>
            <div className="step-top">
              <div className="step-title">
                <span className={`dot ${s.done ? "ok" : "todo"}`} />
                <strong>{s.title}</strong>
              </div>
              {s.badge && <span className="badge">{s.badge}</span>}
            </div>
            <p className="muted">{s.desc}</p>
            <button className="primary" onClick={() => goto(s.key)}>Open</button>
          </div>
        ))}
      </div>

      <div className="card stats">
        <div><span>Billing month</span><b>{state.billing_month || "—"}</b></div>
        <div><span>Bill date</span><b>{state.bill_date || "—"}</b></div>
        <div><span>JPEG files</span><b>{state.jpeg_count}</b></div>
        <div><span>Tenants registered</span><b>{state.tenant_line_id_count}</b></div>
        <div><span>Archives</span><b>{state.archives?.length ?? 0}</b></div>
      </div>
    </div>
  );
}
