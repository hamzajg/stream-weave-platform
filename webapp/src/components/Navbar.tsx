import { Menu, X } from 'lucide-react';
import { useState } from 'react';

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { name: 'Features', href: '#features' },
    { name: 'Solutions', href: '#solutions' },
    { name: 'Documentation', href: '#docs' },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-16 md:h-16 bg-background-primary/85 backdrop-blur-[16px] backdrop-saturate-[180%] border-b border-border-subtle">
      <div className="max-w-[1280px] mx-auto px-4 md:px-6 h-full flex items-center justify-between">
        {/* Brand */}
        <a href="/" className="flex items-center gap-2 no-underline">
          <span className="font-display text-lg font-semibold text-accent tracking-wider">
            STREAMWEAVE
          </span>
          <span className="hidden sm:block font-body text-xs font-medium text-text-tertiary uppercase tracking-widest">
            Platform
          </span>
        </a>

        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center gap-2">
          {navLinks.map((link) => (
            <a
              key={link.name}
              href={link.href}
              className="font-body text-sm font-medium text-text-secondary px-4 py-2.5 rounded-sm min-h-[44px] flex items-center transition-all duration-200 hover:text-text-primary hover:bg-background-tertiary focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
            >
              {link.name}
            </a>
          ))}
        </div>

        {/* CTA Button */}
        <div className="flex items-center gap-4">
          <a
            href="#get-started"
            className="hidden md:flex font-body text-sm font-semibold bg-accent text-background-primary px-5 py-2.5 rounded-sm min-h-[44px] items-center transition-all duration-200 hover:bg-accent-hover hover:shadow-[0_0_20px_rgba(0,212,255,0.25)] focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 focus-visible:shadow-[0_0_0_4px_rgba(0,212,255,0.10)]"
          >
            Get Started
          </a>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 text-text-secondary hover:text-text-primary min-h-[44px] min-w-[44px] flex items-center justify-center rounded-sm transition-colors focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden absolute top-16 left-0 right-0 bg-background-secondary border-b border-border-subtle py-4 px-4">
          <div className="flex flex-col gap-2">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="font-body text-sm font-medium text-text-secondary px-4 py-3 rounded-md min-h-[44px] flex items-center transition-all duration-200 hover:text-text-primary hover:bg-background-tertiary"
              >
                {link.name}
              </a>
            ))}
            <a
              href="#get-started"
              onClick={() => setMobileMenuOpen(false)}
              className="font-body text-sm font-semibold bg-accent text-background-primary px-4 py-3 rounded-md min-h-[44px] flex items-center justify-center mt-2 transition-all duration-200 hover:bg-accent-hover"
            >
              Get Started
            </a>
          </div>
        </div>
      )}
    </nav>
  );
}
