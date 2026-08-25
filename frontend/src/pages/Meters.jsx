import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";

export default function Meters({ state, onRefresh, goto }) {
  const [meters, setMeters] = useState(null);
  const [rows, setRows] = useState({});
  const [csvText, setCsvText] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const rooms = useMemo(() => state?.rooms || [], [state]);

  useEffect(() => {
    let cancelled = false;
    api
      .meters()
      .then((m) => {
        if (cancelled) return;
        setMeters(m);
        const init = {};
        for (const room of rooms) {
          const cur = m.current[room] || {};
          init[room] = {
            water: cur.water !== undefined ? String(cur.water) : "",
            electric: cur.electric !== undefined ? String(cur.electric) : "",
          };
        }
        setRows(init);
      })
      .catch((e) => setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [rooms.join(",")]);

  const setCell = (room, field, value) => {
    setRows((prev) => ({ ...prev, [room]: { ...prev[room], [field]: value } }));
  };

  const importCsv = () => {
    const next = { ...rows };
    let count = 0;
    csvText.split(/\r?\n/).forEach((line) => {
      line = line.trim();
      if (!line) return;
      const parts = line.split(/[,;\t]+/).map((p) => p.trim());
      if (parts.length < 3) return;
      const [room, water, electric] = parts;
      if (next[room]) {
        next[room] = { water, electric };
        count += 1;
      }
    });
    setRows(next);
    setMessage(count ? `Imported ${count} room(s) from CSV.` : "No rooms matched the table.");
  };

  const save = async () => {
    setBusy(true);
    setError("");
    setMessage("");
    const payload = {};
    for (const room of rooms) {
      const w = rows[room]?.water ?? "";
      const e = rows[room]?.electric ?? "";
      payload[room] = {
        water: w === "" ? 0 : Number(w),
        electric: e === "" ? 0 : Number(e),
      };
    }
    try {
      await api.saveMeters(payload);
      onRefresh();
      setMessage("Readings saved ✓");
      goto("drc");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  if (!meters) {
    return <div className="card">Loading readings…</div>;
  }

  return (
    <div className="page">
      <h2>Enter meter readings — {state?.billing_month || ""}</h2>

      <div className="card">
        <p className="muted">
          Fill in water &amp; electric for each room (0–9999). Previous month is shown for
          reference only.
        </p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Room</th>
                <th>Water</th>
                <th>Electric</th>
                <th>Prev water</th>
                <th>Prev elec</th>
              </tr>
            </thead>
            <tbody>
              {rooms.map((room) => {
                const prev = meters.previous[room] || {};
                return (
                  <tr key={room}>
                    <td className="room">{room}</td>
                    <td>
                      <input
                        className="num"
                        type="number"
                        min="0"
                        max="9999"
                        inputMode="numeric"
                        value={rows[room]?.water ?? ""}
                        onChange={(e) => setCell(room, "water", e.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        className="num"
                        type="number"
                        min="0"
                        max="9999"
                        inputMode="numeric"
                        value={rows[room]?.electric ?? ""}
                        onChange={(e) => setCell(room, "electric", e.target.value)}
                      />
                    </td>
                    <td className="prev">{prev.water ?? ""}</td>
                    <td className="prev">{prev.electric ?? ""}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3>Or paste a CSV</h3>
        <p className="muted">One row per room: <code>room,water,electric</code> (comma, tab or semicolon).</p>
        <textarea
          rows="5"
          placeholder={"101/1,354,8698\n102/1,2047,4510"}
          value={csvText}
          onChange={(e) => setCsvText(e.target.value)}
        />
        <div className="row">
          <button className="ghost" onClick={importCsv}>Import into table</button>
        </div>
      </div>

      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="row actions">
        <button className="primary" onClick={save} disabled={busy}>
          {busy ? "Saving…" : "Save readings & continue to DRC"}
        </button>
      </div>
    </div>
  );
}
