import { useState } from "react";
import { saveMemory, getMemory } from "../api/client";

const CONTENT_TYPES = [
  { value: "note", label: "Note — Ghi chú chung" },
  { value: "conversation", label: "Conversation — Chat, đối thoại" },
  { value: "reflection", label: "Reflection — Quan điểm cá nhân" },
  { value: "idea", label: "Idea — Ý tưởng" },
  { value: "article", label: "Article — Kiến thức, link, repo" },
  { value: "log", label: "Log — Chi tiêu, todo, tracking" },
];

const TAG_GROUPS = {
  Domain: ["ai", "code", "life", "finance", "health", "startup", "product", "psychology"],
  Format: ["video", "music", "repo", "file", "article"],
  Style: ["funny", "deep", "technical", "practical", "random"],
  System: ["knowledge", "lesson", "important", "person"],
};

const JSON_TEMPLATE = `{
  "raw_text": "",
  "content_type": "note",
  "importance_score": null,
  "metadata": {
    "tags": [],
    "source": "api"
  }
}`;

export default function MemoryPanel() {
  const [tab, setTab] = useState("form"); // "form" | "json"

  // Form state
  const [rawText, setRawText] = useState("");
  const [contentType, setContentType] = useState("note");
  const [importance, setImportance] = useState("");
  const [tags, setTags] = useState([]);
  const [source, setSource] = useState("api");
  const [personName, setPersonName] = useState("");

  // JSON state
  const [jsonText, setJsonText] = useState(JSON_TEMPLATE);
  const [jsonError, setJsonError] = useState(null);

  // Shared state
  const [alert, setAlert] = useState(null);
  const [saving, setSaving] = useState(false);

  // Lookup
  const [lookupId, setLookupId] = useState("");
  const [lookupResult, setLookupResult] = useState(null);

  const toggleTag = (tag) => {
    setTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  // ─── Form Save ─────────────────────────────────────────────────────────────
  const handleFormSave = async () => {
    if (!rawText.trim()) {
      setAlert({ type: "error", message: "Nội dung không được trống." });
      return;
    }
    setSaving(true);
    setAlert(null);

    const metadata = { source };
    if (tags.length > 0) metadata.tags = tags;
    if (personName.trim()) {
      metadata.extra = { person_name: personName.trim() };
      if (!tags.includes("person")) metadata.tags = [...(metadata.tags || []), "person"];
    }

    try {
      const result = await saveMemory({
        raw_text: rawText,
        content_type: contentType,
        importance_score: importance ? parseFloat(importance) : undefined,
        metadata,
      });
      setAlert({
        type: "success",
        message: `✅ Saved! ID: ${result.id.slice(0, 8)}... | Embedding job created.`,
      });
      setRawText("");
      setTags([]);
      setPersonName("");
      setImportance("");
    } catch (err) {
      setAlert({ type: "error", message: err.message });
    }
    setSaving(false);
  };

  // ─── JSON Save ─────────────────────────────────────────────────────────────
  const handleJsonSave = async () => {
    setJsonError(null);
    setAlert(null);

    let parsed;
    try {
      parsed = JSON.parse(jsonText);
    } catch (e) {
      setJsonError(`Invalid JSON: ${e.message}`);
      return;
    }

    // Normalize: single object → array of 1
    const items = Array.isArray(parsed) ? parsed : [parsed];

    if (items.length === 0) {
      setJsonError("Array is empty.");
      return;
    }

    // Validate all items first
    for (let i = 0; i < items.length; i++) {
      if (!items[i].raw_text || !items[i].raw_text.trim()) {
        setJsonError(`Item ${i + 1}: raw_text is required and cannot be empty.`);
        return;
      }
    }

    setSaving(true);
    let saved = 0;
    let failed = 0;
    let lastError = "";

    for (const item of items) {
      try {
        await saveMemory({
          raw_text: item.raw_text,
          content_type: item.content_type || "note",
          importance_score: item.importance_score ?? undefined,
          metadata: item.metadata || {},
        });
        saved++;
      } catch (err) {
        failed++;
        lastError = err.message;
      }
    }

    if (failed === 0) {
      setAlert({
        type: "success",
        message: `✅ Saved ${saved}/${items.length} memories! Embedding jobs created.`,
      });
      setJsonText(JSON_TEMPLATE);
    } else {
      setAlert({
        type: "error",
        message: `⚠ Saved ${saved}, failed ${failed}. Last error: ${lastError}`,
      });
    }
    setSaving(false);
  };

  const handleLookup = async () => {
    if (!lookupId.trim()) return;
    setLookupResult(null);
    try {
      const result = await getMemory(lookupId.trim());
      setLookupResult(result);
    } catch (err) {
      setAlert({ type: "error", message: err.message });
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>🧠 Memory Management</h2>
        <p>Thêm và xem memory — enforces Memory Contract V1</p>
      </div>

      {alert && (
        <div className={`alert ${alert.type}`}>{alert.message}</div>
      )}

      {/* ─── Tab Switcher ─── */}
      <div className="mode-selector" style={{ marginBottom: 16 }}>
        <button
          className={`mode-btn ${tab === "form" ? "active" : ""}`}
          onClick={() => setTab("form")}
        >
          📋 Form
        </button>
        <button
          className={`mode-btn ${tab === "json" ? "active" : ""}`}
          onClick={() => setTab("json")}
        >
          {"{ }"} JSON
        </button>
      </div>

      {/* ─── Tab 1: Form ─── */}
      {tab === "form" && (
        <div className="form-card">
          <h3>Thêm Memory Mới</h3>

          <div className="form-group">
            <label>Raw Text *</label>
            <textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="Nhập nội dung memory..."
              rows={4}
            />
          </div>

          <div className="form-group">
            <label>Content Type</label>
            <select value={contentType} onChange={(e) => setContentType(e.target.value)}>
              {CONTENT_TYPES.map((ct) => (
                <option key={ct.value} value={ct.value}>{ct.label}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Tags</label>
            {Object.entries(TAG_GROUPS).map(([group, groupTags]) => (
              <div key={group} style={{ marginBottom: 8 }}>
                <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: 4 }}>
                  {group}
                </div>
                <div className="tag-grid">
                  {groupTags.map((tag) => (
                    <span
                      key={tag}
                      className={`tag-chip ${tags.includes(tag) ? "selected" : ""}`}
                      onClick={() => toggleTag(tag)}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="form-group">
            <label>Person Name (nếu memory về người)</label>
            <input
              value={personName}
              onChange={(e) => setPersonName(e.target.value)}
              placeholder="Ví dụ: Linh"
            />
          </div>

          <div className="form-group">
            <label>Importance Score (0.0 — 1.0)</label>
            <input
              type="number"
              min="0"
              max="1"
              step="0.1"
              value={importance}
              onChange={(e) => setImportance(e.target.value)}
              placeholder="Optional"
            />
          </div>

          <button className="btn-primary" onClick={handleFormSave} disabled={saving}>
            {saving ? "Đang lưu..." : "💾 Lưu Memory"}
          </button>
        </div>
      )}

      {/* ─── Tab 2: Raw JSON ─── */}
      {tab === "json" && (
        <div className="form-card">
          <h3>Paste JSON Payload</h3>
          <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: 12 }}>
            Paste đúng format của <code>POST /api/v1/memory</code>. Hệ thống sẽ validate trước khi gửi.
          </p>

          {jsonError && (
            <div className="alert error" style={{ marginBottom: 12 }}>{jsonError}</div>
          )}

          <div className="form-group">
            <label>JSON Body</label>
            <textarea
              value={jsonText}
              onChange={(e) => { setJsonText(e.target.value); setJsonError(null); }}
              rows={12}
              style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem", lineHeight: 1.6 }}
              spellCheck={false}
            />
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn-primary" onClick={handleJsonSave} disabled={saving}>
              {saving ? "Đang lưu..." : "🚀 Send JSON"}
            </button>
            <button
              className="btn-primary"
              style={{ background: "var(--bg-tertiary)", border: "1px solid var(--border)" }}
              onClick={() => setJsonText(JSON_TEMPLATE)}
            >
              ↻ Reset
            </button>
          </div>
        </div>
      )}

      {/* ─── Lookup ─── */}
      <div className="form-card">
        <h3>Tra cứu Memory theo ID</h3>
        <div className="form-group">
          <label>Memory ID (UUID)</label>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              value={lookupId}
              onChange={(e) => setLookupId(e.target.value)}
              placeholder="a1b2c3d4-..."
              style={{ flex: 1 }}
            />
            <button className="btn-primary" onClick={handleLookup}>🔍</button>
          </div>
        </div>

        {lookupResult && (
          <div className="result-card" style={{ marginTop: 12 }}>
            <div className="result-header">
              <span className="result-type">{lookupResult.content_type}</span>
              <span className={`badge ${lookupResult.has_embedding ? "success" : "warning"}`}>
                {lookupResult.has_embedding ? "Embedded" : "Pending"}
              </span>
            </div>
            <div className="result-text">{lookupResult.raw_text}</div>
            <div className="result-footer">
              <span>ID: {lookupResult.id.slice(0, 8)}...</span>
              <span>Created: {new Date(lookupResult.created_at).toLocaleString()}</span>
              {lookupResult.importance_score != null && (
                <span>Score: {lookupResult.importance_score}</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
