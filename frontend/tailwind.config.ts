import type { Config } from "tailwindcss";

/**
 * Tailwind config bound to the DClaw design-kit tokens.
 *
 * The single source of truth for tokens is `src/styles/brand.css` (CSS
 * custom properties prefixed `--dk-*`, where `dk` = "design kit"). This
 * config exposes them as Tailwind utilities so you can write
 * `bg-brand`, `text-fg-1`, `border-brand-soft`, `shadow-brand`,
 * `rounded-pill`, `ease-out-quart` etc. and they resolve to the token
 * values.
 *
 * Light mode only — never add a `.dark` class anywhere in the app.
 *
 * Conventions:
 * - Prefer semantic aliases (`bg-bg`, `text-fg-1`, `border-brand`)
 *   over raw palette (`bg-purple-700`, `text-gray-700`).
 * - shadcn-shaped HSL tokens are still wired in `globals.css` for
 *   compatibility with the existing UI primitives in `components/ui/`.
 *   New components should use the direct brand aliases below.
 */
const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "var(--dk-container-pad)",
      screens: {
        "2xl": "var(--dk-container-max)",
      },
    },
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

        brand: {
          DEFAULT: "var(--dk-purple-700)",
          hover: "var(--dk-purple-800)",
          press: "var(--dk-purple-900)",
          soft: "var(--dk-purple-100)",
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
        gray: {
          50: "var(--dk-gray-50)",
          100: "var(--dk-gray-100)",
          200: "var(--dk-gray-200)",
          300: "var(--dk-gray-300)",
          400: "var(--dk-gray-400)",
          500: "var(--dk-gray-500)",
          600: "var(--dk-gray-600)",
          700: "var(--dk-gray-700)",
          800: "var(--dk-gray-800)",
          900: "var(--dk-gray-900)",
        },

        bg: {
          DEFAULT: "var(--dk-bg)",
          muted: "var(--dk-bg-muted)",
          tint: "var(--dk-bg-tint)",
          inverse: "var(--dk-bg-inverse)",
        },
        fg: {
          DEFAULT: "var(--dk-fg)",
          1: "var(--dk-fg-1)",
          2: "var(--dk-fg-2)",
          muted: "var(--dk-fg-muted)",
          "on-brand": "var(--dk-fg-on-brand)",
          inverse: "var(--dk-fg-inverse)",
        },
        "border-strong": "var(--dk-border-strong)",
        "border-brand": "var(--dk-border-brand)",

        success: {
          DEFAULT: "var(--dk-success)",
          bg: "var(--dk-success-bg)",
        },
        warning: {
          DEFAULT: "var(--dk-warning)",
          bg: "var(--dk-warning-bg)",
        },
        danger: {
          DEFAULT: "var(--dk-danger)",
          bg: "var(--dk-danger-bg)",
        },
        info: {
          DEFAULT: "var(--dk-info)",
          bg: "var(--dk-info-bg)",
        },
      },

      fontFamily: {
        sans: ["var(--dk-font-sans)"],
        display: ["var(--dk-font-display)"],
        mono: ["var(--dk-font-mono)"],
      },
      fontSize: {
        xs: ["var(--dk-text-xs)", { lineHeight: "var(--dk-lh-normal)" }],
        sm: ["var(--dk-text-sm)", { lineHeight: "var(--dk-lh-normal)" }],
        md: ["var(--dk-text-md)", { lineHeight: "var(--dk-lh-relaxed)" }],
        base: ["var(--dk-text-md)", { lineHeight: "var(--dk-lh-relaxed)" }],
        lg: ["var(--dk-text-lg)", { lineHeight: "var(--dk-lh-relaxed)" }],
        xl: ["var(--dk-text-xl)", { lineHeight: "var(--dk-lh-relaxed)" }],
        "2xl": ["var(--dk-text-2xl)", { lineHeight: "var(--dk-lh-snug)" }],
        "3xl": ["var(--dk-text-3xl)", { lineHeight: "var(--dk-lh-snug)" }],
        "4xl": ["var(--dk-text-4xl)", { lineHeight: "var(--dk-lh-snug)" }],
        "5xl": ["var(--dk-text-5xl)", { lineHeight: "var(--dk-lh-snug)" }],
        "6xl": ["var(--dk-text-6xl)", { lineHeight: "var(--dk-lh-tight)" }],
        "7xl": ["var(--dk-text-7xl)", { lineHeight: "var(--dk-lh-tight)" }],
      },
      letterSpacing: {
        tight: "var(--dk-tracking-tight)",
        snug: "var(--dk-tracking-snug)",
        wide: "var(--dk-tracking-wide)",
      },
      lineHeight: {
        tight: "var(--dk-lh-tight)",
        snug: "var(--dk-lh-snug)",
        normal: "var(--dk-lh-normal)",
        relaxed: "var(--dk-lh-relaxed)",
      },
      fontWeight: {
        regular: "400",
        medium: "500",
        semibold: "600",
        bold: "700",
        black: "800",
      },

      spacing: {
        section: "var(--dk-space-24)",
        "section-lg": "var(--dk-space-32)",
      },
      maxWidth: {
        container: "var(--dk-container-max)",
      },

      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xs: "var(--dk-radius-xs)",
        "dk-sm": "var(--dk-radius-sm)",
        "dk-md": "var(--dk-radius-md)",
        "dk-lg": "var(--dk-radius-lg)",
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

      transitionTimingFunction: {
        "out-quart": "var(--dk-ease-out)",
        "in-out-quart": "var(--dk-ease-in-out)",
      },
      transitionDuration: {
        fast: "var(--dk-dur-fast)",
        base: "var(--dk-dur-base)",
        slow: "var(--dk-dur-slow)",
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
        "scroll-in": {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down var(--dk-dur-base) var(--dk-ease-out)",
        "accordion-up": "accordion-up var(--dk-dur-base) var(--dk-ease-out)",
        "scroll-in": "scroll-in var(--dk-dur-slow) var(--dk-ease-out) both",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
