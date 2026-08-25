import { useState } from "react";
import { api } from "../api.js";

const METER_LABEL = { water: "น้ำ (water)", electric: "ไฟ (electric)" };

export default function Drc({ state, onRefresh, goto }) {
  const [issues, setIssues] = useState(null); // null = not run yet
  const [edits, setEdits] = useState({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const run = async () => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const res = await api.drcDetect();
      const list = res.issues || [];
      setIssues(list);
      const init = {};
      list.forEach((iss) => {
        const key = `${iss.unit_number}:${iss.meter_type}`;
        init[key] = {
          corrected_previous: String(iss.previous_value),
          corrected_current: String(iss.current_value),
        };
      });
      setEdits(init);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const setField = (key, field, value) => {
    setEdits((prev) => ({ ...prev, [key]: { ...prev[key], [field]: value } }));
  };

  const apply = async () => {
    setBusy(true);
    setError("");
    setMessage("");
    const fixes = (issues || []).map((iss) => {
      const e = edits[`${iss.unit_number}:${iss.meter_type}`] || {};
      return {
        unit_number: iss.unit_number,
        meter_type: iss.meter_type,
        corrected_previous: e.corrected_previous === "" ? null : Number(e.corrected_previous),
        corrected_current: e.corrected_current === "" ? null : Number(e.corrected_current),
      };
    });
    try {
      const res = await api.drcApply(fixes);
      setMessage(`${res.applied} value(s) updated.`);
      setIssues(res.issues || []);
      onRefresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const hasIssues = (issues || []).length > 0;

  return (
    <div className="page">
      <h2>Run DRC — check meter readings</h2>

      {issues === null ? (
        <div className="card">
          <p className="muted">Detect negative readings, values outside 0–9999, or usage over 500 units.</p>
          {!state?.current_has_values && (
            <p className="warn">⚠️ No readings saved yet — enter meter readings first.</p>
          )}
          <button className="primary" onClick={run} disabled={busy || !state?.current_has_values}>
            {busy ? "Checking…" : "Run DRC"}
          </button>
        </div>
      ) : hasIssues ? (
        <div className="card">
          <div className="row between">
            <strong>Found {issues.length} issue(s)</strong>
            <button className="ghost" onClick={run} disabled={busy}>Re-check</button>
          </div>
          <div className="issue-list">
            {issues.map((iss) => {
              const key = `${iss.unit_number}:${iss.meter_type}`;
              const e = edits[key] || {};
              return (
                <div className="issue" key={key}>
                  <div className="issue-head">
                    <span className="badge">{METER_LABEL[iss.meter_type]}</span>
                    <strong>{iss.unit_number}</strong>
                    <span className="issue-type">{iss.issue_type}</span>
                  </div>
                  <div className="issue-meta">
                    prev {iss.previous_value} → curr {iss.current_value}
                    {iss.usage !== null && ` · usage ${iss.usage}`}
                    {iss.rollover ? " · meter rolled over" : ""}
                  </div>
                  <div className="issue-fields">
                    <label>
                      Corrected previous
                      <input
                        className="num"
                        type="number"
                        min="0"
                        max="9999"
                        value={e.corrected_previous ?? ""}
                        onChange={(ev) => setField(key, "corrected_previous", ev.target.value)}
                      />
                    </label>
                    <label>
                      Corrected current
                      <input
                        className="num"
                        type="number"
                        min="0"
                        max="9999"
                        value={e.corrected_current ?? ""}
                        onChange={(ev) => setField(key, "corrected_current", ev.target.value)}
                      />
                    </label>
                  </div>
                </div>
              );
            })}
          </div>
          {message && <div className="success">{message}</div>}
          {error && <div className="error">{error}</div>}
          <div className="row actions">
            <button className="primary" onClick={apply} disabled={busy}>
              {busy ? "Applying…" : "Apply fixes"}
            </button>
          </div>
        </div>
      ) : (
        <div className="card">
          <p className="success">✅ No issues found — readings look good.</p>
          <div className="row actions">
            <button className="primary" onClick={() => goto("billing")}>Continue to billing</button>
            <button className="ghost" onClick={run}>Re-check</button>
          </div>
        </div>
      )}
    </div>
  );
}
