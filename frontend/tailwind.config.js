/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./contexts/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
          950: "#172554",
        },
        dark: {
          900: "#0b0f19",
          950: "#060911",
          card: "#111827",
          border: "#1f2937",
        },
        risk: {
          low: "#10b981",       // Emerald Green
          medium: "#f59e0b",    // Amber
          high: "#f97316",      // Orange
          critical: "#ef4444",  // Rose Red
        },
      },
      boxShadow: {
        'glow': '0 0 20px -3px rgba(59, 130, 246, 0.4)',
        'glow-lg': '0 0 35px -5px rgba(59, 130, 246, 0.5)',
        'glow-emerald': '0 0 20px -3px rgba(16, 185, 129, 0.4)',
        'glow-rose': '0 0 20px -3px rgba(239, 68, 68, 0.5)',
        'glow-amber': '0 0 20px -3px rgba(245, 158, 11, 0.4)',
        'glow-purple': '0 0 20px -3px rgba(168, 85, 247, 0.4)',
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'card-hover': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
      },
      keyframes: {
        'pulse-subtle': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        'radar-ping': {
          '0%': { transform: 'scale(0.8)', opacity: '0.8' },
          '100%': { transform: 'scale(2.2)', opacity: '0' },
        },
        'shimmer': {
          '100%': { transform: 'translateX(100%)' },
        },
        'gradient-x': {
          '0%, 100%': {
            'background-size': '200% 200%',
            'background-position': 'left center',
          },
          '50%': {
            'background-size': '200% 200%',
            'background-position': 'right center',
          },
        },
      },
      animation: {
        'pulse-subtle': 'pulse-subtle 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'radar-ping': 'radar-ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
        'shimmer': 'shimmer 2.5s infinite',
        'gradient-x': 'gradient-x 6s ease infinite',
      },
    },
  },
  plugins: [],
};

