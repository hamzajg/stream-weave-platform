import { MessageCircle, BookOpen, Github, ExternalLink } from 'lucide-react';

const communityLinks = [
  {
    icon: MessageCircle,
    title: 'Join the Community',
    description: 'Connect with other StreamWeave users, share workflows, and get help from the team.',
    href: 'https://tanoshii-computing.com/community',
    label: 'Join Discord',
    external: true,
  },
  {
    icon: BookOpen,
    title: 'Documentation',
    description: 'Comprehensive guides, API references, and tutorials to help you get started.',
    href: '#docs',
    label: 'Read Docs',
    external: false,
  },
  {
    icon: Github,
    title: 'Open Source',
    description: 'StreamWeave is built in the open. Contribute, report issues, or star the project.',
    href: 'https://github.com/tanoshii-computing/stream-weave-platform',
    label: 'View on GitHub',
    external: true,
  },
];

export function Community() {
  return (
    <section className="relative py-24 md:py-32">
      <div className="relative z-10 max-w-[1200px] mx-auto px-4 md:px-6">
        {/* Section Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-background-secondary border border-border-subtle mb-6">
            <span className="font-body text-sm font-medium text-text-secondary">
              Built by Tanoshii Computing
            </span>
          </div>
          <h2 className="font-body text-3xl md:text-4xl font-bold text-text-primary mb-4">
            Join the <span className="text-accent">Community</span>
          </h2>
          <p className="font-body text-lg text-text-secondary max-w-[600px] mx-auto">
            Be part of a growing community of business specialists transforming 
            their operations with AI-powered workflows.
          </p>
        </div>

        {/* Community Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {communityLinks.map((link, index) => (
            <a
              key={index}
              href={link.href}
              target={link.external ? '_blank' : undefined}
              rel={link.external ? 'noopener noreferrer' : undefined}
              className="group bg-background-secondary border border-border-subtle rounded-lg p-6 transition-all duration-200 hover:border-border-hover hover:bg-background-tertiary hover:-translate-y-0.5 hover:shadow-[0_4px_20px_rgba(0,0,0,0.2)] focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
            >
              {/* Icon */}
              <div className="w-12 h-12 rounded-md bg-accent-dim flex items-center justify-center mb-4 transition-all duration-200 group-hover:shadow-[0_0_20px_rgba(0,212,255,0.2)]">
                <link.icon className="w-6 h-6 text-accent" />
              </div>

              {/* Title */}
              <h3 className="font-body text-lg font-semibold text-text-primary mb-2 flex items-center gap-2">
                {link.title}
                {link.external && <ExternalLink className="w-4 h-4 text-text-tertiary" />}
              </h3>

              {/* Description */}
              <p className="font-body text-sm text-text-secondary leading-relaxed mb-4">
                {link.description}
              </p>

              {/* Link */}
              <span className="font-body text-sm font-semibold text-accent group-hover:text-accent-hover transition-colors">
                {link.label} →
              </span>
            </a>
          ))}
        </div>

        {/* Tanoshii Computing Attribution */}
        <div className="mt-16 pt-8 border-t border-border-subtle text-center">
          <p className="font-body text-sm text-text-tertiary mb-2">
            Proudly built by
          </p>
          <a
            href="https://tanoshii-computing.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 font-display text-lg font-semibold text-accent tracking-wider hover:text-accent-hover transition-colors focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-4"
          >
            TANOSHII COMPUTING
            <ExternalLink className="w-4 h-4" />
          </a>
          <p className="font-body text-xs text-text-tertiary mt-2 max-w-[400px] mx-auto">
            Empowering enterprises with AI automation solutions. 
            Visit tanoshii-computing.com to learn more about our products and services.
          </p>
        </div>
      </div>
    </section>
  );
}
