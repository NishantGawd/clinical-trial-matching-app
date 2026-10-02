"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Check, Loader2, X, Database, ShieldCheck, ShieldX, Gavel, Sigma } from "lucide-react";
import type { SwarmNodeState } from "@/types/clinical";
import { cn } from "@/lib/utils";

const NODE_ICONS: Record<string, React.ElementType> = {
  retrieval: Database,
  inclusion: ShieldCheck,
  exclusion: ShieldX,
  critic: Gavel,
  synthesis: Sigma,
};

function NodePill({ node }: { node: SwarmNodeState }) {
  const Icon = NODE_ICONS[node.id] ?? Database;

  return (
    <div className="flex w-20 shrink-0 flex-col items-center gap-2 sm:w-24">
      <div
        className={cn(
          "relative flex h-11 w-11 items-center justify-center rounded-full border transition-colors duration-300",
          node.status === "idle" && "border-border bg-surface-raised text-muted-foreground",
          node.status === "active" && "border-indigo-500/60 bg-indigo-500/10 text-indigo-400 shadow-glow",
          node.status === "done" && "border-teal-600/50 bg-teal-500/10 text-teal-400",
          node.status === "error" && "border-rose-600/50 bg-rose-500/10 text-rose-400",
        )}
      >
        {node.status === "active" && (
          <span className="absolute inset-0 rounded-full border border-indigo-400/40 animate-pulse-ring" />
        )}
        {node.status === "active" ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : node.status === "done" ? (
          <Check className="h-4 w-4" />
        ) : node.status === "error" ? (
          <X className="h-4 w-4" />
        ) : (
          <Icon className="h-4 w-4" />
        )}
      </div>
      <p
        className={cn(
          "text-center text-[11px] font-medium leading-tight",
          node.status === "idle" ? "text-muted-foreground" : "text-foreground",
        )}
      >
        {node.label}
      </p>
    </div>
  );
}

function Connector({ active }: { active: boolean }) {
  return (
    <div className="relative mb-6 h-px w-6 shrink-0 self-center bg-border sm:w-10">
      <AnimatePresence>
        {active && (
          <motion.div
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.45, ease: "easeOut" }}
            style={{ transformOrigin: "left" }}
            className="absolute inset-0 bg-teal-500"
          />
        )}
      </AnimatePresence>
    </div>
  );
}

export function AgentSwarmStepper({ nodes, fastPath }: { nodes: SwarmNodeState[]; fastPath?: boolean }) {
  const retrieval = nodes.find((n) => n.id === "retrieval")!;
  const inclusion = nodes.find((n) => n.id === "inclusion")!;
  const exclusion = nodes.find((n) => n.id === "exclusion")!;
  const critic = nodes.find((n) => n.id === "critic")!;
  const synthesis = nodes.find((n) => n.id === "synthesis")!;

  const retrievalDone = retrieval.status === "done" || retrieval.status === "active";
  const concurrentDone =
    (inclusion.status === "done" || inclusion.status === "active") &&
    (exclusion.status === "done" || exclusion.status === "active");
  const criticDone = critic.status === "done" || critic.status === "active";
  const concurrentActive = inclusion.status !== "idle" || exclusion.status !== "idle";

  return (
    <div className="w-full">
      {fastPath && (
        <div className="mb-4 flex items-center gap-2 rounded-md border border-amber-600/25 bg-amber-500/[0.06] px-3 py-1.5 text-xs text-amber-500">
          Deterministic fast-path triggered — safety pre-filter bypassed the full reasoning swarm.
        </div>
      )}
      <div className="flex items-start justify-center overflow-x-auto pb-1">
        <NodePill node={retrieval} />
        <Connector active={retrievalDone} />
        <div className="flex flex-col items-center">
          <div className="flex gap-3 sm:gap-4">
            <NodePill node={inclusion} />
            <NodePill node={exclusion} />
          </div>
          <span
            className={cn(
              "-mt-1 rounded-full border px-2 py-0.5 text-[9px] font-medium uppercase tracking-wide",
              concurrentActive
                ? "border-indigo-600/30 bg-indigo-500/10 text-indigo-400"
                : "border-border text-muted-foreground",
            )}
          >
            concurrent
          </span>
        </div>
        <Connector active={concurrentDone} />
        <NodePill node={critic} />
        <Connector active={criticDone} />
        <NodePill node={synthesis} />
      </div>
    </div>
  );
}
