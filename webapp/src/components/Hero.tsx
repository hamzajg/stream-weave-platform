import { ArrowRight, Sparkles } from 'lucide-react';

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center pt-16 overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-accent-dim/20 via-transparent to-transparent pointer-events-none" />
      
      {/* Decorative elements */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent/10 rounded-full blur-[128px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-accent/5 rounded-full blur-[96px] pointer-events-none" />

      <div className="relative z-10 max-w-[900px] mx-auto px-4 md:px-6 py-20 md:py-32 text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-background-secondary border border-border-subtle mb-8">
          <Sparkles className="w-4 h-4 text-accent" />
          <span className="font-body text-sm font-medium text-text-secondary">
            AI Agentic Workflow Platform
          </span>
        </div>

        {/* Main Headline */}
        <h1 className="font-body text-4xl sm:text-5xl md:text-6xl font-bold text-text-primary leading-tight tracking-tight mb-6">
          Transform Your Business with{' '}
          <span className="text-accent">AI-Powered</span>{' '}
          Workflows
        </h1>

        {/* Subheadline */}
        <p className="font-body text-lg md:text-xl text-text-secondary max-w-[680px] mx-auto mb-10 leading-relaxed">
          StreamWeave empowers business specialists across manufacturing, finance, 
          healthcare, and more to build, deploy, and manage AI agentic workflows 
          without writing code.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <a
            href="#get-started"
            className="group font-body text-base font-semibold bg-accent text-background-primary px-8 py-4 rounded-sm min-h-[56px] min-w-[200px] flex items-center justify-center gap-2 transition-all duration-200 hover:bg-accent-hover hover:shadow-[0_0_30px_rgba(0,212,255,0.3)] focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 focus-visible:shadow-[0_0_0_4px_rgba(0,212,255,0.10)]"
          >
            Start Building
            <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
          </a>
          
          <a
            href="#features"
            className="font-body text-base font-semibold text-accent bg-transparent border border-accent px-8 py-4 rounded-sm min-h-[56px] min-w-[200px] flex items-center justify-center transition-all duration-200 hover:bg-accent-dim focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
          >
            Learn More
          </a>
        </div>

        {/* Trust indicators */}
        <div className="mt-16 pt-8 border-t border-border-subtle">
          <p className="font-body text-sm text-text-tertiary uppercase tracking-wider mb-6">
            Trusted by teams across industries
          </p>
          <div className="flex flex-wrap items-center justify-center gap-8 md:gap-12 opacity-50">
            {['Manufacturing', 'Finance', 'Healthcare', 'Insurance', 'Ecommerce'].map((industry) => (
              <span
                key={industry}
                className="font-body text-sm font-medium text-text-secondary"
              >
                {industry}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
