const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {})
    },
    ...options
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }
  return response.text();
}

export async function sendQuery(query, conversationHistory = [], mode = 'hybrid', userPrompt = null) {
  return request('/api/query', {
    method: 'POST',
    body: JSON.stringify({ query, conversation_history: conversationHistory, mode, user_prompt: userPrompt })
  });
}

export async function loadFullGraph() {
  return request('/api/graph/full', { method: 'GET' });
}

export async function loadSubgraph(entities) {
  const param = Array.isArray(entities) ? entities.join(',') : entities;
  return request(`/api/graph/subgraph?entities=${encodeURIComponent(param)}`, { method: 'GET' });
}

export async function loadStats() {
  return request('/api/stats', { method: 'GET' });
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/api/documents/upload`, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }

  return response.json();
}

export async function startIngestion() {
  return request('/api/documents/ingest', { method: 'POST' });
}

export async function getIngestionStatus() {
  return request('/api/documents/ingest/status', { method: 'GET' });
}

export async function checkHealth() {
  return request('/api/health', { method: 'GET' });
}

export function createWebSocket() {
  try {
    const url = new URL(API_BASE);
    url.protocol = url.protocol.replace('http', 'ws');
    url.pathname = '/ws';
    return new WebSocket(url.toString());
  } catch (error) {
    const fallback = API_BASE.replace(/^http/, 'ws');
    return new WebSocket(`${fallback}/ws`);
  }
}
