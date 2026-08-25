import { useEffect, useState } from "react";
import { api, clearToken, getToken } from "./api.js";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import NewCycle from "./pages/NewCycle.jsx";
import Meters from "./pages/Meters.jsx";
import Drc from "./pages/Drc.jsx";
import Billing from "./pages/Billing.jsx";

const PAGES = [
  { key: "dashboard", label: "Dashboard", component: Dashboard },
  { key: "newcycle", label: "New Month", component: NewCycle },
  { key: "meters", label: "Meter Readings", component: Meters },
  { key: "drc", label: "Run DRC", component: Drc },
  { key: "billing", label: "Bill & Deliver", component: Billing },
];

export default function App() {
  const [user, setUser] = useState(undefined); // undefined = loading
  const [page, setPage] = useState("dashboard");
  const [state, setState] = useState(null);

  useEffect(() => {
    let cancelled = false;
    if (!getToken()) {
      setUser(null);
      return;
    }
    api
      .me()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      });

    const onLogout = () => setUser(null);
    window.addEventListener("auth:logout", onLogout);
    return () => {
      cancelled = true;
      window.removeEventListener("auth:logout", onLogout);
    };
  }, []);

  const refreshState = async () => {
    try {
      setState(await api.state());
    } catch {
      setState(null);
    }
  };

  const handleLogin = (username) => {
    setUser({ username });
    setPage("dashboard");
  };

  const handleLogout = () => {
    clearToken();
    setUser(null);
  };

  const goto = (key) => {
    setPage(key);
    refreshState();
  };

  if (user === undefined) {
    return <div className="center-page">Loading…</div>;
  }

  if (user === null) {
    return <Login onLogin={handleLogin} />;
  }

  const active = PAGES.find((p) => p.key === page) || PAGES[0];
  const Page = active.component;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <strong>{state?.apartment_name || "Apartment Billing"}</strong>
          {state?.billing_month && <span className="month">Month {state.billing_month}</span>}
        </div>
        <nav>
          {PAGES.map((p) => (
            <button
              key={p.key}
              className={`nav-btn ${p.key === page ? "active" : ""}`}
              onClick={() => goto(p.key)}
            >
              {p.label}
            </button>
          ))}
        </nav>
        <div className="userbox">
          <span>{user.username}</span>
          <button className="ghost" onClick={handleLogout}>Log out</button>
        </div>
      </header>

      <main className="content">
        <Page state={state} onRefresh={refreshState} goto={goto} />
      </main>
    </div>
  );
}
