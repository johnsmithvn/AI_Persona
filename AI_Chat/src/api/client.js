/**
 * API Client - Centralized fetch wrapper for AI Person backend.
 * Base URL: http://localhost:8000
 *
 * Endpoints:
 *   POST /api/v1/memory      - Save memory
 *   GET  /api/v1/memory/:id  - Get memory
 *   PATCH /api/v1/memory/:id/archive - Archive memory
 *   POST /api/v1/search      - Semantic search
 *   POST /api/v1/query       - Reasoning (6-mode)
 *   GET  /health             - Health check
 */

const BASE_URL = "http://localhost:8000";

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${BASE_URL}${path}`, opts);
  const data = await res.json();

  if (!res.ok) {
    const msg = data.detail?.message || data.detail || JSON.stringify(data);
    throw new Error(`[${res.status}] ${msg}`);
  }
  return data;
}

// Memory

export async function saveMemory({ raw_text, content_type, importance_score, metadata }) {
  return request("POST", "/api/v1/memory", {
    raw_text,
    content_type,
    importance_score,
    metadata,
  });
}

export async function getMemory(id) {
  return request("GET", `/api/v1/memory/${id}`);
}

export async function archiveMemory(id, { is_archived = true, exclude_from_retrieval = false }) {
  return request("PATCH", `/api/v1/memory/${id}/archive`, {
    is_archived,
    exclude_from_retrieval,
  });
}

// Search

export async function searchMemories({ query, content_type, threshold, limit, metadata_filter }) {
  const body = { query };
  if (content_type) body.content_type = content_type;
  if (threshold != null) body.threshold = threshold;
  if (limit != null) body.limit = limit;
  if (metadata_filter) body.metadata_filter = metadata_filter;
  return request("POST", "/api/v1/search", body);
}

// Reasoning

export async function queryReasoning({ query, mode = "RECALL", content_type, threshold }) {
  const body = { query, mode };
  if (content_type) body.content_type = content_type;
  if (threshold != null) body.threshold = threshold;
  return request("POST", "/api/v1/query", body);
}

// Health

export async function healthCheck() {
  return request("GET", "/health");
}
