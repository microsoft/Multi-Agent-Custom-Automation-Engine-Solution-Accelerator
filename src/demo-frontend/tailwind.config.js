/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dynamic branding colors will be injected via CSS variables
        primary: "var(--color-primary, #2563eb)",
        "primary-dark": "var(--color-primary-dark, #1d4ed8)",
        secondary: "var(--color-secondary, #64748b)",
        accent: "var(--color-accent, #10b981)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
