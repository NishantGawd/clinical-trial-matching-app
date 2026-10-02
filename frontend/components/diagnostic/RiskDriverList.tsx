import { TrendingUp, TrendingDown } from "lucide-react";

export function RiskDriverList({
  riskDrivers,
  retentionDrivers,
}: {
  riskDrivers: string[];
  retentionDrivers: string[];
}) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div>
        <div className="mb-2 flex items-center gap-1.5">
          <TrendingUp className="h-3.5 w-3.5 text-rose-400" />
          <p className="text-xs font-medium uppercase tracking-wide text-rose-400">Elevating Risk</p>
        </div>
        <ul className="flex flex-col gap-1.5">
          {riskDrivers.map((driver, i) => (
            <li
              key={i}
              className="rounded-md border border-rose-600/25 bg-rose-500/[0.06] px-3 py-2 text-xs leading-snug text-rose-300/90"
            >
              {driver}
            </li>
          ))}
        </ul>
      </div>
      <div>
        <div className="mb-2 flex items-center gap-1.5">
          <TrendingDown className="h-3.5 w-3.5 text-teal-400" />
          <p className="text-xs font-medium uppercase tracking-wide text-teal-400">Retention Buffers</p>
        </div>
        <ul className="flex flex-col gap-1.5">
          {retentionDrivers.map((driver, i) => (
            <li
              key={i}
              className="rounded-md border border-teal-600/25 bg-teal-500/[0.06] px-3 py-2 text-xs leading-snug text-teal-300/90"
            >
              {driver}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
