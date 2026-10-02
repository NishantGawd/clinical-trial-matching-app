import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { HeartHandshake, Car, Activity, Dumbbell, BatteryLow, ClipboardList } from "lucide-react";
import type { ActionableIntervention } from "@/types/clinical";

const TYPE_ICON: Record<string, React.ElementType> = {
  "Caregiver Support": HeartHandshake,
  "Transportation Assistance": Car,
  "Toxicity Monitoring": Activity,
  "Functional Rehabilitation": Dumbbell,
  "Treatment Fatigue Support": BatteryLow,
};

export function InterventionList({ interventions }: { interventions: ActionableIntervention[] }) {
  if (interventions.length === 0) {
    return (
      <p className="rounded-md border border-dashed border-border p-4 text-xs text-muted-foreground">
        No targeted navigation interventions were flagged for this patient&rsquo;s baseline profile.
      </p>
    );
  }

  return (
    <Accordion type="multiple" defaultValue={[interventions[0]?.intervention_type]}>
      {interventions.map((item, idx) => {
        const Icon = TYPE_ICON[item.intervention_type] ?? ClipboardList;
        return (
          <AccordionItem key={`${item.intervention_type}-${idx}`} value={item.intervention_type}>
            <AccordionTrigger>
              <span className="flex items-center gap-2.5">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-indigo-500/10 text-indigo-400">
                  <Icon className="h-3.5 w-3.5" />
                </span>
                {item.intervention_type}
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <p className="mb-2 text-sm text-muted-foreground">{item.description}</p>
              <div className="rounded-md border border-border bg-surface-raised px-3 py-2">
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Implementation
                </p>
                <p className="mt-0.5 text-sm text-foreground">
                  {item.implementation_details || "Coordinate clinical and logistical trial support."}
                </p>
              </div>
            </AccordionContent>
          </AccordionItem>
        );
      })}
    </Accordion>
  );
}
