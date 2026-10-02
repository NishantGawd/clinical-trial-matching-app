"use client";

import * as React from "react";
import Link from "next/link";
import { CheckCircle2, XCircle, RefreshCw, Loader2, Database, Gauge, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { DialogHeader as RadixDialogHeader, DialogTitle as RadixDialogTitle, DialogDescription as RadixDialogDescription } from "@/components/ui/dialog";
import { cn as cnMerge } from "@/lib/utils";

/**
 * The four-quadrant report is used both inside the workspace's Dialog modal
 * and as a standalone page at /match/[patientId]/[trialId] for shareable
 * deep links. Radix's DialogTitle/DialogDescription require a Dialog.Root
 * ancestor, so outside a modal we render plain, identically-styled markup
 * instead of the Radix primitives.
 */
function ReportHeader({ standalone, children }: { standalone?: boolean; children: React.ReactNode }) {
  if (standalone) {
    return <div className={cnMerge("flex flex-col gap-1 border-b border-border px-6 py-4")}>{children}</div>;
  }
  return <RadixDialogHeader className="pr-14">{children}</RadixDialogHeader>;
}

function ReportTitle({ standalone, children }: { standalone?: boolean; children: React.ReactNode }) {
  const className = "flex flex-wrap items-baseline gap-x-2 gap-y-0.5 pt-1 font-mono text-base font-semibold text-foreground";
  if (standalone) return <h1 className={className}>{children}</h1>;
  return <RadixDialogTitle className={className}>{children}</RadixDialogTitle>;
}

function ReportDescription({ standalone, children }: { standalone?: boolean; children: React.ReactNode }) {
  if (standalone) return <p className="text-xs text-muted-foreground">{children}</p>;
  return <RadixDialogDescription>{children}</RadixDialogDescription>;
}
import { ScoreGauge } from "@/components/diagnostic/ScoreGauge";
import { CalibrationAccordion } from "@/components/diagnostic/CalibrationAccordion";
import { AuditTrailPanel } from "@/components/diagnostic/AuditTrailPanel";
import { DropoutRadialBar } from "@/components/diagnostic/DropoutRadialBar";
import { FrailtyRadar } from "@/components/diagnostic/FrailtyRadar";
import { RiskDriverList } from "@/components/diagnostic/RiskDriverList";
import { InterventionList } from "@/components/diagnostic/InterventionList";
import { AlternativeTrialsPanel } from "@/components/diagnostic/AlternativeTrialsPanel";
import { runMatch, ApiRequestError } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { MatchResponse } from "@/types/clinical";

function QuadrantCard({
  letter,
  title,
  subtitle,
  children,
  accent,
}: {
  letter: string;
  title: string;
  subtitle: string;
  children: React.ReactNode;
  accent: "teal" | "indigo" | "amber" | "rose";
}) {
  const accentClasses: Record<typeof accent, string> = {
    teal: "bg-teal-500/10 text-teal-400 ring-teal-600/25",
    indigo: "bg-indigo-500/10 text-indigo-400 ring-indigo-600/25",
    amber: "bg-amber-500/10 text-amber-400 ring-amber-600/25",
    rose: "bg-rose-500/10 text-rose-400 ring-rose-600/25",
  };

  return (
    <div className="flex flex-col rounded-lg border border-border bg-surface">
      <div className="flex items-center gap-3 border-b border-border px-5 py-4">
        <span
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-xs font-bold ring-1 ring-inset",
            accentClasses[accent],
          )}
        >
          {letter}
        </span>
        <div>
          <p className="text-sm font-semibold text-foreground">{title}</p>
          <p className="text-[11px] text-muted-foreground">{subtitle}</p>
        </div>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

export function MatchReportView({
  response,
  onRerun,
  rerunning,
  standalone,
}: {
  response: MatchResponse;
  onRerun?: () => void;
  rerunning?: boolean;
  /** Render with plain (non-Radix-Dialog) header markup for use outside a modal. */
  standalone?: boolean;
}) {
  const [current, setCurrent] = React.useState<MatchResponse>(response);
  const [pivotingTrialId, setPivotingTrialId] = React.useState<string | null>(null);
  const [pivotError, setPivotError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setCurrent(response);
    setPivotError(null);
  }, [response]);

  const { data, source, execution_mode } = current;
  const eligible = data.overall_match;

  async function handlePivot(trialId: string) {
    setPivotError(null);
    setPivotingTrialId(trialId);
    try {
      const next = await runMatch({
        patient_id: data.patient_id,
        trial_id: trialId,
        force_refresh: false,
      });
      setCurrent(next);
    } catch (err) {
      setPivotError(
        err instanceof ApiRequestError ? err.message : "Failed to re-analyze against the alternative protocol.",
      );
    } finally {
      setPivotingTrialId(null);
    }
  }

  return (
    <div className={cnMerge("flex flex-col", standalone ? "min-h-[calc(100vh-4rem)]" : "max-h-[90vh]")}>
      <ReportHeader standalone={standalone}>
        <div className="flex flex-wrap items-center gap-3">
          <Badge
            variant={eligible ? "pass" : "fail"}
            className="gap-1.5 px-2.5 py-1 text-xs"
          >
            {eligible ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
            {eligible ? "ELIGIBLE / PASSED" : "DISQUALIFIED / CONTRAINDICATED"}
          </Badge>
          <Badge variant="outline" className="gap-1.5">
            <Database className="h-3 w-3" />
            {source}
          </Badge>
          <Badge variant="outline" className="gap-1.5">
            <Gauge className="h-3 w-3" />
            {execution_mode}
          </Badge>
        </div>
        <ReportTitle standalone={standalone}>
          <span>{data.patient_id}</span>
          <span className="text-muted-foreground">×</span>
          <span>{data.trial_id}</span>
        </ReportTitle>
        <ReportDescription standalone={standalone}>
          Match Diagnostic Deep-Dive · Explainable clinical audit trail
        </ReportDescription>
      </ReportHeader>

      <ScrollArea className="flex-1">
        <div className="flex flex-col gap-5 p-6">
          {pivotError && (
            <div className="rounded-md border border-rose-600/30 bg-rose-500/[0.06] px-4 py-3 text-sm text-rose-400">
              {pivotError}
            </div>
          )}

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            {/* Quadrant A */}
            <QuadrantCard
              letter="A"
              title="Eligibility Decision & Calibrated Confidence"
              subtitle="Continuous scoring with itemized deductions"
              accent="teal"
            >
              <div className="mb-5 flex flex-wrap items-center justify-around gap-4">
                <ScoreGauge
                  value={data.extraction_confidence}
                  label="Extraction Confidence"
                  tone="indigo"
                />
                <ScoreGauge
                  value={data.eligibility_score}
                  label="Eligibility Score"
                  display="score"
                  tone="teal"
                />
                <ScoreGauge
                  value={data.confidence_score}
                  label="Composite Confidence"
                  display="score"
                  tone="amber"
                />
              </div>
              <CalibrationAccordion breakdown={data.calibration_breakdown} />
            </QuadrantCard>

            {/* Quadrant B */}
            <QuadrantCard
              letter="B"
              title="Clinical Audit Trail"
              subtitle="Explainable AI reasoning trace"
              accent="indigo"
            >
              <AuditTrailPanel
                inclusionStatus={data.inclusion_status}
                exclusionStatus={data.exclusion_status}
                matchSummary={data.match_summary}
              />
            </QuadrantCard>

            {/* Quadrant C */}
            <QuadrantCard
              letter="C"
              title="ML Patient Frailty & Retention"
              subtitle={data.ml_attrition_risk.status}
              accent="amber"
            >
              <div className="flex flex-col gap-5">
                <DropoutRadialBar
                  probabilityPercent={data.ml_attrition_risk.raw_dropout_probability ?? 0}
                  riskLevel={data.ml_attrition_risk.attrition_risk_level}
                />
                <Separator />
                {"age" in (data.ml_attrition_risk.eval_metrics_used || {}) ? (
                  <FrailtyRadar metrics={data.ml_attrition_risk.eval_metrics_used as any} />
                ) : (
                  <p className="text-xs text-muted-foreground">No feature vector was returned for this patient.</p>
                )}
                <Separator />
                <RiskDriverList
                  riskDrivers={data.ml_attrition_risk.primary_risk_drivers}
                  retentionDrivers={data.ml_attrition_risk.primary_retention_drivers}
                />
                <Separator />
                <div>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Actionable Clinical Interventions
                  </p>
                  <InterventionList interventions={data.ml_attrition_risk.actionable_interventions} />
                </div>
              </div>
            </QuadrantCard>

            {/* Quadrant D */}
            {!eligible && (
              <QuadrantCard
                letter="D"
                title="Dynamic Alternative Protocols"
                subtitle="PGVector-ranked semantic alternatives"
                accent="rose"
              >
                <AlternativeTrialsPanel
                  trials={data.alternative_trials}
                  onPivot={handlePivot}
                  pivotingTrialId={pivotingTrialId}
                />
              </QuadrantCard>
            )}
          </div>
        </div>
      </ScrollArea>

      {(onRerun || !standalone) && (
        <div className="flex items-center justify-between border-t border-border px-6 py-3.5">
          <p className="truncate pr-4 text-[11px] text-muted-foreground">{data.ml_attrition_risk.message}</p>
          <div className="flex shrink-0 items-center gap-2">
            {!standalone && (
              <Button variant="outline" size="sm" asChild>
                <Link href={`/match/${encodeURIComponent(data.patient_id)}/${encodeURIComponent(data.trial_id)}`}>
                  <ExternalLink className="h-3.5 w-3.5" />
                  Shareable link
                </Link>
              </Button>
            )}
            {onRerun && (
              <Button variant="secondary" size="sm" onClick={onRerun} disabled={rerunning}>
                {rerunning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                Re-run evaluation
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
