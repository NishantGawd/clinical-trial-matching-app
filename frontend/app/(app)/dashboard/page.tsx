"use client";

import { AlertTriangle, Sparkles } from "lucide-react";
import { MetricRibbon } from "@/components/dashboard/MetricRibbon";
import { MatchWorkspace } from "@/components/workspace/MatchWorkspace";
import { usePatients, useTrials } from "@/hooks/useClinicalData";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  const patients = usePatients(50);
  const trials = useTrials(50);

  const hasListError = patients.error || trials.error;

  return (
    <div className="flex flex-col">
      <div className="relative overflow-hidden border-b border-border bg-gradient-to-b from-teal-500/[0.06] to-transparent">
        <div className="pointer-events-none absolute inset-0 bg-grid opacity-40" />
        <div className="container relative flex flex-col gap-2 py-10">
          <span className="inline-flex w-fit items-center gap-1.5 rounded-full border border-teal-600/30 bg-teal-500/10 px-3 py-1 text-[11px] font-medium text-teal-400">
            <Sparkles className="h-3 w-3" />
            Live matching engine
          </span>
          <h1 className="text-balance text-3xl font-bold tracking-tight text-foreground">
            Executive Clinical Dashboard
          </h1>
          <p className="max-w-xl text-sm text-muted-foreground">
            Real-time cohort overview, calibrated eligibility matching, and multi-agent swarm execution.
          </p>
        </div>
      </div>

      <div className="container flex flex-col gap-8 py-8">
        {hasListError && (
          <div className="flex flex-col items-start gap-3 rounded-lg border border-rose-600/25 bg-rose-500/[0.06] px-4 py-3.5 text-sm text-rose-400 sm:flex-row sm:items-center sm:justify-between">
            <span className="flex items-start gap-2.5">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              {patients.error || trials.error}
            </span>
            <Button
              variant="outline"
              size="sm"
              className="shrink-0"
              onClick={() => {
                patients.refresh();
                trials.refresh();
              }}
            >
              Retry
            </Button>
          </div>
        )}

        <MetricRibbon
          patientsCount={patients.count}
          patientsLoading={patients.loading}
          trialsCount={trials.count}
          trialsLoading={trials.loading}
        />

        <MatchWorkspace
          patients={patients.items}
          patientsLoading={patients.loading}
          trials={trials.items}
          trialsLoading={trials.loading}
        />
      </div>
    </div>
  );
}
