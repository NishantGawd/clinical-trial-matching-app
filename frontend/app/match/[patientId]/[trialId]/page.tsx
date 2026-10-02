"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Loader2, AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { MatchReportView } from "@/components/diagnostic/MatchReportView";
import { runMatch, ApiRequestError } from "@/lib/api";
import type { MatchResponse } from "@/types/clinical";

export default function MatchDeepLinkPage() {
  const params = useParams<{ patientId: string; trialId: string }>();
  const router = useRouter();

  const patientId = decodeURIComponent(params.patientId);
  const trialId = decodeURIComponent(params.trialId);

  const [forceRefresh, setForceRefresh] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<MatchResponse | null>(null);

  const load = React.useCallback(
    async (force = false) => {
      setLoading(true);
      setError(null);
      try {
        const res = await runMatch({ patient_id: patientId, trial_id: trialId, force_refresh: force });
        setResult(res);
      } catch (err) {
        setError(err instanceof ApiRequestError ? err.message : "The matching pipeline failed unexpectedly.");
      } finally {
        setLoading(false);
      }
    },
    [patientId, trialId],
  );

  React.useEffect(() => {
    load(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId, trialId]);

  return (
    <div className="container py-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <Button variant="ghost" size="sm" onClick={() => router.push("/")}>
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to dashboard
        </Button>
        <label className="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground">
          <Checkbox checked={forceRefresh} onCheckedChange={(v) => setForceRefresh(v === true)} />
          Force live refresh on reload
        </label>
      </div>

      <div className="overflow-hidden rounded-lg border border-border bg-surface">
        {loading && (
          <div className="flex flex-col items-center justify-center gap-3 py-24">
            <Loader2 className="h-6 w-6 animate-spin text-teal-500" />
            <p className="text-sm text-muted-foreground">
              Evaluating <span className="font-mono text-foreground">{patientId}</span> against{" "}
              <span className="font-mono text-foreground">{trialId}</span>…
            </p>
          </div>
        )}

        {!loading && error && (
          <div className="flex flex-col items-center gap-3 px-6 py-20 text-center">
            <AlertTriangle className="h-6 w-6 text-rose-400" />
            <p className="max-w-md text-sm text-muted-foreground">{error}</p>
            <Button variant="outline" size="sm" onClick={() => load(forceRefresh)}>
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </Button>
          </div>
        )}

        {!loading && !error && result && (
          <MatchReportView response={result} onRerun={() => load(forceRefresh)} rerunning={loading} standalone />
        )}
      </div>
    </div>
  );
}
