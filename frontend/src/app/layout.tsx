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
      { url: "/brand/logos/dclaw-icon-purple.svg", type: "image/svg+xml" },
    ],
    shortcut: "/brand/logos/dclaw-icon-purple.svg",
    apple: "/brand/logos/dclaw-icon-purple.svg",
  },
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
