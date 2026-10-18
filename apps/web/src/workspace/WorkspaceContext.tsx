import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type Workspace } from "../api/client";

type Ctx = { workspace: Workspace | null; workspaces: Workspace[]; select: (id: number) => void };
const WsCtx = createContext<Ctx>(null!);
export const useWorkspace = () => useContext(WsCtx);

const KEY = "ada.workspace";   // only a UI preference; the server still checks membership on every call

function readSaved(): number | null {
  try { return Number(localStorage.getItem(KEY)) || null; } catch { return null; }
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [id, setId] = useState<number | null>(readSaved);
  const [error, setError] = useState("");

  useEffect(() => {
    api.workspaces().then(setWorkspaces).catch((e) => setError((e as Error).message));
  }, []);

  const select = (next: number) => {
    setId(next);
    try { localStorage.setItem(KEY, String(next)); } catch { /* private mode: fine */ }
  };

  if (error) return <p className="center muted page-msg">Couldn't load your workspace: {error}</p>;
  if (!workspaces.length) return <p className="center muted page-msg">Loading…</p>;
  const workspace = workspaces.find((w) => w.id === id) ?? workspaces[0];

  return <WsCtx.Provider value={{ workspace, workspaces, select }}>{children}</WsCtx.Provider>;
}
