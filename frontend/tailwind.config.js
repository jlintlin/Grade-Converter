/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [
    require('daisyui'),
  ],
  daisyui: {
    themes: [
      {
        light: {
          "primary": "#2563eb",
          "primary-content": "#ffffff",
          "secondary": "#0f766e",
          "secondary-content": "#ffffff",
          "accent": "#f59e0b",
          "accent-content": "#0f172a",
          "neutral": "#0f172a",
          "neutral-content": "#e2e8f0",
          "base-100": "#ffffff",
          "base-200": "#f1f5f9",
          "base-300": "#e2e8f0",
          "base-content": "#0f172a",
          "info": "#0ea5e9",
          "success": "#16a34a",
          "warning": "#f59e0b",
          "error": "#ef4444",
          "--rounded-box": "0.9rem",
          "--rounded-btn": "0.6rem",
        },
      },
      "dark"
    ],
    darkTheme: "dark",
    base: true,
    styled: true,
    utils: true,
    logs: false,
  },
}
