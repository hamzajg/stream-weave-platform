import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { useAuth } from './AuthContext';

interface Organization {
  id: string;
  name: string;
  slug: string;
  industry: string;
  role: 'owner' | 'admin' | 'editor' | 'viewer';
  member_count: number;
}

interface OrganizationContextType {
  organizations: Organization[];
  currentOrganization: Organization | null;
  setCurrentOrganization: (org: Organization | null) => void;
  isLoading: boolean;
  refreshOrganizations: () => Promise<void>;
}

const OrganizationContext = createContext<OrganizationContextType | undefined>(undefined);

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function OrganizationProvider({ children }: { children: ReactNode }) {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [currentOrganization, setCurrentOrganization] = useState<Organization | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { isAuthenticated } = useAuth();

  const fetchOrganizations = async () => {
    const tokens = localStorage.getItem('tokens');
    if (!tokens) {
      setIsLoading(false);
      return;
    }

    const { access_token } = JSON.parse(tokens);

    try {
      const response = await fetch(`${API_URL}/api/dashboard/organizations`, {
        headers: {
          'Authorization': `Bearer ${access_token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setOrganizations(data);
        
        // Set first org as current if none selected
        if (data.length > 0 && !currentOrganization) {
          setCurrentOrganization(data[0]);
          localStorage.setItem('currentOrg', JSON.stringify(data[0]));
        }
      }
    } catch (error) {
      console.error('Failed to fetch organizations:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      // Check for stored current org
      const stored = localStorage.getItem('currentOrg');
      if (stored) {
        setCurrentOrganization(JSON.parse(stored));
      }
      fetchOrganizations();
    } else {
      setOrganizations([]);
      setCurrentOrganization(null);
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  const handleSetCurrentOrganization = (org: Organization | null) => {
    setCurrentOrganization(org);
    if (org) {
      localStorage.setItem('currentOrg', JSON.stringify(org));
    } else {
      localStorage.removeItem('currentOrg');
    }
  };

  const value: OrganizationContextType = {
    organizations,
    currentOrganization,
    setCurrentOrganization: handleSetCurrentOrganization,
    isLoading,
    refreshOrganizations: fetchOrganizations,
  };

  return (
    <OrganizationContext.Provider value={value}>
      {children}
    </OrganizationContext.Provider>
  );
}

export function useOrganization() {
  const context = useContext(OrganizationContext);
  if (context === undefined) {
    throw new Error('useOrganization must be used within an OrganizationProvider');
  }
  return context;
}
