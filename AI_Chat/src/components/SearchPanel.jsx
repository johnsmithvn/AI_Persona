import { useState } from "react";
import { searchMemories } from "../api/client";

const CONTENT_TYPES = [
  { value: "", label: "Tat ca" },
  { value: "note", label: "Note" },
  { value: "conversation", label: "Conversation" },
  { value: "reflection", label: "Reflection" },
  { value: "idea", label: "Idea" },
  { value: "article", label: "Article" },
  { value: "log", label: "Log" },
];

export default function SearchPanel() {
  const [query, setQuery] = useState("");
  const [contentType, setContentType] = useState("");
  const [threshold, setThreshold] = useState(0.45);
  const [limit, setLimit] = useState(10);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const res = await searchMemories({
        query,
        content_type: contentType || undefined,
        threshold,
        limit,
      });
      setResults(res);
    } catch (err) {
      setError(err.message);
      setResults(null);
    }
    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Semantic Search</h2>
        <p>Tim kiem memory bang ngon ngu tu nhien</p>
      </div>

      <div className="form-card">
        <div className="form-group">
          <label>Query</label>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Toi da nghien cuu gi ve AI?"
          />
        </div>

        <div style={{ display: "flex", gap: 12 }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Content Type</label>
            <select value={contentType} onChange={(e) => setContentType(e.target.value)}>
              {CONTENT_TYPES.map((ct) => (
                <option key={ct.value} value={ct.value}>{ct.label}</option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ width: 100 }}>
            <label>Threshold</label>
            <input
              type="number"
              min="0"
              max="1"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
            />
          </div>

          <div className="form-group" style={{ width: 80 }}>
            <label>Limit</label>
            <input
              type="number"
              min="1"
              max="100"
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value))}
            />
          </div>
        </div>

        <button className="btn-primary" onClick={handleSearch} disabled={loading || !query.trim()}>
          {loading ? "Dang tim..." : "Search"}
        </button>
      </div>

      {error && <div className="alert error">{error}</div>}

      {results && (
        <>
          <div style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginBottom: 12 }}>
            Tim thay <strong style={{ color: "var(--accent)" }}>{results.total}</strong> ket qua
            cho "{results.query}"
          </div>

          <div className="search-results">
            {results.results.map((r) => (
              <div key={r.id} className="result-card">
                <div className="result-header">
                  <span className="result-type">{r.content_type}</span>
                  <span className="result-score">
                    sim: {r.similarity?.toFixed(3)} | score: {r.final_score?.toFixed(3)}
                  </span>
                </div>
                <div className="result-text">{r.raw_text}</div>
                <div className="result-footer">
                  <span>ID {r.id.slice(0, 8)}...</span>
                  <span>Date {new Date(r.created_at).toLocaleDateString()}</span>
                  {r.importance_score != null && <span>Score {r.importance_score}</span>}
                  {r.metadata?.tags && <span>Tags {r.metadata.tags.join(", ")}</span>}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {results && results.total === 0 && (
        <div className="chat-empty" style={{ padding: 40 }}>
          <p>Khong tim thay memory nao phu hop</p>
        </div>
      )}
    </div>
  );
}
