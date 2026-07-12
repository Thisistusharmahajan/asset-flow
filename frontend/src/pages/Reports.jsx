import { useEffect, useState } from "react";
import { api } from "../api";
import Sidebar from "../components/Sidebar";
import "./Reports.css";

function BarChart({ data }) {
  if (!data || data.length === 0) return <p className="chart-empty">No data yet</p>;
  const max = Math.max(...data.map((d) => d.count), 1);
  return (
    <svg viewBox="0 0 240 110" className="chart-svg" preserveAspectRatio="none">
      {data.map((d, i) => {
        const barWidth = 240 / data.length;
        const h = (d.count / max) * 90;
        return (
          <g key={d.department}>
            <rect
              x={i * barWidth + barWidth * 0.2}
              y={100 - h}
              width={barWidth * 0.6}
              height={h}
              rx="2"
              className="chart-bar"
            />
            <title>{`${d.department}: ${d.count}`}</title>
          </g>
        );
      })}
    </svg>
  );
}

function LineChart({ data }) {
  if (!data || data.length === 0) return <p className="chart-empty">No data yet</p>;
  const max = Math.max(...data.map((d) => d.count), 1);
  const points = data.map((d, i) => {
    const x = (i / (data.length - 1 || 1)) * 230 + 5;
    const y = 100 - (d.count / max) * 85;
    return `${x},${y}`;
  });
  return (
    <svg viewBox="0 0 240 110" className="chart-svg" preserveAspectRatio="none">
      <polyline points={points.join(" ")} className="chart-line" fill="none" />
      {points.map((p, i) => {
        const [x, y] = p.split(",");
        return <circle key={i} cx={x} cy={y} r="2.5" className="chart-dot" />;
      })}
    </svg>
  );
}

export default function Reports() {
  const [byDept, setByDept] = useState(null);
  const [maintFreq, setMaintFreq] = useState(null);
  const [mostUsed, setMostUsed] = useState(null);
  const [idle, setIdle] = useState(null);
  const [due, setDue] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api.reportUtilizationByDepartment(),
      api.reportMaintenanceFrequency(),
      api.reportMostUsed({ limit: 3 }),
      api.reportIdle({ limit: 3 }),
      api.reportMaintenanceDue(),
    ])
      .then(([dept, freq, used, idleList, dueList]) => {
        setByDept(dept);
        setMaintFreq(freq);
        setMostUsed(used);
        setIdle(idleList);
        setDue(dueList);
      })
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="shell">
      <Sidebar active="Reports" />
      <main className="content">
        <header className="content-header">
          <h1>Reports &amp; Analytics</h1>
        </header>

        {error && <div className="banner banner-error">{error}</div>}

        <div className="chart-row">
          <div className="chart-card">
            <div className="chart-card-title">Utilization by department</div>
            <BarChart data={byDept} />
          </div>
          <div className="chart-card">
            <div className="chart-card-title">Maintenance frequency</div>
            <LineChart data={maintFreq} />
          </div>
        </div>

        <div className="list-row">
          <div className="list-block">
            <h2>Most used assets</h2>
            {mostUsed === null ? (
              <p className="empty-state">Loading…</p>
            ) : mostUsed.length === 0 ? (
              <p className="empty-state">No usage recorded yet.</p>
            ) : (
              <ul className="report-list">
                {mostUsed.map((m) => (
                  <li key={m.asset_tag}>
                    <span className="asset-tag">{m.asset_tag}</span> {m.asset_name}:{" "}
                    <strong>{m.count}</strong> {m.unit}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="list-block">
            <h2>Idle assets</h2>
            {idle === null ? (
              <p className="empty-state">Loading…</p>
            ) : idle.length === 0 ? (
              <p className="empty-state">Nothing idle right now.</p>
            ) : (
              <ul className="report-list">
                {idle.map((a) => (
                  <li key={a.asset_tag}>
                    <span className="asset-tag">{a.asset_tag}</span> {a.asset_name}: unused{" "}
                    <strong>{a.days_idle}+</strong> days
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="list-block full-width">
          <h2>Assets due for maintenance / nearing retirement</h2>
          {due === null ? (
            <p className="empty-state">Loading…</p>
          ) : due.length === 0 ? (
            <p className="empty-state">Nothing flagged right now.</p>
          ) : (
            <ul className="report-list muted-list">
              {due.map((a, i) => (
                <li key={a.asset_tag + i}>
                  <span className="asset-tag">{a.asset_tag}</span> {a.asset_name}: {a.reason}
                </li>
              ))}
            </ul>
          )}
        </div>

        <a
          className="btn-export"
          href={api.reportExportUrl()}
          onClick={(e) => {
            // fetch with auth header instead of a plain navigation, since
            // the export endpoint requires a JWT
            e.preventDefault();
            fetch(api.reportExportUrl(), {
              headers: {
                Authorization: `Bearer ${localStorage.getItem("assetflow_token")}`,
              },
            })
              .then((res) => res.blob())
              .then((blob) => {
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "assetflow-report.csv";
                a.click();
                URL.revokeObjectURL(url);
              });
          }}
        >
          Export report
        </a>
      </main>
    </div>
  );
}
