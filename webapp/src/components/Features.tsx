import { Workflow, Bot, Shield, Zap, Layers, Globe } from 'lucide-react';

const features = [
  {
    icon: Workflow,
    title: 'Visual Workflow Builder',
    description: 'Design complex AI workflows with our intuitive drag-and-drop interface. No coding required.',
  },
  {
    icon: Bot,
    title: 'AI Agent Orchestration',
    description: 'Deploy and manage multiple AI agents that work together to automate your business processes.',
  },
  {
    icon: Shield,
    title: 'Enterprise Security',
    description: 'Built for enterprise with role-based access control, audit logs, and data isolation.',
  },
  {
    icon: Zap,
    title: 'Real-time Execution',
    description: 'Monitor workflow execution in real-time with live streaming and instant feedback.',
  },
  {
    icon: Layers,
    title: 'Industry Templates',
    description: 'Get started quickly with pre-built templates for manufacturing, finance, healthcare, and more.',
  },
  {
    icon: Globe,
    title: 'AutoGen Studio Integration',
    description: 'Seamlessly integrate with Microsoft AutoGen Studio for advanced AI agent capabilities.',
  },
];

export function Features() {
  return (
    <section id="features" className="relative py-24 md:py-32">
      <div className="max-w-[1200px] mx-auto px-4 md:px-6">
        {/* Section Header */}
        <div className="text-center mb-16 md:mb-20">
          <h2 className="font-body text-3xl md:text-4xl font-bold text-text-primary mb-4">
            Everything You Need to{' '}
            <span className="text-accent">Automate</span>
          </h2>
          <p className="font-body text-lg text-text-secondary max-w-[600px] mx-auto">
            A complete platform for building, deploying, and managing AI-powered 
            business workflows across any industry.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <div
              key={index}
              className="group bg-background-secondary border border-border-subtle rounded-lg p-6 transition-all duration-200 hover:border-border-hover hover:bg-background-tertiary hover:-translate-y-0.5 hover:shadow-[0_4px_20px_rgba(0,0,0,0.2)] focus-within:border-accent focus-within:shadow-[0_0_0_3px_rgba(0,212,255,0.10)]"
              tabIndex={0}
            >
              {/* Icon */}
              <div className="w-12 h-12 rounded-md bg-accent-dim flex items-center justify-center mb-4 transition-all duration-200 group-hover:shadow-[0_0_20px_rgba(0,212,255,0.2)]">
                <feature.icon className="w-6 h-6 text-accent" />
              </div>

              {/* Title */}
              <h3 className="font-body text-lg font-semibold text-text-primary mb-2">
                {feature.title}
              </h3>

              {/* Description */}
              <p className="font-body text-sm text-text-secondary leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
