"use client";

import * as React from "react";
import { CheckCircle2 } from "lucide-react";
import { AgentSwarmStepper } from "@/components/dashboard/AgentSwarmStepper";
import { SWARM_NODES } from "@/lib/constants";
import type { SwarmNodeState } from "@/types/clinical";

const CYCLE_MS = 1100;

function buildFrame(activeIndex: number): SwarmNodeState[] {
  return SWARM_NODES.map((node, i) => ({
    id: node.id,
    label: node.label,
    status: i < activeIndex ? "done" : i === activeIndex ? "active" : "idle",
  }));
}

/**
 * Decorative, looping preview of the real swarm topology used on the
 * dashboard (see AgentSwarmStepper). Purely illustrative for the landing
 * page — not connected to the live API — labeled as such below.
 */
export function SwarmPreview() {
  const [step, setStep] = React.useState(0);
  const totalSteps = SWARM_NODES.length + 1;

  React.useEffect(() => {
    const id = setInterval(() => {
      setStep((s) => (s + 1) % totalSteps);
    }, CYCLE_MS);
    return () => clearInterval(id);
  }, [totalSteps]);

  const nodes = buildFrame(step);
  const complete = step === totalSteps - 1;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-panel-lift">
      <div className="flex items-center gap-1.5 border-b border-border bg-muted/30 px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-rose-400/70" />
        <span className="h-2.5 w-2.5 rounded-full bg-amber-400/70" />
        <span className="h-2.5 w-2.5 rounded-full bg-teal-400/70" />
        <span className="ml-3 text-xs font-medium text-muted-foreground">Match Workspace Preview</span>
      </div>

      <div className="p-6 sm:p-8">
        <AgentSwarmStepper nodes={nodes} />

        <div className="mt-6 flex flex-col items-center gap-2 border-t border-border pt-5 sm:flex-row sm:justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2
              className={`h-4 w-4 transition-colors ${complete ? "text-teal-400" : "text-muted-foreground/40"}`}
            />
            <span className="text-sm text-muted-foreground">
              {complete ? "Evaluation synthesized — 4-quadrant report ready" : "Evaluating against protocol criteria…"}
            </span>
          </div>
          <span className="text-[11px] text-muted-foreground/70">Illustrative example, not live patient data</span>
        </div>
      </div>
    </div>
  );
}
