import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import Sidebar from "../components/Sidebar";
import "./Notifications.css";

const TABS = [
  { key: "all", label: "All" },
  { key: "alerts", label: "Alerts" },
  { key: "approvals", label: "Approvals" },
  { key: "bookings", label: "Bookings" },
];

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.max(1, Math.round(diffMs / 60000));
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

export default function Notifications() {
  const [tab, setTab] = useState("all");
  const [notifications, setNotifications] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback((category) => {
    setError("");
    api
      .notifications({ category })
      .then(setNotifications)
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    load(tab);
  }, [tab, load]);

  async function handleMarkRead(id) {
    try {
      await api.markNotificationRead(id);
      load(tab);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="shell">
      <Sidebar active="Notifications" />
      <main className="content">
        <header className="content-header">
          <h1>Activity Logs &amp; Notifications</h1>
        </header>

        {error && <div className="banner banner-error">{error}</div>}

        <div className="tab-row">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={"tab-chip" + (tab === t.key ? " active" : "")}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="notif-panel">
          {notifications === null ? (
            <p className="empty-state">Loading…</p>
          ) : notifications.length === 0 ? (
            <p className="empty-state">Nothing here yet.</p>
          ) : (
            <ul className="notif-list">
              {notifications.map((n) => (
                <li
                  key={n.id}
                  className={n.is_read ? "read" : "unread"}
                  onClick={() => !n.is_read && handleMarkRead(n.id)}
                >
                  <span className={"notif-dot cat-" + n.category} />
                  <span className="notif-message">{n.message}</span>
                  <span className="notif-time">{timeAgo(n.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
