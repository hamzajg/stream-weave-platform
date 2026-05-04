import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Workflow, Users, LogOut,
  Plus, Zap, TrendingUp, Clock, Activity,
  ChevronDown, Building2, Bell
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useOrganization } from '../contexts/OrganizationContext';

interface DashboardStats {
  total_workflows: number;
  total_runs: number;
  active_agents: number;
  success_rate: number;
  runs_today: number;
  runs_this_week: number;
}

interface ActivityItem {
  id: string;
  type: string;
  description: string;
  user: { full_name: string; email: string };
  created_at: string;
}

export function Dashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { organizations, currentOrganization, setCurrentOrganization, isLoading: orgLoading } = useOrganization();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showOrgDropdown, setShowOrgDropdown] = useState(false);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!currentOrganization) return;

    const fetchDashboardData = async () => {
      const tokens = localStorage.getItem('tokens');
      if (!tokens) return;

      const { access_token } = JSON.parse(tokens);

      try {
        // Fetch stats
        const statsRes = await fetch(
          `${API_URL}/api/dashboard/stats?org_id=${currentOrganization.id}`,
          { headers: { 'Authorization': `Bearer ${access_token}` } }
        );
        if (statsRes.ok) {
          setStats(await statsRes.json());
        }

        // Fetch activity
        const activityRes = await fetch(
          `${API_URL}/api/dashboard/activity?org_id=${currentOrganization.id}&limit=10`,
          { headers: { 'Authorization': `Bearer ${access_token}` } }
        );
        if (activityRes.ok) {
          setActivity(await activityRes.json());
        }
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, [currentOrganization]);

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
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 h-16 bg-background-primary/85 backdrop-blur-xl border-b border-border-subtle z-50">
        <div className="max-w-[1400px] mx-auto px-4 h-full flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-8">
            <span className="font-display text-lg font-semibold text-accent tracking-wider">
              STREAMWEAVE
            </span>

            {/* Nav Links */}
            <div className="hidden md:flex items-center gap-1">
              <button className="px-3 py-2 rounded text-sm font-medium text-text-primary bg-accent-dim">
                <LayoutDashboard className="w-4 h-4 inline mr-2" />
                Dashboard
              </button>
              <button className="px-3 py-2 rounded text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-background-tertiary transition-colors">
                <Workflow className="w-4 h-4 inline mr-2" />
                Workflows
              </button>
              <button className="px-3 py-2 rounded text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-background-tertiary transition-colors">
                <Users className="w-4 h-4 inline mr-2" />
                Team
              </button>
            </div>
          </div>

          {/* Right Side */}
          <div className="flex items-center gap-4">
            {/* Org Selector */}
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

            {/* Notifications */}
            <button className="relative p-2 text-text-secondary hover:text-text-primary">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-accent rounded-full" />
            </button>

            {/* User Menu */}
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

      {/* Main Content */}
      <main className="pt-24 pb-12 px-4">
        <div className="max-w-[1400px] mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold mb-2">Dashboard</h1>
            <p className="text-text-secondary">
              Welcome back! Here's what's happening in {currentOrganization.name}.
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex gap-3 mb-8">
            <button className="px-4 py-2 bg-accent text-background-primary font-medium rounded flex items-center gap-2 hover:bg-accent-hover transition-colors">
              <Plus className="w-4 h-4" />
              Create Workflow
            </button>
            <button className="px-4 py-2 bg-background-secondary border border-border-subtle text-text-primary font-medium rounded flex items-center gap-2 hover:border-border-hover transition-colors">
              <Users className="w-4 h-4" />
              Invite Team
            </button>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
            <StatCard
              icon={Workflow}
              label="Total Workflows"
              value={stats?.total_workflows ?? 0}
              loading={isLoading}
            />
            <StatCard
              icon={Zap}
              label="Total Runs"
              value={stats?.total_runs ?? 0}
              loading={isLoading}
            />
            <StatCard
              icon={Activity}
              label="Active Agents"
              value={stats?.active_agents ?? 0}
              loading={isLoading}
            />
            <StatCard
              icon={TrendingUp}
              label="Success Rate"
              value={`${stats?.success_rate ?? 0}%`}
              loading={isLoading}
            />
            <StatCard
              icon={Clock}
              label="Runs Today"
              value={stats?.runs_today ?? 0}
              loading={isLoading}
            />
            <StatCard
              icon={TrendingUp}
              label="This Week"
              value={stats?.runs_this_week ?? 0}
              loading={isLoading}
            />
          </div>

          {/* Content Grid */}
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Recent Workflows */}
            <div className="lg:col-span-2 bg-background-secondary border border-border-subtle rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Recent Workflows</h2>
                <button className="text-sm text-accent hover:text-accent-hover">
                  View All
                </button>
              </div>
              <div className="text-center py-12 text-text-tertiary">
                <Workflow className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No workflows yet</p>
                <p className="text-sm mt-1">Create your first workflow to get started</p>
              </div>
            </div>

            {/* Activity Feed */}
            <div className="bg-background-secondary border border-border-subtle rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4">Activity</h2>
              {activity.length === 0 ? (
                <div className="text-center py-8 text-text-tertiary">
                  <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No recent activity</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {activity.map((item) => (
                    <div key={item.id} className="flex gap-3">
                      <div className="w-8 h-8 rounded-full bg-accent-dim flex items-center justify-center flex-shrink-0">
                        <Activity className="w-4 h-4 text-accent" />
                      </div>
                      <div>
                        <p className="text-sm">{item.description}</p>
                        <p className="text-xs text-text-tertiary mt-0.5">
                          {new Date(item.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  loading,
}: {
  icon: typeof Workflow;
  label: string;
  value: number | string;
  loading: boolean;
}) {
  return (
    <div className="bg-background-secondary border border-border-subtle rounded-lg p-4">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-8 h-8 rounded bg-accent-dim flex items-center justify-center">
          <Icon className="w-4 h-4 text-accent" />
        </div>
        <span className="text-xs text-text-tertiary uppercase tracking-wider">{label}</span>
      </div>
      <p className="text-2xl font-bold">
        {loading ? '-' : value}
      </p>
    </div>
  );
}
