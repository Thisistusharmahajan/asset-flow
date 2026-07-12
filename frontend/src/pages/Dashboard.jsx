import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import Sidebar from "../components/Sidebar";
import "./Dashboard.css";

const KPI_META = [
  { key: "assets_available", label: "Available" },
  { key: "assets_allocated", label: "Allocated" },
  { key: "maintenance_today", label: "Maintenance today" },
  { key: "active_bookings", label: "Active bookings" },
  { key: "pending_transfers", label: "Pending transfers" },
  { key: "upcoming_returns", label: "Upcoming returns" },
];

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.max(1, Math.round(diffMs / 60000));
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [kpis, setKpis] = useState(null);
  const [overdue, setOverdue] = useState([]);
  const [activity, setActivity] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.kpis(), api.overdue(), api.activity()])
      .then(([k, o, a]) => {
        setKpis(k);
        setOverdue(o);
        setActivity(a);
      })
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="shell">
      <Sidebar active="Dashboard" />

      <main className="content">
        <header className="content-header">
          <h1>Today's overview</h1>
          <span className="content-date">
            {new Date().toLocaleDateString(undefined, {
              weekday: "long", month: "long", day: "numeric",
            })}
          </span>
        </header>

        {error && <div className="banner banner-error">{error}</div>}

        <section className="kpi-grid">
          {KPI_META.map(({ key, label }) => (
            <div className="kpi-card" key={key}>
              <span className="kpi-value">
                {kpis ? kpis[key] : "–"}
              </span>
              <span className="kpi-label">{label}</span>
            </div>
          ))}
        </section>

        {overdue.length > 0 && (
          <div className="banner banner-overdue">
            <strong>{overdue.length}</strong>
            {overdue.length === 1 ? " asset is" : " assets are"} overdue for
            return — flagged for follow-up
          </div>
        )}

        <section className="quick-actions">
          <button className="action-primary" onClick={() => navigate("/assets")}>
            + Register asset
          </button>
          <button className="action-secondary">Book resource</button>
          <button className="action-secondary">Raise maintenance request</button>
        </section>

        <section className="panels">
          <div className="panel">
            <h2>Recent activity</h2>
            {activity.length === 0 && (
              <p className="empty-state">Nothing to show yet — activity will appear here.</p>
            )}
            <ul className="activity-list">
              {activity.map((a) => (
                <li key={a.id}>
                  <span className="activity-dot" data-type={a.type} />
                  <span className="activity-message">{a.message}</span>
                  <span className="activity-time">{timeAgo(a.created_at)}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="panel">
            <h2>Overdue returns</h2>
            {overdue.length === 0 && (
              <p className="empty-state">No overdue returns right now.</p>
            )}
            <ul className="overdue-list">
              {overdue.map((o) => (
                <li key={o.id}>
                  <span className="asset-tag">{o.asset_tag}</span>
                  <span className="overdue-name">{o.asset_name}</span>
                  <span className="overdue-holder">{o.holder}</span>
                  <span className="overdue-days">{o.days_overdue}d overdue</span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </main>
    </div>
  );
}
