import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2, Building2, Users, User, Sparkles,
  Briefcase, Factory, Landmark, Stethoscope, ShoppingCart, Truck, Leaf, Building,
  ArrowRight, Loader2
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  icon: typeof User;
}

const steps: OnboardingStep[] = [
  {
    id: 'personal',
    title: 'Personal Info',
    description: 'Tell us about yourself',
    icon: User,
  },
  {
    id: 'organization',
    title: 'Organization',
    description: 'Set up your workspace',
    icon: Building2,
  },
  {
    id: 'invite',
    title: 'Invite Team',
    description: 'Collaborate with others',
    icon: Users,
  },
];

const industries = [
  { id: 'manufacturing', label: 'Manufacturing', icon: Factory },
  { id: 'finance', label: 'Finance', icon: Landmark },
  { id: 'insurance', label: 'Insurance', icon: Building },
  { id: 'healthcare', label: 'Healthcare', icon: Stethoscope },
  { id: 'ecommerce', label: 'Ecommerce', icon: ShoppingCart },
  { id: 'transportation', label: 'Transportation', icon: Truck },
  { id: 'agriculture', label: 'Agriculture', icon: Leaf },
  { id: 'other', label: 'Other', icon: Briefcase },
];

const sizes = [
  { id: '1-10', label: '1-10 employees' },
  { id: '11-50', label: '11-50 employees' },
  { id: '51-200', label: '51-200 employees' },
  { id: '201-500', label: '201-500 employees' },
  { id: '500+', label: '500+ employees' },
];

