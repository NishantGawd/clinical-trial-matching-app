import Link from "next/link";
import { Stethoscope } from "lucide-react";
import { APP_NAME } from "@/lib/constants";

export function MarketingFooter() {
  return (
    <footer className="border-t border-border">
      <div className="container flex flex-col items-center gap-3 py-8 text-center sm:flex-row sm:justify-between sm:text-left">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-gradient-to-br from-teal-500 to-teal-700 text-white">
            <Stethoscope className="h-3.5 w-3.5" />
          </span>
          <span className="text-sm font-semibold text-foreground">{APP_NAME}</span>
        </Link>
        <p className="text-xs text-muted-foreground">
          © {new Date().getFullYear()} · Investigational decision support system · Not for autonomous clinical
          decision-making.
        </p>
      </div>
    </footer>
  );
}
