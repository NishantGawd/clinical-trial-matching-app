"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { EvalMetricsUsed } from "@/types/clinical";
import { isTruthyFlag } from "@/lib/utils";

/**
 * Normalizes each raw clinical feature onto a common 0-100 "relative burden"
 * scale so heterogeneous units (years, miles, count, ordinal, index) can
 * share one radial axis. Higher = greater contribution to attrition risk.
 * Reference ranges follow the feature semantics documented in ml_scoring.py
 * (ECOG 0-4, toxicity_burden 0-10) and typical oncology trial cohorts for
 * age, distance, and prior treatment lines.
 */
function normalizeMetrics(m: EvalMetricsUsed) {
  const age = Number(m.age) || 0;
  const distance = Number(m.distance_miles) || 0;
  const priors = Number(m.prior_treatments) || 0;
  const ecog = Number(m.ecog_score) || 0;
  const toxicity = Number(m.toxicity_burden) || 0;
  const hasCaregiver = isTruthyFlag(m.has_caregiver as number | boolean);

  return [
    { metric: "Age", raw: `${age} yrs`, value: Math.min(100, (age / 90) * 100) },
    { metric: "Distance", raw: `${distance.toFixed(0)} mi`, value: Math.min(100, (distance / 150) * 100) },
    { metric: "Prior Regimens", raw: `${priors}`, value: Math.min(100, (priors / 8) * 100) },
    { metric: "ECOG Status", raw: `ECOG ${ecog}`, value: Math.min(100, (ecog / 4) * 100) },
    { metric: "Toxicity Index", raw: `${toxicity.toFixed(1)} / 10`, value: Math.min(100, (toxicity / 10) * 100) },
    {
      metric: "Caregiver Gap",
      raw: hasCaregiver ? "Supported" : "Unsupported",
      value: hasCaregiver ? 8 : 100,
    },
  ];
}

function RadarTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-md border border-border bg-surface-raised px-3 py-2 text-xs shadow-panel-lift">
      <p className="font-medium text-foreground">{point.metric}</p>
      <p className="text-muted-foreground">{point.raw}</p>
    </div>
  );
}

export function FrailtyRadar({ metrics }: { metrics: EvalMetricsUsed }) {
  const data = normalizeMetrics(metrics);

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke="hsl(var(--border))" />
          <PolarAngleAxis
            dataKey="metric"
            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
          />
          <Radar
            name="Relative burden"
            dataKey="value"
            stroke="#0d9488"
            fill="#0d9488"
            fillOpacity={0.28}
            strokeWidth={2}
          />
          <Tooltip content={<RadarTooltip />} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
