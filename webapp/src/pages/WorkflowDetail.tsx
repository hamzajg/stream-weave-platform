import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Plus, Trash2, AlertTriangle, Check, Save } from 'lucide-react';
import { WorkspaceNav } from '../components/WorkspaceNav';
import {
  ApiError,
  NODE_TYPES,
  emptyDefinition,
  getWorkflow,
  nextNodeId,
  saveDraft,
  type NodeType,
  type Workflow,
  type WorkflowDefinition,
} from '../api/workflows';

export function WorkflowDetail() {
  const { id = '' } = useParams();
  const navigate = useNavigate();

  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [definition, setDefinition] = useState<WorkflowDefinition>(emptyDefinition());
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [saving, setSaving] = useState(false);
  const [problems, setProblems] = useState<string[]>([]);
  const [saved, setSaved] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const loaded = await getWorkflow(id);
      setWorkflow(loaded);
      setDefinition(loaded.definition ?? emptyDefinition());
      setDirty(false);
    } catch (error) {
      setLoadError(
        error instanceof ApiError && error.status === 404
          ? 'This workflow does not exist in your organization.'
          : error instanceof ApiError
            ? error.message
            : 'Could not load the workflow',
      );
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  const update = (next: WorkflowDefinition) => {
    setDefinition(next);
    setDirty(true);
    setSaved(null);
    setProblems([]);
  };

  const addNode = () => {
    const nodeId = nextNodeId(definition);
    update({
      ...definition,
      nodes: [...definition.nodes, { id: nodeId, type: 'action', label: '' }],
    });
  };

  const removeNode = (nodeId: string) => {
    update({
      nodes: definition.nodes.filter((node) => node.id !== nodeId),
      // A dangling edge would be rejected on save; drop them with the node.
      edges: definition.edges.filter((edge) => edge.source !== nodeId && edge.target !== nodeId),
    });
  };

  const patchNode = (nodeId: string, patch: Partial<{ type: NodeType; label: string }>) => {
    update({
      ...definition,
      nodes: definition.nodes.map((node) => (node.id === nodeId ? { ...node, ...patch } : node)),
    });
  };

  const addEdge = () => {
    const [source, target] = definition.nodes;
    if (!source || !target) return;
    update({ ...definition, edges: [...definition.edges, { source: source.id, target: target.id }] });
  };

  const patchEdge = (index: number, patch: Partial<{ source: string; target: string }>) => {
    update({
      ...definition,
      edges: definition.edges.map((edge, i) => (i === index ? { ...edge, ...patch } : edge)),
    });
  };

  const removeEdge = (index: number) => {
    update({ ...definition, edges: definition.edges.filter((_, i) => i !== index) });
  };

  const handleSave = async () => {
    setSaving(true);
    setProblems([]);
    setSaved(null);
    try {
      const version = await saveDraft(id, definition);
      setSaved(`Draft saved as version ${version.version}`);
      setDirty(false);
      const refreshed = await getWorkflow(id);
      setWorkflow(refreshed);
    } catch (error) {
      if (error instanceof ApiError) {
        setProblems(error.problems.length ? error.problems : [error.message]);
      } else {
        setProblems(['Could not save the draft']);
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-background-primary text-text-primary font-body blueprint-grid">
      <WorkspaceNav active="workflows" />

      <main className="max-w-[1100px] mx-auto px-4 pt-28 pb-16">
        <button
          onClick={() => navigate('/workflows')}
          className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          All workflows
        </button>

        {isLoading ? (
          <div className="text-sm text-text-secondary">Loading workflow…</div>
        ) : loadError ? (
          <div className="rounded border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {loadError}
          </div>
        ) : workflow ? (
          <>
            <header className="flex flex-wrap items-start justify-between gap-4 mb-8">
              <div>
                <h1 className="font-display text-2xl font-semibold mb-1">{workflow.name}</h1>
                <p className="text-xs text-text-tertiary font-mono">{workflow.slug}</p>
                {workflow.description && (
                  <p className="text-sm text-text-secondary mt-2 max-w-2xl">{workflow.description}</p>
                )}
              </div>
              <div className="flex items-center gap-2 text-xs text-text-secondary">
                <span className="px-2 py-1 rounded bg-background-tertiary">
                  draft v{workflow.draft_version ?? '—'}
                </span>
                <span className="px-2 py-1 rounded bg-background-tertiary">
                  {workflow.published_version ? `published v${workflow.published_version}` : 'unpublished'}
                </span>
              </div>
            </header>

            {problems.length > 0 && (
              <div className="mb-6 rounded border border-red-500/40 bg-red-500/10 px-4 py-3">
                <p className="flex items-center gap-2 text-sm font-medium text-red-300 mb-2">
                  <AlertTriangle className="w-4 h-4" />
                  The graph was rejected — nothing was saved
                </p>
                <ul className="list-disc pl-6 text-sm text-red-200 space-y-1">
                  {problems.map((problem) => (
                    <li key={problem}>{problem}</li>
                  ))}
                </ul>
              </div>
            )}

            {saved && (
              <p className="mb-6 flex items-center gap-2 rounded border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
                <Check className="w-4 h-4" />
                {saved}
              </p>
            )}

            <section className="rounded-lg border border-border-subtle bg-background-secondary mb-6">
              <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle">
                <div>
                  <h2 className="text-sm font-semibold">Nodes</h2>
                  <p className="text-xs text-text-tertiary">
                    Exactly one <code>trigger</code> is required; ids are generated for you.
                  </p>
                </div>
                <button
                  onClick={addNode}
                  className="flex items-center gap-2 px-3 py-1.5 rounded border border-border-subtle text-xs hover:bg-background-tertiary"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add node
                </button>
              </div>

              {definition.nodes.length === 0 ? (
                <p className="px-5 py-6 text-sm text-text-secondary">
                  No nodes yet. Add a <code>trigger</code>, then an <code>agent</code> and an{' '}
                  <code>action</code>.
                </p>
              ) : (
                <ul className="divide-y divide-border-subtle">
                  {definition.nodes.map((node) => (
                    <li key={node.id} className="flex flex-wrap items-center gap-3 px-5 py-3">
                      <span className="font-mono text-xs text-text-tertiary w-12">{node.id}</span>
                      <select
                        aria-label={`Type of node ${node.id}`}
                        value={node.type}
                        onChange={(event) => patchNode(node.id, { type: event.target.value as NodeType })}
                        className="px-2 py-1.5 rounded bg-background-tertiary border border-border-subtle text-sm"
                      >
                        {NODE_TYPES.map((type) => (
                          <option key={type} value={type}>
                            {type}
                          </option>
                        ))}
                      </select>
                      <input
                        aria-label={`Label of node ${node.id}`}
                        value={node.label ?? ''}
                        onChange={(event) => patchNode(node.id, { label: event.target.value })}
                        placeholder="Label"
                        className="flex-1 min-w-[12rem] px-2 py-1.5 rounded bg-background-tertiary border border-border-subtle text-sm"
                      />
                      <button
                        onClick={() => removeNode(node.id)}
                        aria-label={`Remove node ${node.id}`}
                        className="p-1.5 rounded text-text-tertiary hover:text-red-300 hover:bg-background-tertiary"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded-lg border border-border-subtle bg-background-secondary mb-6">
              <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle">
                <div>
                  <h2 className="text-sm font-semibold">Edges</h2>
                  <p className="text-xs text-text-tertiary">Each edge connects two declared nodes.</p>
                </div>
                <button
                  onClick={addEdge}
                  disabled={definition.nodes.length < 2}
                  className="flex items-center gap-2 px-3 py-1.5 rounded border border-border-subtle text-xs hover:bg-background-tertiary disabled:opacity-40"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add edge
                </button>
              </div>

              {definition.edges.length === 0 ? (
                <p className="px-5 py-6 text-sm text-text-secondary">No edges yet.</p>
              ) : (
                <ul className="divide-y divide-border-subtle">
                  {definition.edges.map((edge, index) => (
                    <li key={`${edge.source}->${edge.target}-${index}`} className="flex flex-wrap items-center gap-3 px-5 py-3">
                      <select
                        aria-label={`Source of edge ${index + 1}`}
                        value={edge.source}
                        onChange={(event) => patchEdge(index, { source: event.target.value })}
                        className="px-2 py-1.5 rounded bg-background-tertiary border border-border-subtle text-sm"
                      >
                        {definition.nodes.map((node) => (
                          <option key={node.id} value={node.id}>
                            {node.id}
                          </option>
                        ))}
                      </select>
                      <span className="text-text-tertiary">→</span>
                      <select
                        aria-label={`Target of edge ${index + 1}`}
                        value={edge.target}
                        onChange={(event) => patchEdge(index, { target: event.target.value })}
                        className="px-2 py-1.5 rounded bg-background-tertiary border border-border-subtle text-sm"
                      >
                        {definition.nodes.map((node) => (
                          <option key={node.id} value={node.id}>
                            {node.id}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={() => removeEdge(index)}
                        aria-label={`Remove edge ${index + 1}`}
                        className="ml-auto p-1.5 rounded text-text-tertiary hover:text-red-300 hover:bg-background-tertiary"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <div className="flex items-center justify-between gap-4">
              <p className="text-xs text-text-tertiary">
                {dirty ? 'Unsaved changes' : 'Draft is in sync with the server'}
              </p>
              <button
                onClick={handleSave}
                disabled={saving || !dirty}
                className="flex items-center gap-2 px-4 py-2 rounded bg-accent text-background-primary text-sm font-semibold disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Saving…' : 'Save draft'}
              </button>
            </div>
          </>
        ) : null}
      </main>
    </div>
  );
}
