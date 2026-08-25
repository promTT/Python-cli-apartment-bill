import { useState } from "react";
import { api } from "../api.js";

function savePdf(blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "apartment_bill.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function Billing({ state, onRefresh, goto }) {
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [showSendDetail, setShowSendDetail] = useState(false);

  const run = async (step, fn) => {
    setBusy(step);
    setError("");
    setResult(null);
    try {
      const data = await fn();
      setResult({ step, data });
      onRefresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  };

  const download = async () => {
    setError("");
    try {
      const blob = await api.downloadPdf();
      savePdf(blob);
    } catch (err) {
      setError(err.message);
    }
  };

  if (!state) {
    return <div className="card">Loading…</div>;
  }

  const steps = [
    {
      key: "generate",
      title: "Generate bill PDF",
      desc: "Compute usage & charges, save to MongoDB, render the invoice PDF.",
      done: state.bills_generated,
      busy: busy === "generate",
      action: () => run("generate", api.generateBill),
      extra: state.bills_generated ? (
        <button className="ghost" onClick={download}>Download PDF</button>
      ) : null,
    },
    {
      key: "convert",
      title: "Convert PDF to JPEG",
      desc: "Split the master PDF into one image per room.",
      done: state.jpegs_exist,
      busy: busy === "convert",
      action: () => run("convert", api.convertPdf),
      extra: state.jpegs_exist ? <span className="badge">{state.jpeg_count} images</span> : null,
    },
    {
      key: "upload",
      title: "Upload to ImgBB",
      desc: "Upload every room's JPEG and keep the public URLs (auto-delete 90 days).",
      done: state.urls_uploaded,
      busy: busy === "upload",
      action: () => run("upload", api.upload),
      extra: state.urls_uploaded ? <span className="badge">{state.uploaded_count} uploaded</span> : null,
    },
    {
      key: "send",
      title: "Send via LINE",
      desc: "Push each bill to the room's tenant; rooms without a LINE ID go to the admin.",
      done: false,
      busy: busy === "send",
      action: () => run("send", api.send),
      extra: null,
    },
  ];

  const sendData = result?.step === "send" ? result.data : null;

  return (
    <div className="page">
      <h2>Bill, upload & deliver</h2>

      {result && (
        <div className="card success result-box">
          <strong>
            {result.step === "generate" && `PDF generated for ${result.data.rooms} rooms ✓`}
            {result.step === "convert" && `${result.data.count} JPEGs created ✓`}
            {result.step === "upload" && `Uploaded ${result.data.uploaded}/${result.data.total} images ✓`}
            {result.step === "send" && `Sent ${result.data.sent}/${result.data.total} bills via LINE ✓`}
          </strong>
        </div>
      )}
      {error && <div className="error">{error}</div>}

      <div className="cards stack">
        {steps.map((s) => (
          <div className={`card step ${s.done ? "done" : ""}`} key={s.key}>
            <div className="step-top">
              <div className="step-title">
                <span className={`dot ${s.done ? "ok" : "todo"}`} />
                <strong>{s.title}</strong>
              </div>
              {s.extra}
            </div>
            <p className="muted">{s.desc}</p>
            <div className="row">
              <button className="primary" onClick={s.action} disabled={s.busy}>
                {s.busy ? "Working…" : s.done ? "Run again" : "Run"}
              </button>
              {s.extra}
            </div>
          </div>
        ))}
      </div>

      {sendData && (
        <div className="card">
          <div className="row between">
            <button className="ghost" onClick={() => setShowSendDetail((v) => !v)}>
              {showSendDetail ? "Hide" : "Show"} delivery detail
            </button>
          </div>
          {showSendDetail && (
            <table className="compact">
              <thead>
                <tr><th>Room</th><th>Sent to</th><th>Status</th></tr>
              </thead>
              <tbody>
                {Object.entries(sendData.results || {}).map(([room, r]) => (
                  <tr key={room}>
                    <td>{room}</td>
                    <td className="muted">{r.to || "—"}</td>
                    <td>{r.sent ? "✅" : "❌"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
