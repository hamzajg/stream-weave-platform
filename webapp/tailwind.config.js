/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          primary: '#0c1220',
          secondary: '#121b2e',
          tertiary: '#1a2640',
          elevated: '#1f2d45',
        },
        border: {
          subtle: 'rgba(100, 180, 255, 0.12)',
          DEFAULT: 'rgba(100, 180, 255, 0.20)',
          hover: 'rgba(0, 212, 255, 0.25)',
          focus: 'rgba(0, 212, 255, 0.60)',
        },
        text: {
          primary: '#f0f4f8',
          secondary: '#a8b8c8',
          tertiary: '#7a8a9a',
          disabled: '#5a6a7a',
        },
        accent: {
          DEFAULT: '#00d4ff',
          dim: 'rgba(0, 212, 255, 0.10)',
          glow: 'rgba(0, 212, 255, 0.25)',
          hover: '#33ddff',
        },
        success: '#10b981',
        warning: '#ff7a4d',
        danger: '#f04d4d',
      },
      fontFamily: {
        display: ['Orbitron', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        sm: '4px',
        md: '8px',
        lg: '12px',
        xl: '16px',
      },
      animation: {
        'shimmer': 'shimmer 1.5s infinite',
        'spin-slow': 'spin 0.8s linear infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
      },
    },
  },
  plugins: [],
}
