"use client";

import * as React from "react";
import { Check, ChevronsUpDown, Loader2, PlayCircle, RefreshCw, AlertTriangle, User, Beaker } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { AgentSwarmStepper } from "@/components/dashboard/AgentSwarmStepper";
import { MatchReportView } from "@/components/diagnostic/MatchReportView";
import { runMatch, ApiRequestError } from "@/lib/api";
import { SWARM_NODES } from "@/lib/constants";
import { cn, truncate } from "@/lib/utils";
import type { MatchResponse, Patient, SwarmNodeId, SwarmNodeState, Trial } from "@/types/clinical";

type RunPhase = "idle" | "running" | "success" | "error";

function makeIdleNodes(): SwarmNodeState[] {
  return SWARM_NODES.map((n) => ({ id: n.id, label: n.label, status: "idle" as const }));
}

function EntitySelector<T extends { preview: string }>({
  label,
  icon: Icon,
  items,
  loading,
  getId,
  selectedId,
  onSelect,
  placeholder,
  emptyLabel,
}: {
  label: string;
  icon: React.ElementType;
  items: T[];
  loading: boolean;
  getId: (item: T) => string;
  selectedId: string | null;
  onSelect: (id: string) => void;
  placeholder: string;
  emptyLabel: string;
}) {
  const [open, setOpen] = React.useState(false);
  const selected = items.find((item) => getId(item) === selectedId) ?? null;

  return (
    <div className="flex flex-col gap-1.5">
      <Label>{label}</Label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            disabled={loading}
            className={cn(
              "flex h-auto min-h-[3.25rem] w-full items-center justify-between gap-3 rounded-md border border-input bg-surface px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
            )}
          >
            <span className="flex min-w-0 items-center gap-2.5">
              <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
              {selected ? (
                <span className="min-w-0">
                  <span className="block truncate font-mono text-sm font-medium text-foreground">
                    {getId(selected)}
                  </span>
                  <span className="block truncate text-xs text-muted-foreground">
                    {truncate(selected.preview.replace(/\n/g, " "), 70)}
                  </span>
                </span>
              ) : (
                <span className="text-muted-foreground">{loading ? "Loading…" : placeholder}</span>
              )}
            </span>
            <ChevronsUpDown className="h-4 w-4 shrink-0 text-muted-foreground" />
          </button>
        </PopoverTrigger>
        <PopoverContent className="p-0">
          <Command>
            <CommandInput placeholder={`Search ${label.toLowerCase()}…`} />
            <CommandList>
              <CommandEmpty>{emptyLabel}</CommandEmpty>
              <CommandGroup>
                {items.map((item) => {
                  const id = getId(item);
                  return (
                    <CommandItem
                      key={id}
                      value={`${id} ${item.preview}`}
                      onSelect={() => {
                        onSelect(id);
                        setOpen(false);
                      }}
                    >
                      <div className="flex w-full items-start gap-2">
                        <Check
                          className={cn(
                            "mt-0.5 h-3.5 w-3.5 shrink-0",
                            id === selectedId ? "opacity-100 text-teal-500" : "opacity-0",
                          )}
                        />
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-mono text-xs font-medium text-foreground">{id}</p>
                          <p className="truncate text-xs text-muted-foreground">
                            {truncate(item.preview.replace(/\n/g, " "), 90)}
                          </p>
                        </div>
                      </div>
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}

export function MatchWorkspace({
  patients,
  patientsLoading,
  trials,
  trialsLoading,
}: {
  patients: Patient[];
  patientsLoading: boolean;
  trials: Trial[];
  trialsLoading: boolean;
}) {
  const [patientId, setPatientId] = React.useState<string | null>(null);
  const [trialId, setTrialId] = React.useState<string | null>(null);
  const [forceRefresh, setForceRefresh] = React.useState(false);

  const [phase, setPhase] = React.useState<RunPhase>("idle");
  const [nodes, setNodes] = React.useState<SwarmNodeState[]>(makeIdleNodes());
  const [result, setResult] = React.useState<MatchResponse | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [reportOpen, setReportOpen] = React.useState(false);

  const timersRef = React.useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = () => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  };

  const setNodeStatus = (id: SwarmNodeId, status: SwarmNodeState["status"]) => {
    setNodes((prev) => prev.map((n) => (n.id === id ? { ...n, status } : n)));
  };

  React.useEffect(() => clearTimers, []);

  async function handleRunMatch() {
    if (!patientId || !trialId) return;

    clearTimers();
    setError(null);
    setResult(null);
    setPhase("running");
    setNodes(makeIdleNodes());

    // Cosmetic staged progression while the (single, non-streaming) POST
    // /api/match call is in flight. The backend returns one final payload,
    // so this reflects the known LangGraph topology rather than real
    // server-sent events — it is finalized instantly the moment the
    // response actually arrives, whichever stage it's in.
    timersRef.current.push(setTimeout(() => setNodeStatus("retrieval", "active"), 50));
    timersRef.current.push(
      setTimeout(() => {
        setNodeStatus("retrieval", "done");
        setNodeStatus("inclusion", "active");
        setNodeStatus("exclusion", "active");
      }, 700),
    );
    timersRef.current.push(
      setTimeout(() => {
        setNodeStatus("inclusion", "done");
        setNodeStatus("exclusion", "done");
        setNodeStatus("critic", "active");
      }, 3200),
    );
    timersRef.current.push(
      setTimeout(() => {
        setNodeStatus("critic", "done");
        setNodeStatus("synthesis", "active");
      }, 6000),
    );

    try {
      const response = await runMatch({
        patient_id: patientId,
        trial_id: trialId,
        force_refresh: forceRefresh,
      });

      clearTimers();
      setNodes(SWARM_NODES.map((n) => ({ id: n.id, label: n.label, status: "done" as const })));
      setResult(response);
      setPhase("success");
      setReportOpen(true);
    } catch (err) {
      clearTimers();
      const message =
        err instanceof ApiRequestError ? err.message : "The matching pipeline failed unexpectedly.";
      setError(message);
      setPhase("error");
      setNodes((prev) => prev.map((n) => (n.status === "active" ? { ...n, status: "error" as const } : n)));
    }
  }

  const canRun = Boolean(patientId && trialId) && phase !== "running";
  const isFastPath = result?.execution_mode === "DETERMINISTIC_FAST_PATH";
  const isCached = result?.source === "CACHE";

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Interactive Match Workspace</CardTitle>
          <CardDescription>
            Select a patient record and a target protocol, then run the multi-agent eligibility swarm.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <EntitySelector
              label="Patient"
              icon={User}
              items={patients}
              loading={patientsLoading}
              getId={(p) => p.patient_id}
              selectedId={patientId}
              onSelect={setPatientId}
              placeholder="Select a patient record…"
              emptyLabel="No matching patients."
            />
            <EntitySelector
              label="Trial Protocol"
              icon={Beaker}
              items={trials}
              loading={trialsLoading}
              getId={(t) => t.trial_id}
              selectedId={trialId}
              onSelect={setTrialId}
              placeholder="Select a trial protocol…"
              emptyLabel="No matching trials."
            />
          </div>

          <div className="flex flex-col gap-4 border-t border-border pt-5 sm:flex-row sm:items-center sm:justify-between">
            <label className="flex cursor-pointer items-center gap-2.5">
              <Checkbox
                checked={forceRefresh}
                onCheckedChange={(v) => setForceRefresh(v === true)}
                disabled={phase === "running"}
              />
              <span className="text-sm text-foreground">Force Live Refresh</span>
              <span className="text-xs text-muted-foreground">(bypass DB cache)</span>
            </label>

            <Button onClick={handleRunMatch} disabled={!canRun} size="lg" className="w-full sm:w-auto">
              {phase === "running" ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Running Multi-Agent Match Swarm…
                </>
              ) : (
                <>
                  <PlayCircle className="h-4 w-4" />
                  Run Multi-Agent Match Swarm
                </>
              )}
            </Button>
          </div>

          {(phase === "running" || phase === "success" || phase === "error") && (
            <div className="rounded-md border border-border bg-muted/20 p-5">
              <div className="mb-4 flex items-center justify-between">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Live Agent Execution
                </p>
                {result && (
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {result.source} · {result.execution_mode}
                  </span>
                )}
              </div>
              <AgentSwarmStepper nodes={nodes} fastPath={isFastPath} />
            </div>
          )}

          {phase === "error" && error && (
            <div className="flex items-start gap-2.5 rounded-md border border-rose-600/30 bg-rose-500/[0.06] px-4 py-3 text-sm text-rose-400">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <p className="font-medium">Matching pipeline failed</p>
                <p className="mt-0.5 text-xs text-rose-400/80">{error}</p>
              </div>
            </div>
          )}

          {phase === "success" && result && !reportOpen && (
            <button
              onClick={() => setReportOpen(true)}
              className="flex items-center justify-between rounded-md border border-teal-600/30 bg-teal-500/[0.06] px-4 py-3 text-left text-sm text-teal-400 transition-colors hover:bg-teal-500/[0.1]"
            >
              <span className="flex items-center gap-2 font-medium">
                <RefreshCw className="h-3.5 w-3.5" />
                Match complete — reopen diagnostic report
              </span>
              <span className="text-xs opacity-80">
                {isCached ? "Served from cache" : "View 4-quadrant breakdown →"}
              </span>
            </button>
          )}
        </CardContent>
      </Card>

      <Dialog open={reportOpen} onOpenChange={setReportOpen}>
        <DialogContent className="max-w-6xl p-0">
          {result && <MatchReportView response={result} onRerun={handleRunMatch} rerunning={phase === "running"} />}
        </DialogContent>
      </Dialog>
    </>
  );
}
