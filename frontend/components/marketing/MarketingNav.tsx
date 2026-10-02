"use client";

import Link from "next/link";
import { Stethoscope, Moon, Sun, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/components/layout/ThemeProvider";
import { APP_NAME } from "@/lib/constants";

export function MarketingNav() {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-md">
      <div className="container flex h-16 items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-teal-500 to-teal-700 text-white shadow-panel">
            <Stethoscope className="h-4.5 w-4.5" />
          </span>
          <span className="text-sm font-semibold text-foreground">{APP_NAME}</span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          <a href="#platform" className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
            Platform
          </a>
          <a href="#how-it-works" className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
            How it works
          </a>
          <a href="#trust" className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
            Compliance
          </a>
        </nav>

        <div className="flex items-center gap-2.5">
          <button
            onClick={toggleTheme}
            aria-label="Toggle color theme"
            className="hidden h-9 w-9 items-center justify-center rounded-full border border-border bg-surface-raised text-muted-foreground transition-colors hover:text-foreground hover:bg-muted sm:flex"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          <Button asChild size="sm">
            <Link href="/dashboard">
              Launch Application
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
