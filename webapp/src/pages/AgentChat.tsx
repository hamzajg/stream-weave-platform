import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, LogOut, Plus, Send, Bot,
  Check, X, Clock, AlertTriangle, Wrench, ChevronDown, Building2,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useOrganization } from '../contexts/OrganizationContext';

interface Conversation {
  id: string;
  organization_id: string;
  user_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

interface Message {
  id: string;
  role: string;
  content: string | null;
  tool_name: string | null;
  created_at: string;
}

interface PendingAction {
  id: string;
  conversation_id: string;
  organization_id: string;
  user_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  status: string;
  result: Record<string, unknown> | null;
  error: string | null;
  expires_at: string;
  created_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function authHeaders(): Record<string, string> {
  const tokens = localStorage.getItem('tokens');
  if (!tokens) return {};
  return { Authorization: `Bearer ${JSON.parse(tokens).access_token}` };
}

function isExpired(action: PendingAction): boolean {
  return new Date(action.expires_at).getTime() < Date.now();
}

export function AgentChat() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const {
    organizations, currentOrganization, setCurrentOrganization,
    isLoading: orgLoading,
  } = useOrganization();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConv, setActiveConv] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showOrgDropdown, setShowOrgDropdown] = useState(false);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadConversations = useCallback(async () => {
    if (!currentOrganization) return;
    const res = await fetch(
      `${API_URL}/api/agents/conversations?organization_id=${currentOrganization.id}`,
      { headers: authHeaders() },
    );
    if (res.ok) setConversations(await res.json());
  }, [currentOrganization]);

  const loadPendingActions = useCallback(async (convId: string) => {
    const res = await fetch(
      `${API_URL}/api/agents/actions?conversation_id=${convId}&action_status=pending`,
      { headers: authHeaders() },
    );
    if (res.ok) setPendingActions(await res.json());
  }, []);

  const openConversation = useCallback(async (conv: Conversation) => {
    setActiveConv(conv);
    setError(null);
    const res = await fetch(`${API_URL}/api/agents/conversations/${conv.id}`, {
      headers: authHeaders(),
    });
    if (res.ok) {
      const detail = await res.json();
      setMessages(detail.messages);
    }
    await loadPendingActions(conv.id);
  }, [loadPendingActions]);

  useEffect(() => {
    setActiveConv(null);
    setMessages([]);
    setPendingActions([]);
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, pendingActions]);

  const handleNewChat = async () => {
    if (!currentOrganization) return;
    const res = await fetch(`${API_URL}/api/agents/conversations`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ organization_id: currentOrganization.id }),
    });
    if (res.ok) {
      const conv = await res.json();
      await loadConversations();
      await openConversation(conv);
    }
  };

  const handleSend = async () => {
    const content = input.trim();
    if (!content || !activeConv || sending) return;
    setSending(true);
    setError(null);
    setInput('');

    // Optimistic user message; the API excludes it from the response.
    const optimistic: Message = {
      id: `local-${Date.now()}`,
      role: 'user',
      content,
      tool_name: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);

    try {
      const res = await fetch(
        `${API_URL}/api/agents/conversations/${activeConv.id}/messages`,
        {
          method: 'POST',
          headers: { ...authHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ content }),
        },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${res.status})`);
      }
      const data = await res.json();
      setMessages((prev) => [...prev, ...data.messages]);
      await loadPendingActions(activeConv.id);
      await loadConversations();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const resolveAction = async (action: PendingAction, decision: 'approve' | 'reject') => {
    setResolvingId(action.id);
    setError(null);
    try {
      const res = await fetch(
        `${API_URL}/api/agents/actions/${action.id}/${decision}`,
        { method: 'POST', headers: authHeaders() },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${res.status})`);
      }
      if (activeConv) await loadPendingActions(activeConv.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : `Failed to ${decision} action`);
    } finally {
      setResolvingId(null);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  if (orgLoading || !currentOrganization) {
    return (
      <div className="min-h-screen bg-background-primary flex items-center justify-center">
        <div className="text-text-secondary">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background-primary text-text-primary font-body blueprint-grid">
      {/* Navbar — same shell as Dashboard */}
      <nav className="fixed top-0 left-0 right-0 h-16 bg-background-primary/85 backdrop-blur-xl border-b border-border-subtle z-50">
        <div className="max-w-[1400px] mx-auto px-4 h-full flex items-center justify-between">
          <div className="flex items-center gap-8">
            <button
              onClick={() => navigate('/dashboard')}
              className="font-display text-lg font-semibold text-accent tracking-wider"
            >
              STREAMWEAVE
            </button>
            <div className="hidden md:flex items-center gap-1">
              <button
                onClick={() => navigate('/dashboard')}
                className="px-3 py-2 rounded text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-background-tertiary transition-colors"
              >
                <LayoutDashboard className="w-4 h-4 inline mr-2" />
                Dashboard
              </button>
              <button className="px-3 py-2 rounded text-sm font-medium text-text-primary bg-accent-dim">
                <Bot className="w-4 h-4 inline mr-2" />
                Agent
              </button>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative">
              <button
                onClick={() => setShowOrgDropdown(!showOrgDropdown)}
                className="flex items-center gap-2 px-3 py-2 bg-background-secondary border border-border-subtle rounded text-sm hover:border-border-hover transition-colors"
              >
                <Building2 className="w-4 h-4 text-accent" />
                <span className="max-w-[150px] truncate">{currentOrganization.name}</span>
                <ChevronDown className="w-4 h-4 text-text-tertiary" />
              </button>
              {showOrgDropdown && (
                <div className="absolute top-full right-0 mt-2 w-64 bg-background-secondary border border-border-subtle rounded-lg shadow-lg py-1 z-50">
                  <div className="px-3 py-2 text-xs font-medium text-text-tertiary uppercase tracking-wider">
                    Your Organizations
                  </div>
                  {organizations.map((org) => (
                    <button
                      key={org.id}
                      onClick={() => {
                        setCurrentOrganization(org);
                        setShowOrgDropdown(false);
                      }}
                      className={`w-full px-3 py-2 text-left text-sm flex items-center justify-between hover:bg-background-tertiary ${
                        org.id === currentOrganization.id ? 'bg-accent-dim/30' : ''
                      }`}
                    >
                      <span>{org.name}</span>
                      <span className="text-xs text-text-tertiary capitalize">{org.role}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="flex items-center gap-3 pl-4 border-l border-border-subtle">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-medium">{user?.full_name}</p>
                <p className="text-xs text-text-tertiary">{user?.email}</p>
              </div>
              <button
                onClick={handleLogout}
                className="p-2 text-text-tertiary hover:text-red-400 transition-colors"
                title="Logout"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="pt-24 pb-6 px-4 h-[calc(100vh-6rem)]">
        <div className="max-w-[1400px] mx-auto h-full flex gap-6">
          {/* Conversation sidebar */}
          <aside className="w-64 flex-shrink-0 flex flex-col bg-background-secondary border border-border-subtle rounded-lg overflow-hidden">
            <div className="p-3 border-b border-border-subtle">
              <button
                onClick={handleNewChat}
                className="w-full px-3 py-2 bg-accent text-background-primary text-sm font-medium rounded flex items-center justify-center gap-2 hover:bg-accent-hover transition-colors"
              >
                <Plus className="w-4 h-4" />
                New chat
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {conversations.length === 0 && (
                <p className="text-xs text-text-tertiary text-center py-6">
                  No conversations yet
                </p>
              )}
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => openConversation(conv)}
                  className={`w-full text-left px-3 py-2 rounded text-sm truncate transition-colors ${
                    activeConv?.id === conv.id
                      ? 'bg-accent-dim/40 text-text-primary'
                      : 'text-text-secondary hover:bg-background-tertiary hover:text-text-primary'
                  }`}
                  title={conv.title || 'Untitled conversation'}
                >
                  {conv.title || 'Untitled conversation'}
                </button>
              ))}
            </div>
          </aside>

          {/* Chat area */}
          <section className="flex-1 flex flex-col bg-background-secondary border border-border-subtle rounded-lg overflow-hidden min-w-0">
            {!activeConv ? (
              <div className="flex-1 flex flex-col items-center justify-center text-text-tertiary">
                <Bot className="w-12 h-12 mb-3 opacity-50" />
                <p className="text-sm">Select a conversation or start a new chat</p>
              </div>
            ) : (
              <>
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  {messages.map((msg) => (
                    <MessageBubble key={msg.id} message={msg} />
                  ))}
                  {pendingActions.length > 0 && (
                    <div className="space-y-3 pt-2">
                      {pendingActions.map((action) => (
                        <PendingActionCard
                          key={action.id}
                          action={action}
                          busy={resolvingId === action.id}
                          onResolve={resolveAction}
                        />
                      ))}
                    </div>
                  )}
                  {sending && (
                    <div className="flex items-center gap-2 text-text-tertiary text-sm">
                      <Bot className="w-4 h-4 animate-pulse" />
                      Agent is thinking…
                    </div>
                  )}
                  <div ref={bottomRef} />
                </div>

                {error && (
                  <div className="mx-4 mb-2 px-3 py-2 bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    {error}
                  </div>
                )}

                <div className="p-4 border-t border-border-subtle">
                  <div className="flex gap-2">
                    <input
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                      placeholder="Ask the agent about your organization…"
                      disabled={sending}
                      className="flex-1 px-4 py-2.5 bg-background-primary border border-border-subtle rounded text-sm text-text-primary placeholder-text-tertiary focus:outline-none focus:border-accent transition-colors disabled:opacity-50"
                    />
                    <button
                      onClick={handleSend}
                      disabled={sending || !input.trim()}
                      className="px-4 py-2.5 bg-accent text-background-primary rounded text-sm font-medium flex items-center gap-2 hover:bg-accent-hover transition-colors disabled:opacity-50"
                    >
                      <Send className="w-4 h-4" />
                      Send
                    </button>
                  </div>
                  <p className="text-xs text-text-tertiary mt-2">
                    Write actions require your approval before they execute.
                  </p>
                </div>
              </>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] px-4 py-2.5 bg-accent-dim/40 border border-border-subtle rounded-lg">
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  if (message.role === 'tool') {
    return (
      <div className="flex items-start gap-2">
        <Wrench className="w-4 h-4 text-text-tertiary mt-1 flex-shrink-0" />
        <div className="max-w-[85%]">
          <p className="text-xs text-text-tertiary mb-1">
            tool: {message.tool_name}
          </p>
          <pre className="text-xs bg-background-primary border border-border-subtle rounded p-2 overflow-x-auto text-text-secondary whitespace-pre-wrap">
            {message.content}
          </pre>
        </div>
      </div>
    );
  }

  // assistant
  return (
    <div className="flex items-start gap-2">
      <Bot className="w-4 h-4 text-accent mt-1 flex-shrink-0" />
      <div className="max-w-[85%] px-4 py-2.5 bg-background-primary border border-border-subtle rounded-lg">
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}

function PendingActionCard({
  action,
  busy,
  onResolve,
}: {
  action: PendingAction;
  busy: boolean;
  onResolve: (action: PendingAction, decision: 'approve' | 'reject') => void;
}) {
  const expired = isExpired(action);
  const args = Object.entries(action.arguments)
    .map(([k, v]) => `${k}: ${String(v)}`)
    .join('  ·  ');

  return (
    <div className="border border-amber-500/40 bg-amber-500/5 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <Clock className="w-4 h-4 text-amber-400" />
        <span className="text-sm font-medium">Approval required</span>
        <span className="text-xs text-text-tertiary font-mono">{action.tool_name}</span>
      </div>
      {args && <p className="text-xs text-text-secondary mb-1">{args}</p>}
      <p className="text-xs text-text-tertiary mb-3">
        Proposed {new Date(action.created_at).toLocaleString()} · expires{' '}
        {new Date(action.expires_at).toLocaleString()}
        {expired && ' · expired'}
      </p>
      <div className="flex gap-2">
        <button
          onClick={() => onResolve(action, 'approve')}
          disabled={busy || expired}
          className="px-3 py-1.5 bg-accent text-background-primary text-xs font-medium rounded flex items-center gap-1.5 hover:bg-accent-hover transition-colors disabled:opacity-50"
        >
          <Check className="w-3.5 h-3.5" />
          Approve
        </button>
        <button
          onClick={() => onResolve(action, 'reject')}
          disabled={busy || expired}
          className="px-3 py-1.5 bg-background-primary border border-border-subtle text-text-secondary text-xs font-medium rounded flex items-center gap-1.5 hover:border-red-400/50 hover:text-red-400 transition-colors disabled:opacity-50"
        >
          <X className="w-3.5 h-3.5" />
          Reject
        </button>
        {busy && <span className="text-xs text-text-tertiary self-center">Resolving…</span>}
      </div>
    </div>
  );
}
