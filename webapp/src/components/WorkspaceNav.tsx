import { useNavigate } from 'react-router-dom';
import { LayoutDashboard, Workflow, Bot, Building2, LogOut } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useOrganization } from '../contexts/OrganizationContext';

type Section = 'dashboard' | 'workflows' | 'agent';

const LINKS: { key: Section; label: string; path: string; icon: typeof Workflow }[] = [
  { key: 'dashboard', label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { key: 'workflows', label: 'Workflows', path: '/workflows', icon: Workflow },
  { key: 'agent', label: 'Agent', path: '/agent', icon: Bot },
];

export function WorkspaceNav({ active }: { active: Section }) {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { currentOrganization } = useOrganization();

  return (
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
            {LINKS.map(({ key, label, path, icon: Icon }) => (
              <button
                key={key}
                onClick={() => navigate(path)}
                className={
                  key === active
                    ? 'px-3 py-2 rounded text-sm font-medium text-text-primary bg-accent-dim'
                    : 'px-3 py-2 rounded text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-background-tertiary transition-colors'
                }
              >
                <Icon className="w-4 h-4 inline mr-2" />
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4">
          {currentOrganization && (
            <span className="hidden sm:flex items-center gap-2 text-sm text-text-secondary">
              <Building2 className="w-4 h-4" />
              {currentOrganization.name}
            </span>
          )}
          <button
            onClick={() => {
              logout();
              navigate('/');
            }}
            className="flex items-center gap-2 px-3 py-2 rounded text-sm text-text-secondary hover:text-text-primary hover:bg-background-tertiary transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </div>
    </nav>
  );
}
