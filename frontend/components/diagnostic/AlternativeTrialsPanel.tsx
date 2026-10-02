import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { parsePercentString } from "@/lib/utils";
import type { AlternativeTrial } from "@/types/clinical";

export function AlternativeTrialsPanel({
  trials,
  onPivot,
  pivotingTrialId,
}: {
  trials: AlternativeTrial[];
  onPivot: (trialId: string) => void;
  pivotingTrialId: string | null;
}) {
  if (trials.length === 0) {
    return (
      <p className="rounded-md border border-dashed border-border p-4 text-xs text-muted-foreground">
        No PGVector-ranked alternative protocols were returned for this patient profile.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {trials.slice(0, 3).map((trial) => {
        const score = parsePercentString(trial.similarity_match_score);
        const isPivoting = pivotingTrialId === trial.trial_id;
        return (
          <div
            key={trial.trial_id}
            className="flex flex-col gap-3 rounded-md border border-border bg-surface-raised p-4 sm:flex-row sm:items-start sm:justify-between"
          >
            <div className="min-w-0 flex-1">
              <div className="mb-1 flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs font-semibold text-foreground">{trial.trial_id}</span>
                <Badge variant="info">{score.toFixed(1)}% similarity</Badge>
              </div>
              <p className="line-clamp-2 text-sm font-medium text-foreground">{trial.trial_title}</p>
              <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{trial.match_rationale}</p>
            </div>
            <Button
              variant="indigo"
              size="sm"
              className="shrink-0"
              onClick={() => onPivot(trial.trial_id)}
              disabled={pivotingTrialId !== null}
            >
              {isPivoting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Re-analyzing…
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5" />
                  Pivot & Re-Analyze
                  <ArrowRight className="h-3.5 w-3.5" />
                </>
              )}
            </Button>
          </div>
        );
      })}
    </div>
  );
}
