"use client";

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import type { CalibrationMetrics } from "@/types/clinical";
import { cn } from "@/lib/utils";

function PenaltyRow({ label, value }: { label: string; value: number }) {
  const isDeduction = value < 0;
  const isNeutral = value === 0;
  return (
    <div className="flex items-center justify-between border-b border-border/60 py-2 text-sm last:border-b-0">
      <span className="text-muted-foreground">{label.replace(/_/g, " ")}</span>
      <span
        className={cn(
          "tabular font-mono text-sm font-medium",
          isNeutral ? "text-muted-foreground" : isDeduction ? "text-rose-400" : "text-teal-400",
        )}
      >
        {isNeutral ? "0.00" : value > 0 ? `+${value.toFixed(2)}` : value.toFixed(2)}
      </span>
    </div>
  );
}

export function CalibrationAccordion({ breakdown }: { breakdown: CalibrationMetrics | null | undefined }) {
  if (!breakdown) {
    return (
      <p className="rounded-md border border-dashed border-border p-4 text-xs text-muted-foreground">
        No calibration breakdown was returned for this evaluation.
      </p>
    );
  }

  const penaltyEntries = Object.entries(breakdown.gating_penalties ?? {});

  return (
    <Accordion type="single" collapsible defaultValue="calibration">
      <AccordionItem value="calibration" className="border-none">
        <AccordionTrigger className="rounded-md border border-border bg-muted/20 px-4 py-3 hover:no-underline">
          Calibration Transparency
        </AccordionTrigger>
        <AccordionContent className="px-1 pt-3">
          <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className="font-medium text-foreground">Method:</span>
            {breakdown.metric_calibration_method}
          </div>
          <div className="rounded-md border border-border bg-surface-raised px-4">
            {penaltyEntries.length > 0 ? (
              penaltyEntries.map(([key, value]) => <PenaltyRow key={key} label={key} value={value} />)
            ) : (
              <p className="py-3 text-xs text-muted-foreground">No itemized penalties reported.</p>
            )}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
