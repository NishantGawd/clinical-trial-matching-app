import { ShieldCheck, ShieldX, Gavel, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ExclusionStatus, InclusionStatus } from "@/types/clinical";

function StatusCard({
  title,
  icon: Icon,
  status,
  passed,
  passedCopy,
  failedCopy,
}: {
  title: string;
  icon: React.ElementType;
  status: string;
  passed: boolean;
  passedCopy: string;
  failedCopy: string;
}) {
  return (
    <div className="flex flex-1 flex-col gap-3 rounded-md border border-border bg-surface-raised p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className={cn("h-4 w-4", passed ? "text-teal-400" : "text-rose-400")} />
          <p className="text-sm font-semibold text-foreground">{title}</p>
        </div>
        <Badge variant={passed ? "pass" : "fail"}>{status}</Badge>
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground">{passed ? passedCopy : failedCopy}</p>
    </div>
  );
}

export function AuditTrailPanel({
  inclusionStatus,
  exclusionStatus,
  matchSummary,
}: {
  inclusionStatus: InclusionStatus;
  exclusionStatus: ExclusionStatus;
  matchSummary: string;
}) {
  const inclusionPassed = inclusionStatus === "PASSED";
  const exclusionPassed = exclusionStatus === "CLEARED";

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-4 sm:flex-row">
        <StatusCard
          title="Inclusion Criteria"
          icon={ShieldCheck}
          status={inclusionStatus}
          passed={inclusionPassed}
          passedCopy="All evaluated disease-specific and target inclusion criteria are satisfied by the documented record."
          failedCopy="One or more essential protocol inclusion criteria are not satisfied by the documented record."
        />
        <StatusCard
          title="Exclusion Criteria"
          icon={ShieldX}
          status={exclusionStatus}
          passed={exclusionPassed}
          passedCopy="No active contraindications or disqualifying exclusion factors were found in the clinical record."
          failedCopy="The record documents a clinical factor that triggers a protocol safety exclusion."
        />
      </div>

      <div className="rounded-md border border-border bg-muted/20 p-4">
        <div className="mb-1.5 flex items-center gap-2">
          <FileText className="h-3.5 w-3.5 text-muted-foreground" />
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Synthesized Match Rationale
          </p>
        </div>
        <p className="text-sm leading-relaxed text-foreground">{matchSummary}</p>
      </div>

      <div className="flex items-start gap-2.5 rounded-md border border-indigo-600/25 bg-indigo-500/[0.06] p-4">
        <Gavel className="mt-0.5 h-4 w-4 shrink-0 text-indigo-400" />
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-indigo-400">Auditor Feedback</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Reasoning verified for factual grounding against source clinical records by the Critic agent prior to
            synthesis.
          </p>
        </div>
      </div>
    </div>
  );
}
