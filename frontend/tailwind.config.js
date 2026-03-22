/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx,vue}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#059669', // Emerald-600
        }
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
