export default function Sidebar({ activeView, onChangeView, online }) {
  const views = [
    { key: "chat", icon: "💬", label: "Chat" },
    { key: "memory", icon: "🧠", label: "Memory" },
    { key: "search", icon: "🔍", label: "Search" },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="logo-icon">🧠</div>
          <h1>AI Person</h1>
        </div>
        <div className="sidebar-version">v0.3.0 - Bo Nao Thu 2</div>
      </div>

      <nav className="sidebar-nav">
        {views.map((v) => (
          <button
            key={v.key}
            className={`nav-item ${activeView === v.key ? "active" : ""}`}
            onClick={() => onChangeView(v.key)}
          >
            <span className="icon">{v.icon}</span>
            <span>{v.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className={`status-dot ${online ? "" : "offline"}`} />
        <span>{online ? "API Connected" : "Disconnected"}</span>
      </div>
    </aside>
  );
}
