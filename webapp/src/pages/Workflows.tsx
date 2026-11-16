import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Workflow as WorkflowIcon, ArrowRight, AlertTriangle, X } from 'lucide-react';
import { useOrganization } from '../contexts/OrganizationContext';
import { WorkspaceNav } from '../components/WorkspaceNav';
import {
  ApiError,
  createWorkflow,
  listWorkflows,
  type Workflow,
} from '../api/workflows';

export function Workflows() {
  const navigate = useNavigate();
  const { currentOrganization, isLoading: orgLoading } = useOrganization();

  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [creating, setCreating] = useState(false);
  const [createProblems, setCreateProblems] = useState<string[]>([]);

  const load = useCallback(async () => {
    if (!currentOrganization) return;
    setIsLoading(true);
    setLoadError(null);
    try {
      setWorkflows(await listWorkflows(currentOrganization.id));
    } catch (error) {
      setLoadError(error instanceof ApiError ? error.message : 'Could not load workflows');
    } finally {
      setIsLoading(false);
    }
  }, [currentOrganization]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!currentOrganization) return;
    setCreating(true);
    setCreateProblems([]);
    try {
      const created = await createWorkflow({
        organization_id: currentOrganization.id,
        name: name.trim(),
        description: description.trim() || undefined,
      });
      navigate(`/workflows/${created.id}`);
    } catch (error) {
      if (error instanceof ApiError) {
        setCreateProblems(error.problems.length ? error.problems : [error.message]);
      } else {
        setCreateProblems(['Could not create the workflow']);
      }
    } finally {
      setCreating(false);
    }
  };

  if (orgLoading) {
    return (
      <div className="min-h-screen bg-background-primary flex items-center justify-center">
        <div className="text-text-secondary">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background-primary text-text-primary font-body blueprint-grid">
      <WorkspaceNav active="workflows" />

      <main className="max-w-[1100px] mx-auto px-4 pt-28 pb-16">
        <div className="flex items-start justify-between gap-4 mb-8">
          <div>
            <h1 className="font-display text-2xl font-semibold mb-1">Workflows</h1>
            <p className="text-sm text-text-secondary">
              Agentic workflows in {currentOrganization?.name ?? 'your organization'}.
              A workflow is a draft graph you edit and publish.
            </p>
          </div>
          <button
            onClick={() => setShowCreate((open) => !open)}
            className="flex items-center gap-2 px-4 py-2 rounded bg-accent text-background-primary text-sm font-semibold hover:opacity-90 transition-opacity"
          >
            {showCreate ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
            {showCreate ? 'Cancel' : 'New workflow'}
          </button>
        </div>

        {showCreate && (
          <form
            onSubmit={handleCreate}
            className="mb-8 rounded-lg border border-border-subtle bg-background-secondary p-5 space-y-4"
          >
            <div>
              <label htmlFor="workflow-name" className="block text-xs uppercase tracking-wide text-text-secondary mb-1">
                Name
              </label>
              <input
                id="workflow-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
                maxLength={255}
                autoFocus
                placeholder="Invoice triage"
                className="w-full px-3 py-2 rounded bg-background-tertiary border border-border-subtle text-sm focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label htmlFor="workflow-description" className="block text-xs uppercase tracking-wide text-text-secondary mb-1">
                Description <span className="normal-case text-text-tertiary">(optional)</span>
              </label>
              <textarea
                id="workflow-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={2}
                placeholder="What this workflow does, and who runs it"
                className="w-full px-3 py-2 rounded bg-background-tertiary border border-border-subtle text-sm focus:outline-none focus:border-accent"
              />
            </div>

            {createProblems.length > 0 && (
              <ul className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300 space-y-1">
                {createProblems.map((problem) => (
                  <li key={problem} className="flex gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{problem}</span>
                  </li>
                ))}
              </ul>
            )}

            <button
              type="submit"
              disabled={creating || !name.trim()}
              className="px-4 py-2 rounded bg-accent text-background-primary text-sm font-semibold disabled:opacity-50"
            >
              {creating ? 'Creating…' : 'Create workflow'}
            </button>
          </form>
        )}

        {loadError && (
          <div className="mb-6 rounded border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {loadError}
          </div>
        )}

        {isLoading ? (
          <div className="text-sm text-text-secondary">Loading workflows…</div>
        ) : workflows.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border-subtle px-6 py-14 text-center">
            <WorkflowIcon className="w-8 h-8 mx-auto mb-3 text-text-tertiary" />
            <p className="text-sm text-text-secondary mb-1">No workflows yet.</p>
            <p className="text-xs text-text-tertiary">
              Create one, then add a trigger, an agent and an action on the detail page.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-border-subtle rounded-lg border border-border-subtle bg-background-secondary">
            {workflows.map((workflow) => (
              <li key={workflow.id}>
                <button
                  onClick={() => navigate(`/workflows/${workflow.id}`)}
                  className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left hover:bg-background-tertiary transition-colors"
                >
                  <span className="min-w-0">
                    <span className="block text-sm font-medium truncate">{workflow.name}</span>
                    <span className="block text-xs text-text-tertiary truncate">
                      {workflow.slug}
                      {workflow.description ? ` · ${workflow.description}` : ''}
                    </span>
                  </span>
                  <span className="flex items-center gap-3 shrink-0 text-xs text-text-secondary">
                    <span className="px-2 py-0.5 rounded bg-background-tertiary">
                      {workflow.published_version
                        ? `published v${workflow.published_version}`
                        : 'unpublished'}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-background-tertiary">
                      {workflow.definition.nodes.length} nodes
                    </span>
                    <ArrowRight className="w-4 h-4" />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
