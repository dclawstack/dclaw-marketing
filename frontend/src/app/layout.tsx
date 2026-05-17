import type { Metadata } from "next";
import { Poppins } from "next/font/google";

import { AuthGuard } from "@/components/auth-guard";
import { AppShell } from "@/components/app-shell";
import { AuthProvider } from "@/contexts/auth-context";
import { OrgProvider } from "@/contexts/org-context";

import "./globals.css";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
  variable: "--font-poppins",
  display: "swap",
});

export const metadata: Metadata = {
  title: "DClaw Marketing",
  description: "Agent-driven marketing operating system",
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
    ],
    shortcut: "/favicon.png",
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
    other: [
      { rel: "icon", type: "image/png", sizes: "192x192", url: "/android-chrome-192x192.png" },
      { rel: "icon", type: "image/png", sizes: "512x512", url: "/android-chrome-512x512.png" },
    ],
  },
  manifest: "/site.webmanifest",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={poppins.variable}>
      <body
        className="min-h-screen bg-background font-sans text-foreground"
        style={{ fontFamily: "var(--font-poppins), var(--dk-font-sans)" }}
      >
        <AuthProvider>
          <OrgProvider>
            <AuthGuard>
              <AppShell>{children}</AppShell>
            </AuthGuard>
          </OrgProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
