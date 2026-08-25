import { useState } from "react";
import { api } from "../api.js";

function nextMonthBE() {
  const now = new Date();
  const m = now.getMonth() + 1;
  const y = now.getFullYear() + 543;
  const nm = m === 12 ? 1 : m + 1;
  const ny = m === 12 ? y + 1 : y;
  return `${String(nm).padStart(2, "0")}/${ny}`;
}

function todayBE() {
  const now = new Date();
  const y = now.getFullYear() + 543;
  return `${String(now.getDate()).padStart(2, "0")}/${String(now.getMonth() + 1).padStart(2, "0")}/${y}`;
}

export default function NewCycle({ state, onRefresh, goto }) {
  const [month, setMonth] = useState(nextMonthBE());
  const [date, setDate] = useState(todayBE());
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      await api.newCycle(month, date);
      onRefresh();
      setConfirm(false);
      goto("meters");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <h2>Start a new billing cycle</h2>
      <div className="card form">
        <p className="warn">
          ⚠️ This archives the current month ({state?.billing_month || "—"}) into MongoDB,
          rolls the meters over, and clears the current readings so you can enter the
          new month's values.
        </p>
        <label>
          Billing month (MM/YYYY, Thai era)
          <input value={month} onChange={(e) => setMonth(e.target.value)} placeholder="08/2569" />
        </label>
        <label>
          Bill date (DD/MM/YYYY, Thai era)
          <input value={date} onChange={(e) => setDate(e.target.value)} placeholder="25/08/2569" />
        </label>

        {error && <div className="error">{error}</div>}

        {!confirm ? (
          <button className="danger" disabled={busy} onClick={() => setConfirm(true)}>
            Start new month…
          </button>
        ) : (
          <div className="row">
            <button className="danger" disabled={busy} onClick={submit}>
              {busy ? "Working…" : "Yes, archive & start"}
            </button>
            <button className="ghost" disabled={busy} onClick={() => setConfirm(false)}>
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
