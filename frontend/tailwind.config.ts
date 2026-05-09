import type { Config } from "tailwindcss";

/**
 * Light-mode only. Brand tokens live in src/styles/brand.css and are
 * exposed as `--dk-*` CSS variables; shadcn-style HSL tokens in
 * src/app/globals.css are remapped to those brand colors.
 */
const config: Config = {
  // Light-mode only. We keep `class` strategy but never add `.dark` anywhere.
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // Direct brand-token aliases (use these for new code instead of
        // the shadcn-shaped tokens above when convenient).
        brand: {
          DEFAULT: "var(--dk-purple-700)",
          50: "var(--dk-purple-50)",
          100: "var(--dk-purple-100)",
          200: "var(--dk-purple-200)",
          300: "var(--dk-purple-300)",
          400: "var(--dk-purple-400)",
          500: "var(--dk-purple-500)",
          600: "var(--dk-purple-600)",
          700: "var(--dk-purple-700)",
          800: "var(--dk-purple-800)",
          900: "var(--dk-purple-900)",
        },
        ink: "var(--dk-ink)",
        success: "var(--dk-success)",
        warning: "var(--dk-warning)",
        danger: "var(--dk-danger)",
        info: "var(--dk-info)",
      },
      fontFamily: {
        sans: ["var(--dk-font-sans)"],
        display: ["var(--dk-font-display)"],
        mono: ["var(--dk-font-mono)"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xl: "var(--dk-radius-xl)",
        "2xl": "var(--dk-radius-2xl)",
        pill: "var(--dk-radius-pill)",
      },
      boxShadow: {
        xs: "var(--dk-shadow-xs)",
        sm: "var(--dk-shadow-sm)",
        md: "var(--dk-shadow-md)",
        lg: "var(--dk-shadow-lg)",
        brand: "var(--dk-shadow-brand)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
