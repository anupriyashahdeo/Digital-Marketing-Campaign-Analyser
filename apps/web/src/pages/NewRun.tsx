import { Link, Navigate } from "react-router-dom";
import NewRunForm from "../features/runs/NewRunForm";
import { useWorkspace } from "../workspace/WorkspaceContext";

export default function NewRun() {
  const { workspace } = useWorkspace();
  if (workspace?.role === "viewer") return <Navigate to="/" replace />;
  return (
    <>
      <p><Link to="/">← Dashboard</Link></p>
      <section className="card narrow">
        <h1>New analysis</h1>
        <p className="muted">We'll find YouTube ads in this category and analyse each one.</p>
        <NewRunForm />
      </section>
    </>
  );
}
