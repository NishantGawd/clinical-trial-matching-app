import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Formats a 0..1 fraction as a percentage string, e.g. 0.837 -> "83.7%" */
export function toPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

/** Formats a 0..1 continuous score as "0.83" */
export function toScore(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

/** Parses a backend "66.2%" style string into a numeric 0..100 value */
export function parsePercentString(value: string | null | undefined): number {
  if (!value) return 0;
  const parsed = parseFloat(value.replace("%", "").trim());
  return Number.isNaN(parsed) ? 0 : parsed;
}

export function truncate(text: string, max = 160): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max).trimEnd()}…`;
}

/** Normalizes has_caregiver, which the backend sends as 0/1 in some places and boolean in others */
export function isTruthyFlag(value: number | boolean | undefined | null): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value === 1;
  return false;
}

export function riskLevelTone(level: string | null | undefined): "pass" | "warn" | "fail" | "neutral" {
  switch ((level || "").toUpperCase()) {
    case "LOW":
      return "pass";
    case "MEDIUM":
      return "warn";
    case "HIGH":
      return "fail";
    default:
      return "neutral";
  }
}

export function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
