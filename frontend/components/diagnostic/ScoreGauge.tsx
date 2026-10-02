"use client";

import { cn } from "@/lib/utils";

interface ScoreGaugeProps {
  /** 0..1 fraction */
  value: number;
  label: string;
  /** How to render the center number: "percent" -> 83%, "score" -> 0.83 */
  display?: "percent" | "score";
  tone?: "teal" | "indigo" | "amber";
  size?: number;
}

const TONE_STROKE: Record<NonNullable<ScoreGaugeProps["tone"]>, string> = {
  teal: "#0d9488",
  indigo: "#6366f1",
  amber: "#d97706",
};

export function ScoreGauge({ value, label, display = "percent", tone = "teal", size = 108 }: ScoreGaugeProps) {
  const clamped = Math.max(0, Math.min(1, value ?? 0));
  const radius = (size - 12) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped);
  const center = size / 2;

  const centerLabel = display === "percent" ? `${Math.round(clamped * 100)}%` : clamped.toFixed(2);

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="hsl(var(--border))"
            strokeWidth={8}
          />
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={TONE_STROKE[tone]}
            strokeWidth={8}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 0.7s ease-out" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="tabular text-xl font-semibold text-foreground">{centerLabel}</span>
        </div>
      </div>
      <p className={cn("text-center text-[11px] font-medium uppercase tracking-wide text-muted-foreground")}>
        {label}
      </p>
    </div>
  );
}
