"use client";

import { Users, FlaskConical, Timer, HeartPulse } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useHealthCheck } from "@/hooks/useHealthCheck";
import { cn } from "@/lib/utils";

interface MetricRibbonProps {
  patientsCount: number;
  patientsLoading: boolean;
  trialsCount: number;
  trialsLoading: boolean;
}

function MetricCard({
  icon: Icon,
  label,
  value,
  loading,
  accent,
  hint,
}: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
  loading?: boolean;
  accent: "teal" | "indigo" | "amber" | "status";
  hint?: string;
}) {
  const accentClasses: Record<typeof accent, string> = {
    teal: "bg-gradient-to-br from-teal-500 to-teal-700 text-white",
    indigo: "bg-gradient-to-br from-indigo-500 to-indigo-700 text-white",
    amber: "bg-gradient-to-br from-amber-500 to-amber-600 text-white",
    status: "bg-gradient-to-br from-slate-500 to-slate-700 text-white",
  };

  return (
    <Card className="group relative overflow-hidden p-5 transition-shadow hover:shadow-panel-lift">
      <div
        className={cn(
          "pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full opacity-[0.08] blur-xl transition-opacity group-hover:opacity-[0.14]",
          accent === "teal" && "bg-teal-500",
          accent === "indigo" && "bg-indigo-500",
          accent === "amber" && "bg-amber-500",
          accent === "status" && "bg-slate-500",
        )}
      />
      <div className="relative flex items-start gap-4">
        <span className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-xl shadow-panel", accentClasses[accent])}>
          <Icon className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
          {loading ? (
            <Skeleton className="mt-2 h-7 w-20" />
          ) : (
            <p className="tabular mt-0.5 text-2xl font-bold text-foreground">{value}</p>
          )}
          {hint && <p className="mt-1 truncate text-[11px] text-muted-foreground">{hint}</p>}
        </div>
      </div>
    </Card>
  );
}

export function MetricRibbon({
  patientsCount,
  patientsLoading,
  trialsCount,
  trialsLoading,
}: MetricRibbonProps) {
  const { state } = useHealthCheck();

  const statusLabel = state === "online" ? "Operational" : state === "offline" ? "Unavailable" : "Checking";
  const statusHint =
    state === "online" ? "All services running normally" : state === "offline" ? "Reconnecting…" : "Awaiting response…";

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard
        icon={Users}
        label="Active Patients Indexed"
        value={patientsCount.toLocaleString()}
        loading={patientsLoading}
        accent="teal"
        hint="Synced from the clinical record pipeline"
      />
      <MetricCard
        icon={FlaskConical}
        label="Protocols Ingested"
        value={trialsCount.toLocaleString()}
        loading={trialsLoading}
        accent="indigo"
        hint="Live trial protocol registry"
      />
      <MetricCard
        icon={Timer}
        label="Avg. Match Latency"
        value="~12.4s"
        accent="amber"
        hint="Swarm evaluation · instant when cached"
      />
      <MetricCard
        icon={HeartPulse}
        label="System Health"
        value={statusLabel}
        accent="status"
        hint={statusHint}
      />
    </div>
  );
}
