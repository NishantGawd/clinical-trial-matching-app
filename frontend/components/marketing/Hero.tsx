"use client";

import Link from "next/link";
import { ArrowRight, ShieldCheck, PlayCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SwarmPreview } from "@/components/marketing/SwarmPreview";

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-grid opacity-40 [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,black_40%,transparent_100%)]" />
      <div
        className="pointer-events-none absolute -top-40 left-1/2 h-[560px] w-[900px] -translate-x-1/2 rounded-full opacity-[0.18] blur-3xl"
        style={{ background: "radial-gradient(closest-side, #0d9488, transparent)" }}
      />
      <div
        className="pointer-events-none absolute -top-24 right-1/4 h-[420px] w-[420px] rounded-full opacity-[0.14] blur-3xl"
        style={{ background: "radial-gradient(closest-side, #6366f1, transparent)" }}
      />

      <div className="container relative flex flex-col items-center gap-8 pb-20 pt-20 text-center sm:pt-28">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-raised px-3.5 py-1.5 text-xs font-medium text-muted-foreground shadow-panel">
          <ShieldCheck className="h-3.5 w-3.5 text-teal-500" />
          Investigational decision support · SaMD Class II
        </span>

        <h1 className="text-balance max-w-3xl text-4xl font-bold leading-[1.1] tracking-tight text-foreground sm:text-5xl lg:text-6xl">
          Match every patient to the right trial —{" "}
          <span className="bg-gradient-to-r from-teal-400 via-teal-500 to-indigo-500 bg-clip-text text-transparent">
            and explain every decision.
          </span>
        </h1>

        <p className="max-w-xl text-balance text-base leading-relaxed text-muted-foreground sm:text-lg">
          A multi-agent reasoning swarm cross-references patient records against protocol criteria, calibrates a
          defensible confidence score, and models attrition risk — with a full audit trail your clinical team can
          actually verify.
        </p>

        <div className="flex flex-col items-center gap-3 sm:flex-row">
          <Button asChild size="lg" className="group">
            <Link href="/dashboard">
              Launch Matching Engine
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href="/explore">
              <PlayCircle className="h-4 w-4" />
              Explore the cohort
            </Link>
          </Button>
        </div>

        <p className="text-xs text-muted-foreground">
          Clinical verification required before any enrollment decision.
        </p>

        <div className="mt-6 w-full max-w-4xl">
          <SwarmPreview />
        </div>
      </div>
    </section>
  );
}
