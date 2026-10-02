import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/layout/ThemeProvider";

// Intentionally not using next/font/google: it requires a build-time fetch
// to fonts.googleapis.com, which fails in network-restricted CI/CD and
// sandboxed build environments. A high-quality native system stack (see
// --font-inter / --font-mono in tailwind.config.ts and globals.css) renders
// identically fast with zero external dependency and no layout shift.

export const metadata: Metadata = {
  title: "Matching Engine — Clinical Trial Matching Platform",
  description:
    "Multi-agent clinical trial eligibility matching, calibrated confidence scoring, and ML-driven retention insight for oncology trial navigation.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans text-foreground antialiased">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
