"use client";

import { CohortExplorer } from "@/components/explore/CohortExplorer";
import { usePatients, useTrials } from "@/hooks/useClinicalData";

export default function ExplorePage() {
  const patients = usePatients(200);
  const trials = useTrials(200);

  return (
    <div className="container flex flex-col gap-8 py-8">
      <div>
        <h1 className="text-balance text-2xl font-semibold text-foreground">Cohort &amp; Protocol Explorer</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Browse every indexed patient record and trial protocol, with an instant full-text preview.
        </p>
      </div>

      <CohortExplorer
        patients={patients.items}
        patientsLoading={patients.loading}
        patientsError={patients.error}
        trials={trials.items}
        trialsLoading={trials.loading}
        trialsError={trials.error}
        onRefresh={() => {
          patients.refresh();
          trials.refresh();
        }}
      />
    </div>
  );
}