export function Onboarding() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    personal: {
      fullName: user?.full_name || '',
      roleTitle: '',
    },
    organization: {
      name: '',
      industry: '',
      size: '',
      description: '',
    },
    invites: {
      emails: [''],
    },
  });

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // Check if already onboarded
  useEffect(() => {
    const checkStatus = async () => {
      const tokens = localStorage.getItem('tokens');
      if (!tokens) {
        navigate('/login');
        return;
      }

      const { access_token } = JSON.parse(tokens);

      try {
        const response = await fetch(`${API_URL}/api/onboarding/status`, {
          headers: { 'Authorization': `Bearer ${access_token}` },
        });

        if (response.ok) {
          const status = await response.json();
          if (status.is_complete) {
            navigate('/dashboard');
          }
        }
      } catch (error) {
        console.error('Failed to check onboarding status:', error);
      }
    };

    checkStatus();
  }, [navigate]);

  const saveStep = async (stepId: string) => {
    const tokens = localStorage.getItem('tokens');
    if (!tokens) return;

    const { access_token } = JSON.parse(tokens);

    try {
      let body = {};
      if (stepId === 'personal') {
        body = {
          full_name: formData.personal.fullName,
          role_title: formData.personal.roleTitle,
        };
      } else if (stepId === 'organization') {
        body = {
          name: formData.organization.name,
          industry: formData.organization.industry,
          size: formData.organization.size,
          description: formData.organization.description,
        };
      } else if (stepId === 'invite') {
        body = {
          invites: formData.invites.emails.filter(e => e).map(email => ({ email, role: 'viewer' })),
        };
      }

      const response = await fetch(`${API_URL}/api/onboarding/${stepId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `Failed to save ${stepId}`);
      }
    } catch (err) {
      throw err;
    }
  };

  const handleNext = async () => {
    setError('');
    setIsLoading(true);

    try {
      await saveStep(steps[currentStep].id);

      if (currentStep < steps.length - 1) {
        setCurrentStep(currentStep + 1);
      } else {
        // Complete onboarding
        const tokens = localStorage.getItem('tokens');
        if (!tokens) return;

        const { access_token } = JSON.parse(tokens);

        const response = await fetch(`${API_URL}/api/onboarding/complete`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${access_token}` },
        });

        if (response.ok) {
          navigate('/dashboard');
        } else {
          const error = await response.json();
          throw new Error(error.detail || 'Failed to complete onboarding');
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSkip = async () => {
    setIsLoading(true);
    const tokens = localStorage.getItem('tokens');
    if (!tokens) return;

    const { access_token } = JSON.parse(tokens);

    try {
      const response = await fetch(`${API_URL}/api/onboarding/skip`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${access_token}` },
      });

      if (response.ok) {
        navigate('/dashboard');
      }
    } catch (error) {
      console.error('Failed to skip onboarding:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const CurrentStepIcon = steps[currentStep].icon;

  return (
    <div className="min-h-screen bg-background-primary text-text-primary font-body blueprint-grid">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 h-16 bg-background-primary/85 backdrop-blur-xl border-b border-border-subtle z-50">
        <div className="max-w-4xl mx-auto px-4 h-full flex items-center justify-between">
          <span className="font-display text-lg font-semibold text-accent tracking-wider">
            STREAMWEAVE
          </span>
          <button
            onClick={handleSkip}
            disabled={isLoading}
            className="text-sm text-text-tertiary hover:text-text-primary transition-colors"
          >
            Skip for now
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="pt-24 pb-12 px-4">
        <div className="max-w-2xl mx-auto">
          {/* Progress Steps */}
          <div className="mb-8">
            <div className="flex items-center justify-between">
              {steps.map((step, index) => {
                const StepIcon = step.icon;
                const isActive = index === currentStep;
                const isCompleted = index < currentStep;

                return (
                  <div key={step.id} className="flex items-center">
                    <div className={`flex flex-col items-center ${isActive ? 'text-accent' : isCompleted ? 'text-green-400' : 'text-text-tertiary'}`}>
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center mb-2 ${
                        isActive ? 'bg-accent/20 border-2 border-accent' :
                        isCompleted ? 'bg-green-400/20 border-2 border-green-400' :
                        'bg-background-tertiary border-2 border-border-subtle'
                      }`}>
                        {isCompleted ? (
                          <CheckCircle2 className="w-5 h-5" />
                        ) : (
                          <StepIcon className="w-5 h-5" />
                        )}
                      </div>
                      <span className="text-xs font-medium">{step.title}</span>
                    </div>
                    {index < steps.length - 1 && (
                      <div className={`w-16 h-px mx-2 ${isCompleted ? 'bg-green-400' : 'bg-border-subtle'}`} />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Form Card */}
          <div className="bg-background-secondary border border-border-subtle rounded-lg p-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 rounded-lg bg-accent-dim flex items-center justify-center">
                <CurrentStepIcon className="w-6 h-6 text-accent" />
              </div>
              <div>
                <h1 className="text-xl font-semibold">{steps[currentStep].title}</h1>
                <p className="text-sm text-text-secondary">{steps[currentStep].description}</p>
              </div>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded text-red-400 text-sm">
                {error}
              </div>
            )}

            {/* Step Content */}
            {currentStep === 0 && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1.5">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={formData.personal.fullName}
                    onChange={(e) => setFormData({ ...formData, personal: { ...formData.personal, fullName: e.target.value } })}
                    className="w-full px-4 py-2.5 bg-background-tertiary border border-border-subtle rounded text-text-primary focus:outline-none focus:border-accent transition-all"
                    placeholder="Your full name"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1.5">
                    Role/Title (Optional)
                  </label>
                  <input
                    type="text"
                    value={formData.personal.roleTitle}
                    onChange={(e) => setFormData({ ...formData, personal: { ...formData.personal, roleTitle: e.target.value } })}
                    className="w-full px-4 py-2.5 bg-background-tertiary border border-border-subtle rounded text-text-primary focus:outline-none focus:border-accent transition-all"
                    placeholder="e.g., Product Manager"
                  />
                </div>
              </div>
            )}

            {currentStep === 1 && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1.5">
                    Organization Name
                  </label>
                  <input
                    type="text"
                    value={formData.organization.name}
                    onChange={(e) => setFormData({ ...formData, organization: { ...formData.organization, name: e.target.value } })}
                    className="w-full px-4 py-2.5 bg-background-tertiary border border-border-subtle rounded text-text-primary focus:outline-none focus:border-accent transition-all"
                    placeholder="Acme Inc."
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    Industry
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {industries.map((ind) => {
                      const Icon = ind.icon;
                      return (
                        <button
                          key={ind.id}
                          type="button"
                          onClick={() => setFormData({ ...formData, organization: { ...formData.organization, industry: ind.id } })}
                          className={`flex items-center gap-2 px-3 py-2 rounded border text-sm transition-all ${
                            formData.organization.industry === ind.id
                              ? 'bg-accent-dim border-accent text-accent'
                              : 'bg-background-tertiary border-border-subtle text-text-secondary hover:border-border-hover'
                          }`}
                        >
                          <Icon className="w-4 h-4" />
                          {ind.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    Organization Size
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {sizes.map((size) => (
                      <button
                        key={size.id}
                        type="button"
                        onClick={() => setFormData({ ...formData, organization: { ...formData.organization, size: size.id } })}
                        className={`px-4 py-2 rounded border text-sm transition-all ${
                          formData.organization.size === size.id
                            ? 'bg-accent-dim border-accent text-accent'
                            : 'bg-background-tertiary border-border-subtle text-text-secondary hover:border-border-hover'
                        }`}
                      >
                        {size.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {currentStep === 2 && (
              <div className="space-y-4">
                <div className="text-center py-8">
                  <Users className="w-16 h-16 mx-auto mb-4 text-accent opacity-50" />
                  <h3 className="text-lg font-medium mb-2">Invite your team (Optional)</h3>
                  <p className="text-sm text-text-secondary max-w-sm mx-auto">
                    You can invite team members now or skip this step and invite them later from your organization settings.
                  </p>
                </div>

                {formData.invites.emails.map((email, index) => (
                  <div key={index} className="flex gap-2">
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => {
                        const newEmails = [...formData.invites.emails];
                        newEmails[index] = e.target.value;
                        setFormData({ ...formData, invites: { emails: newEmails } });
                      }}
                      className="flex-1 px-4 py-2.5 bg-background-tertiary border border-border-subtle rounded text-text-primary focus:outline-none focus:border-accent transition-all"
                      placeholder="colleague@example.com"
                    />
                    {index > 0 && (
                      <button
                        type="button"
                        onClick={() => {
                          const newEmails = formData.invites.emails.filter((_, i) => i !== index);
                          setFormData({ ...formData, invites: { emails: newEmails } });
                        }}
                        className="px-3 py-2 text-red-400 hover:text-red-300"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ))}

                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, invites: { emails: [...formData.invites.emails, ''] } })}
                  className="text-sm text-accent hover:text-accent-hover"
                >
                  + Add another email
                </button>
              </div>
            )}

            {/* Navigation */}
            <div className="flex items-center justify-between mt-8 pt-6 border-t border-border-subtle">
              <button
                type="button"
                onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
                disabled={currentStep === 0 || isLoading}
                className="px-4 py-2 text-text-secondary hover:text-text-primary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Back
              </button>

              <button
                type="button"
                onClick={handleNext}
                disabled={isLoading}
                className="px-6 py-2.5 bg-accent text-background-primary font-semibold rounded flex items-center gap-2 hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : currentStep === steps.length - 1 ? (
                  <>
                    Complete
                    <Sparkles className="w-4 h-4" />
                  </>
                ) : (
                  <>
                    Continue
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Footer */}
          <p className="text-center text-xs text-text-tertiary mt-8">
            Built with 💙 by{' '}
            <a
              href="https://tanoshii-computing.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent hover:text-accent-hover"
            >
              Tanoshii Computing
            </a>
          </p>
        </div>
      </main>
    </div>
  );
}
