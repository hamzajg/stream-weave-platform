import { Github, Twitter, Linkedin } from 'lucide-react';

export function Footer() {
  const currentYear = new Date().getFullYear();

  const footerLinks = {
    product: [
      { name: 'Features', href: '#features' },
      { name: 'Pricing', href: '#pricing' },
      { name: 'Documentation', href: '#docs' },
      { name: 'API Reference', href: '#api' },
    ],
    company: [
      { name: 'About', href: '#about' },
      { name: 'Blog', href: '#blog' },
      { name: 'Careers', href: '#careers' },
      { name: 'Contact', href: '#contact' },
    ],
    legal: [
      { name: 'Privacy', href: '#privacy' },
      { name: 'Terms', href: '#terms' },
      { name: 'Security', href: '#security' },
    ],
  };

  return (
    <footer className="border-t border-border-subtle bg-background-secondary">
      <div className="max-w-[1200px] mx-auto px-4 md:px-6 py-12 md:py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <a href="/" className="inline-block mb-4">
              <span className="font-display text-base font-semibold text-accent tracking-wider">
                STREAMWEAVE
              </span>
            </a>
            <p className="font-body text-sm text-text-secondary mb-6 max-w-[280px]">
              AI Agentic Workflow Platform for enterprise business automation.
            </p>
            {/* Social Links */}
            <div className="flex items-center gap-3">
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="w-10 h-10 rounded-md bg-background-tertiary flex items-center justify-center text-text-secondary transition-all duration-200 hover:text-text-primary hover:bg-background-elevated min-h-[44px] min-w-[44px] focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
                aria-label="GitHub"
              >
                <Github className="w-5 h-5" />
              </a>
              <a
                href="https://twitter.com"
                target="_blank"
                rel="noopener noreferrer"
                className="w-10 h-10 rounded-md bg-background-tertiary flex items-center justify-center text-text-secondary transition-all duration-200 hover:text-text-primary hover:bg-background-elevated min-h-[44px] min-w-[44px] focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
                aria-label="Twitter"
              >
                <Twitter className="w-5 h-5" />
              </a>
              <a
                href="https://linkedin.com"
                target="_blank"
                rel="noopener noreferrer"
                className="w-10 h-10 rounded-md bg-background-tertiary flex items-center justify-center text-text-secondary transition-all duration-200 hover:text-text-primary hover:bg-background-elevated min-h-[44px] min-w-[44px] focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
                aria-label="LinkedIn"
              >
                <Linkedin className="w-5 h-5" />
              </a>
            </div>
          </div>

          {/* Product Links */}
          <div>
            <h4 className="font-body text-sm font-semibold text-text-primary uppercase tracking-wider mb-4">
              Product
            </h4>
            <ul className="space-y-3">
              {footerLinks.product.map((link) => (
                <li key={link.name}>
                  <a
                    href={link.href}
                    className="font-body text-sm text-text-secondary transition-colors duration-200 hover:text-text-primary focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
                  >
                    {link.name}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Company Links */}
          <div>
            <h4 className="font-body text-sm font-semibold text-text-primary uppercase tracking-wider mb-4">
              Company
            </h4>
            <ul className="space-y-3">
              {footerLinks.company.map((link) => (
                <li key={link.name}>
                  <a
                    href={link.href}
                    className="font-body text-sm text-text-secondary transition-colors duration-200 hover:text-text-primary focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
                  >
                    {link.name}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal Links */}
          <div>
            <h4 className="font-body text-sm font-semibold text-text-primary uppercase tracking-wider mb-4">
              Legal
            </h4>
            <ul className="space-y-3">
              {footerLinks.legal.map((link) => (
                <li key={link.name}>
                  <a
                    href={link.href}
                    className="font-body text-sm text-text-secondary transition-colors duration-200 hover:text-text-primary focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
                  >
                    {link.name}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-border-subtle flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="font-body text-sm text-text-tertiary">
            © {currentYear} StreamWeave Platform. All rights reserved.
          </p>
          <p className="font-body text-xs text-text-tertiary">
            Built for enterprise AI automation
          </p>
        </div>
      </div>
    </footer>
  );
}
