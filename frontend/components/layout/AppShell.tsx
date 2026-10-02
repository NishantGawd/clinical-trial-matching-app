"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Moon, Sun, Stethoscope, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS, APP_NAME } from "@/lib/constants";
import { useHealthCheck } from "@/hooks/useHealthCheck";
import { useTheme } from "@/components/layout/ThemeProvider";
import { ComplianceBanner } from "@/components/layout/ComplianceBanner";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

function relativeTime(date: Date | null): string {
  if (!date) return "";
  const seconds = Math.round((Date.now() - date.getTime()) / 1000);
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  return `${minutes}m ago`;
}

function SystemStatusPill() {
  const { state, lastChecked } = useHealthCheck();

  const tone = state === "online" ? "bg-teal-500" : state === "offline" ? "bg-rose-500" : "bg-amber-500";
  const label = state === "online" ? "All systems normal" : state === "offline" ? "Service unavailable" : "Checking status";

  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-2 rounded-full border border-border bg-surface-raised px-3 py-1.5 shadow-panel">
            <span className="relative flex h-2 w-2">
              {state === "online" && (
                <span className={cn("absolute inline-flex h-full w-full rounded-full opacity-75 animate-pulse-ring", tone)} />
              )}
              <span className={cn("relative inline-flex h-2 w-2 rounded-full", tone)} />
            </span>
            <span className="hidden text-xs font-medium text-muted-foreground sm:inline">{label}</span>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          {label}
          {lastChecked ? ` · updated ${relativeTime(lastChecked)}` : ""}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  return (
    <button
      onClick={toggleTheme}
      aria-label="Toggle color theme"
      className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface-raised text-muted-foreground shadow-panel transition-colors hover:text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen flex-col bg-background bg-grid">
      <ComplianceBanner />
      <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur-md">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-8">
            <Link href="/dashboard" className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-teal-500 to-teal-700 text-white shadow-panel">
                <Stethoscope className="h-4.5 w-4.5" />
              </span>
              <div className="leading-tight">
                <p className="text-sm font-semibold text-foreground">{APP_NAME}</p>
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  Multi-agent eligibility engine
                </p>
              </div>
            </Link>
            <nav className="hidden items-center gap-1 md:flex">
              {NAV_ITEMS.map((item) => {
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                      active
                        ? "bg-teal-500/10 text-teal-400"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <SystemStatusPill />
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t border-border">
        <div className="container flex flex-col gap-2 py-6 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-center gap-1.5">
            <ShieldCheck className="h-3 w-3" />
            {APP_NAME} · Investigational decision support, not autonomous clinical decision-making.
          </p>
          <p>© {new Date().getFullYear()} Clinical Trial Matching Engine</p>
        </div>
      </footer>
    </div>
  );
}
