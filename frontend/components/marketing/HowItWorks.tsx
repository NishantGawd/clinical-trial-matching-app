import { Database, ShieldCheck, ShieldX, Gavel, Sigma } from "lucide-react";

const STEPS = [
  {
    icon: Database,
    title: "Retrieval & Cache",
    description:
      "The patient record and trial protocol are pulled from the vector store; a prior evaluation is served instantly if one already exists.",
  },
  {
    icon: ShieldCheck,
    title: "Inclusion & Exclusion Agents",
    description:
      "Two agents work concurrently — one confirms disease-specific inclusion criteria, the other screens for disqualifying contraindications.",
  },
  {
    icon: Gavel,
    title: "Critic Auditor",
    description:
      "A dedicated auditor agent verifies both agents' reasoning against the source clinical text before anything is finalized.",
  },
  {
    icon: Sigma,
    title: "Synthesis & ML Scoring",
    description:
      "A calibrated eligibility score and an ML-driven attrition risk profile are synthesized into one explainable report.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-border py-20">
      <div className="container">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-balance text-3xl font-bold tracking-tight text-foreground">How a match runs</h2>
          <p className="mt-3 text-balance text-muted-foreground">
            One request, four coordinated reasoning stages, one calibrated decision.
          </p>
        </div>

        <div className="relative mx-auto mt-14 grid max-w-5xl grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, i) => (
            <div key={step.title} className="relative flex flex-col items-center text-center">
              {i < STEPS.length - 1 && (
                <div className="absolute left-1/2 top-7 hidden h-px w-full -translate-y-1/2 bg-border lg:block" />
              )}
              <div className="relative z-10 flex h-14 w-14 items-center justify-center rounded-full border border-teal-600/30 bg-surface text-teal-400 shadow-panel">
                <step.icon className="h-5 w-5" />
                <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-teal-600 text-[10px] font-bold text-white">
                  {i + 1}
                </span>
              </div>
              <h3 className="mt-4 text-sm font-semibold text-foreground">{step.title}</h3>
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
