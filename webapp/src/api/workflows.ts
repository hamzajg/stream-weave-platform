/**
 * Typed client for `/api/workflows`.
 *
 * The details the UI must get right:
 * - a workflow's graph lives on its *draft* version, so `definition` in the
 *   workflow response is the draft graph;
 * - validation failures come back as `422` with
 *   `detail: {message, problems: [...]}` — those strings are what the builder
 *   shows next to the editor, so they are parsed rather than swallowed;
 * - another tenant's workflow is `404` (never `403`), so a stale link degrades
 *   to "not found" instead of a permission error.
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export type NodeType = 'trigger' | 'agent' | 'condition' | 'action';

export const NODE_TYPES: NodeType[] = ['trigger', 'agent', 'condition', 'action'];

export interface WorkflowNode {
  id: string;
  type: NodeType;
  label?: string;
  config?: Record<string, unknown>;
}

export interface WorkflowEdge {
  source: string;
  target: string;
}

export interface WorkflowDefinition {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface Workflow {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  draft_version: number | null;
  published_version: number | null;
  definition: WorkflowDefinition;
}

export interface WorkflowVersion {
  id: string;
  version: number;
  status: 'draft' | 'published';
  definition: WorkflowDefinition;
  created_at: string;
  published_at: string | null;
}

export class ApiError extends Error {
  status: number;
  problems: string[];

  constructor(status: number, message: string, problems: string[] = []) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.problems = problems;
  }
}

function authHeaders(): Record<string, string> {
  const tokens = localStorage.getItem('tokens');
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (tokens) headers.Authorization = `Bearer ${JSON.parse(tokens).access_token}`;
  return headers;
}

function problemsFrom(body: unknown): string[] {
  const detail = (body as { detail?: unknown } | null)?.detail;

  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const { problems, message } = detail as { problems?: unknown; message?: unknown };
    if (Array.isArray(problems)) return problems.map(String);
    if (typeof message === 'string') return [message];
  }
  // FastAPI's own request validation errors.
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      const entry = item as { loc?: unknown[]; msg?: unknown };
      const where = Array.isArray(entry.loc) ? entry.loc.join('.') : 'request';
      return `${where}: ${String(entry.msg ?? 'invalid value')}`;
    });
  }
  if (typeof detail === 'string') return [detail];
  return [];
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { ...init, headers: { ...authHeaders(), ...init.headers } });

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let body: unknown;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }

  if (!res.ok) {
    const problems = problemsFrom(body);
    const detail = (body as { detail?: unknown } | null)?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : problems[0] ?? `Request failed (${res.status})`;
    throw new ApiError(res.status, message, problems);
  }

  return body as T;
}

export function listWorkflows(organizationId?: string): Promise<Workflow[]> {
  const query = organizationId ? `?organization_id=${encodeURIComponent(organizationId)}` : '';
  return request<Workflow[]>(`/api/workflows${query}`);
}

export function getWorkflow(id: string): Promise<Workflow> {
  return request<Workflow>(`/api/workflows/${id}`);
}

export function createWorkflow(input: {
  organization_id: string;
  name: string;
  description?: string;
}): Promise<Workflow> {
  return request<Workflow>('/api/workflows', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function saveDraft(id: string, definition: WorkflowDefinition): Promise<WorkflowVersion> {
  return request<WorkflowVersion>(`/api/workflows/${id}/draft`, {
    method: 'PUT',
    body: JSON.stringify(definition),
  });
}

export function emptyDefinition(): WorkflowDefinition {
  return { nodes: [], edges: [] };
}

/** An id that is unique within `definition` — `n1`, `n2`, … */
export function nextNodeId(definition: WorkflowDefinition): string {
  const used = new Set(definition.nodes.map((node) => node.id));
  for (let i = 1; i <= used.size + 1; i += 1) {
    const candidate = `n${i}`;
    if (!used.has(candidate)) return candidate;
  }
  return `n${Date.now().toString(36)}`;
}
