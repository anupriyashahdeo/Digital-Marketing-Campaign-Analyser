import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api/client";
import { useWorkspace } from "../../workspace/WorkspaceContext";

// Mirrors the server rules in api/schemas (the server is still the one that enforces them).
const MAX_KEYWORDS = 10, MAX_KEYWORD_LEN = 60;

export default function NewRunForm({ submitLabel = "Start analysis" }: { submitLabel?: string }) {
  const { workspace } = useWorkspace();
  const nav = useNavigate();
  const [category, setCategory] = useState("");
  const [keywords, setKeywords] = useState("");
  const [language, setLanguage] = useState("en");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const kws = keywords.split(",").map((k) => k.trim()).filter(Boolean);
    if (category.trim().length < 2) return setError("Enter a category of at least 2 characters.");
    if (kws.length > MAX_KEYWORDS) return setError(`Use at most ${MAX_KEYWORDS} brands or keywords.`);
    if (kws.some((k) => k.length > MAX_KEYWORD_LEN)) return setError(`Each keyword must be at most ${MAX_KEYWORD_LEN} characters.`);
    setBusy(true);
    try {
      const run = await api.createRun(workspace!.id, { category: category.trim(), keywords: kws, language });
      nav(`/runs/${run.id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="run-form">
      <div className="field">
        <label htmlFor="category">Category</label>
        <input id="category" value={category} maxLength={120} required
          placeholder="e.g. running shoes" onChange={(e) => setCategory(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="keywords">Brands or keywords <span className="muted">(optional, comma-separated)</span></label>
        <input id="keywords" value={keywords} placeholder="e.g. Nike, Adidas, Puma"
          onChange={(e) => setKeywords(e.target.value)} />
      </div>
      <div className="field-row">
        <div className="field">
          <label htmlFor="language">Ad language</label>
          <select id="language" value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="en">English</option>
            <option value="hi">Hindi</option>
          </select>
        </div>
        <div className="field">
          <label>Region</label>
          <div className="static-field">{workspace?.region === "IN" ? "India (IN)" : workspace?.region}</div>
        </div>
      </div>
      {error && <div className="alert error" role="alert">{error}</div>}
      <button className="primary" disabled={busy}>{busy ? "Starting…" : submitLabel}</button>
    </form>
  );
}
