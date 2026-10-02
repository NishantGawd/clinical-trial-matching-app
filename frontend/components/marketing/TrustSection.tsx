import { ShieldCheck, Eye, UserCheck } from "lucide-react";

const POINTS = [
  {
    icon: ShieldCheck,
    title: "Investigational decision support",
    description:
      "Classified and operated as SaMD Class II investigational software. Every output requires clinical verification before any enrollment or treatment decision.",
  },
  {
    icon: Eye,
    title: "Nothing is a black box",
    description:
      "Calibration penalties, inclusion/exclusion disposition, and attrition risk drivers are all itemized and visible — not summarized away.",
  },
  {
    icon: UserCheck,
    title: "Built for clinician review",
    description:
      "The audit trail is designed to be read and challenged by a clinical team, not just logged for compliance.",
  },
];

export function TrustSection() {
  return (
    <section id="trust" className="border-t border-border bg-muted/10 py-20">
      <div className="container">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-balance text-3xl font-bold tracking-tight text-foreground">
            Compliance is a feature, not an afterthought
          </h2>
        </div>
        <div className="mx-auto mt-12 grid max-w-4xl grid-cols-1 gap-6 sm:grid-cols-3">
          {POINTS.map((point) => (
            <div key={point.title} className="flex flex-col items-center gap-3 text-center">
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-teal-500/10 text-teal-400 ring-1 ring-inset ring-teal-600/25">
                <point.icon className="h-5 w-5" />
              </span>
              <h3 className="text-sm font-semibold text-foreground">{point.title}</h3>
              <p className="text-xs leading-relaxed text-muted-foreground">{point.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
