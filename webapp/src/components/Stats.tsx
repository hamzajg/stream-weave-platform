import { Users, Workflow, Zap, Globe } from 'lucide-react';

const stats = [
  {
    icon: Users,
    value: '10K+',
    label: 'Active Users',
    description: 'Business specialists worldwide',
  },
  {
    icon: Workflow,
    value: '50K+',
    label: 'Workflows Created',
    description: 'AI agentic automations',
  },
  {
    icon: Zap,
    value: '1M+',
    label: 'Tasks Executed',
    description: 'Automated with AI agents',
  },
  {
    icon: Globe,
    value: '7',
    label: 'Industries',
    description: 'Manufacturing, Finance, Healthcare & more',
  },
];

export function Stats() {
  return (
    <section className="relative py-20 md:py-28 border-y border-border-subtle">
      {/* Subtle gradient background */}
      <div className="absolute inset-0 bg-gradient-to-r from-accent-dim/10 via-transparent to-accent-dim/10 pointer-events-none" />

      <div className="relative z-10 max-w-[1200px] mx-auto px-4 md:px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
          {stats.map((stat, index) => (
            <div key={index} className="text-center">
              <div className="w-12 h-12 mx-auto mb-4 rounded-md bg-accent-dim flex items-center justify-center">
                <stat.icon className="w-6 h-6 text-accent" />
              </div>
              <div className="font-body text-3xl md:text-4xl font-bold text-accent mb-1">
                {stat.value}
              </div>
              <div className="font-body text-sm font-semibold text-text-primary mb-1">
                {stat.label}
              </div>
              <div className="font-body text-xs text-text-tertiary">
                {stat.description}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
