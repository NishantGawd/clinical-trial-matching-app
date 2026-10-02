import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function FinalCta() {
  return (
    <section className="relative overflow-hidden border-t border-border py-20">
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[420px] w-[820px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-[0.12] blur-3xl"
        style={{ background: "radial-gradient(closest-side, #0d9488, transparent)" }}
      />
      <div className="container relative flex flex-col items-center gap-5 text-center">
        <h2 className="text-balance max-w-lg text-3xl font-bold tracking-tight text-foreground">
          Ready to see it evaluate a real case?
        </h2>
        <p className="max-w-md text-sm text-muted-foreground">
          Open the workspace, pick a patient and a protocol, and run the full multi-agent swarm end to end.
        </p>
        <Button asChild size="lg" className="group">
          <Link href="/dashboard">
            Launch Matching Engine
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </Button>
      </div>
    </section>
  );
}
