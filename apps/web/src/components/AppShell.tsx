import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useWorkspace } from "../workspace/WorkspaceContext";

export default function AppShell() {
  const { user, logout } = useAuth();
  const { workspace, workspaces, select } = useWorkspace();

  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-left">
          <span className="brand">Ad Campaign Analyser</span>
          <nav aria-label="Main">
            <NavLink to="/" end>Dashboard</NavLink>
            <NavLink to="/runs">Analyses</NavLink>
            <NavLink to="/youtube">YouTube</NavLink>
          </nav>
        </div>
        <div className="topbar-right">
          {workspaces.length > 1 ? (
            <select aria-label="Workspace" value={workspace?.id}
              onChange={(e) => select(Number(e.target.value))}>
              {workspaces.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          ) : <span className="muted ws-name">{workspace?.name}</span>}
          <span className="muted user-email" title={user?.email}>{user?.email}</span>
          <button className="link" onClick={logout}>Sign out</button>
        </div>
      </header>
      <main className="page"><Outlet /></main>
    </div>
  );
}
