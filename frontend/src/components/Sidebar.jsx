import { useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import "./Sidebar.css";

const NAV_ITEMS = [
  { label: "Dashboard", path: "/dashboard" },
  { label: "Organization setup", path: "/organization-setup" },
  { label: "Assets", path: "/assets" },
  { label: "Allocation & Transfer", path: null },
  { label: "Resource Booking", path: null },
  { label: "Maintenance", path: null },
  { label: "Audit", path: null },
  { label: "Reports", path: null },
  { label: "Notifications", path: null },
];

export default function Sidebar({ active }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">AssetFlow</div>
      <nav className="sidebar-nav">
        {NAV_ITEMS.map((item) => {
          const isActive = item.label === active;
          const disabled = !item.path;
          return (
            <a
              key={item.label}
              href="#"
              className={
                "sidebar-link" +
                (isActive ? " active" : "") +
                (disabled ? " disabled" : "")
              }
              onClick={(e) => {
                e.preventDefault();
                if (item.path) navigate(item.path);
              }}
            >
              {item.label}
            </a>
          );
        })}
      </nav>
      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-avatar">{user?.name?.[0] ?? "?"}</div>
          <div>
            <div className="sidebar-user-name">{user?.name ?? "…"}</div>
            <div className="sidebar-user-role">{user?.role ?? ""}</div>
          </div>
        </div>
        <button className="sidebar-logout" onClick={handleLogout}>
          Log out
        </button>
      </div>
    </aside>
  );
}
