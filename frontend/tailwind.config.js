/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx,vue}",
  ],
  theme: {
    extend: {
      colors: {
        "primary-container": "#dcfce7",
        "surface-bright": "#f0fdf4",
        "on-tertiary-fixed-variant": "#334f00",
        "inverse-surface": "#0f172a",
        "on-primary-fixed": "#002117",
        "on-primary-fixed-variant": "#0b513d",
        "surface-container-lowest": "#ffffff",
        "on-tertiary-fixed": "#121f00",
        "on-primary-container": "#064e3b",
        "secondary-fixed": "#10b981",
        "on-surface": "#064e3b",
        "error-container": "#fee2e2",
        "on-tertiary": "#213600",
        "surface-container-low": "#ecfdf5",
        "inverse-primary": "#2b6954",
        "tertiary": "#65a30d",
        "surface-container-highest": "#d1fae5",
        "on-tertiary-container": "#3f6212",
        "surface-tint": "#059669",
        "on-error-container": "#991b1b",
        "primary-fixed-dim": "#95d3ba",
        "on-secondary-fixed-variant": "#304f00",
        "tertiary-fixed": "#bef264",
        "secondary-container": "#10b981",
        "primary": "#065f46",
        "tertiary-container": "#f7fee7",
        "on-primary": "#ffffff",
        "on-secondary": "#ffffff",
        "outline": "#a3b1a9",
        "surface-container-high": "#d1fae5",
        "primary-fixed": "#b0f0d6",
        "outline-variant": "#cbd5e1",
        "on-error": "#ffffff",
        "surface": "#f0fdf4",
        "on-background": "#064e3b",
        "background": "#d1fae5",
        "surface-container": "#f0fdf4",
        "secondary-fixed-dim": "#059669",
        "secondary": "#059669",
        "error": "#dc2626",
        "on-surface-variant": "#334155",
        "inverse-on-surface": "#f8fafc",
        "on-secondary-fixed": "#102000",
        "on-secondary-container": "#064e3b",
        "tertiary-fixed-dim": "#98da27",
        "surface-variant": "#f1f5f9",
        "surface-dim": "#f8fafc"
      },
      borderRadius: {
        "DEFAULT": "0.125rem",
        "lg": "0.25rem",
        "xl": "0.5rem",
        "full": "0.75rem"
      },
      fontFamily: {
        "headline": ["Space Grotesk"],
        "body": ["Inter"],
        "label": ["Inter"],
        "inter": ["Inter"],
        "sans": ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"]
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography')
  ],
}
