"use client";

import { RadialBar, RadialBarChart, PolarAngleAxis, ResponsiveContainer } from "recharts";
import { Badge } from "@/components/ui/badge";
import { cn, riskLevelTone } from "@/lib/utils";
import type { AttritionRiskLevel } from "@/types/clinical";

const TONE_COLOR: Record<string, string> = {
  pass: "#0d9488",
  warn: "#d97706",
  fail: "#e11d48",
  neutral: "#6366f1",
};

export function DropoutRadialBar({
  probabilityPercent,
  riskLevel,
}: {
  /** Raw 0..1 probability */
  probabilityPercent: number;
  riskLevel: AttritionRiskLevel | null | undefined;
}) {
  const pct = Math.round(Math.max(0, Math.min(1, probabilityPercent)) * 100);
  const tone = riskLevelTone(riskLevel);
  const color = TONE_COLOR[tone];

  const data = [{ name: "dropout", value: pct, fill: color }];

  return (
    <div className="flex items-center gap-5">
      <div className="relative h-32 w-32 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            innerRadius="72%"
            outerRadius="100%"
            data={data}
            startAngle={90}
            endAngle={-270}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
            <RadialBar background={{ fill: "hsl(var(--muted))" }} dataKey="value" cornerRadius={8} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="tabular text-2xl font-bold text-foreground">{pct}%</span>
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground">Dropout</span>
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Attrition Risk Category</p>
        <Badge variant={tone === "neutral" ? "info" : tone} className="w-fit px-2.5 py-1 text-sm">
          {(riskLevel || "UNKNOWN").toString().toUpperCase()}
        </Badge>
        <p className={cn("max-w-[16rem] text-xs text-muted-foreground")}>
          Calibrated soft-voting probability across the LightGBM / XGBoost / Random Forest ensemble.
        </p>
      </div>
    </div>
  );
}
