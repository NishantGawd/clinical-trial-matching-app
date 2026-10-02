import type { SwarmNodeId } from "@/types/clinical";

export const APP_NAME = "Matching Engine";
export const APP_ORG = "Clinical Trial Matching Engine";

export const COMPLIANCE_NOTICE =
  "Investigational Decision Support System (SaMD Class II) — Clinical Verification Required";

/**
 * Visual stepper nodes, matching the LangGraph swarm topology described in
 * the frontend spec: Retrieval & Cache -> Inclusion + Exclusion (concurrent)
 * -> Critic Auditor -> Synthesis & ML Scoring.
 */
export const SWARM_NODES: { id: SwarmNodeId; label: string; sublabel: string }[] = [
  { id: "retrieval", label: "Retrieval & Cache", sublabel: "PGVector lookup" },
  { id: "inclusion", label: "Inclusion Agent", sublabel: "Criteria match" },
  { id: "exclusion", label: "Exclusion Agent", sublabel: "Safety gate" },
  { id: "critic", label: "Critic Auditor", sublabel: "Fact verification" },
  { id: "synthesis", label: "Synthesis & ML", sublabel: "Scoring + attrition" },
];

export const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/explore", label: "Cohort & Protocols" },
];
