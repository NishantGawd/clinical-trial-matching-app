import { ShieldAlert } from "lucide-react";
import { COMPLIANCE_NOTICE } from "@/lib/constants";

export function ComplianceBanner() {
  return (
    <div className="flex items-center justify-center gap-2 border-b border-amber-600/20 bg-amber-500/[0.06] px-4 py-2 text-center">
      <ShieldAlert className="h-3.5 w-3.5 shrink-0 text-amber-500" />
      <p className="text-[11px] font-medium leading-none text-amber-500/90">
        {COMPLIANCE_NOTICE}
      </p>
    </div>
  );
}
