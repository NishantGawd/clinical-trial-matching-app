import { Network, Gauge, LineChart, FileSearch } from "lucide-react";

const FEATURES = [
  {
    icon: Network,
    accent: "teal" as const,
    title: "Multi-Agent Reasoning Swarm",
    description:
      "Dedicated inclusion and exclusion agents evaluate criteria concurrently, a critic auditor verifies every claim against the source record, and a synthesis stage produces one calibrated decision.",
  },
  {
    icon: Gauge,
    accent: "indigo" as const,
    title: "Calibrated Confidence Scoring",
    description:
      "Eligibility scores are anchored to empirical extraction confidence, then adjusted with itemized physiological gating penalties — never a black-box number.",
  },
  {
    icon: LineChart,
    accent: "amber" as const,
    title: "ML Attrition & Retention Modeling",
    description:
      "A calibrated soft-voting ensemble across gradient-boosted and random-forest models predicts dropout risk, with per-feature drivers surfaced through SHAP explainability.",
  },
  {
    icon: FileSearch,
    accent: "rose" as const,
    title: "Explainable Audit Trail",
    description:
      "Every match ships with inclusion/exclusion disposition, auditor verification notes, and — on disqualification — ranked alternative protocols your team can pivot to instantly.",
  },
];

const ACCENT_CLASSES: Record<string, string> = {
  teal: "bg-gradient-to-br from-teal-500 to-teal-700",
  indigo: "bg-gradient-to-br from-indigo-500 to-indigo-700",
  amber: "bg-gradient-to-br from-amber-500 to-amber-600",
  rose: "bg-gradient-to-br from-rose-500 to-rose-600",
};

export function FeatureGrid() {
  return (
    <section id="platform" className="border-t border-border bg-muted/10 py-20">
      <div className="container">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-balance text-3xl font-bold tracking-tight text-foreground">
            Built for defensible clinical decisions
          </h2>
          <p className="mt-3 text-balance text-muted-foreground">
            Every score, status, and recommendation on this platform traces back to a documented, auditable step in
            the reasoning pipeline.
          </p>
        </div>

        <div className="mx-auto mt-12 grid max-w-5xl grid-cols-1 gap-5 sm:grid-cols-2">
          {FEATURES.map((feature) => (
            <div
              key={feature.title}
              className="group rounded-xl border border-border bg-surface p-6 shadow-panel transition-shadow hover:shadow-panel-lift"
            >
              <span
                className={`flex h-11 w-11 items-center justify-center rounded-xl text-white shadow-panel ${ACCENT_CLASSES[feature.accent]}`}
              >
                <feature.icon className="h-5 w-5" />
              </span>
              <h3 className="mt-4 text-base font-semibold text-foreground">{feature.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
