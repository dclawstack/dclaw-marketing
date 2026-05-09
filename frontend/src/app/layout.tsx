import type { Metadata } from "next";
import Link from "next/link";
import { Poppins } from "next/font/google";
import "./globals.css";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
  variable: "--font-poppins",
  display: "swap",
});

export const metadata: Metadata = {
  title: "DClaw Marketing",
  description: "DClaw Marketing Application",
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
        <nav className="border-b border-border bg-background">
          <div className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3">
            <Link href="/" className="text-lg font-bold text-ink">
              DClaw Marketing
            </Link>
            <div className="flex gap-4 text-sm">
              <Link href="/" className="text-muted-foreground hover:text-ink">
                Dashboard
              </Link>
              <Link href="/campaigns" className="text-muted-foreground hover:text-ink">
                Campaigns
              </Link>
              <Link href="/leads" className="text-muted-foreground hover:text-ink">
                Leads
              </Link>
            </div>
          </div>
        </nav>
        <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
