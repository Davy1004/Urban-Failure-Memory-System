/** Number formatting, in one place so a figure reads the same on every screen. */

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** A proportion as a percentage. Two decimals is the project's convention:
 *  14.08%, not 14% — the second decimal is the difference between the ERA5 and
 *  IFS bases and the paper quotes it. */
export function pct(value: number, digits = 2): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function num(value: number, digits = 2): string {
  return value.toFixed(digits);
}

/** Signed, for a slope or a delta where the direction is the whole point. */
export function signed(value: number, digits = 3): string {
  return `${value >= 0 ? "+" : "−"}${Math.abs(value).toFixed(digits)}`;
}

/**
 * A p-value, never bare. Below 0.001 it is reported as an inequality rather
 * than a spuriously precise decimal.
 */
export function pval(p: number): string {
  if (p < 0.0001) return "p < 0.0001";
  if (p < 0.001) return "p < 0.001";
  return `p = ${p.toFixed(p < 0.01 ? 4 : 3)}`;
}

/** Indian rupees, in the units a municipal budget is actually discussed in. */
export function inr(value: number): string {
  if (value === 0) return "₹0";
  if (value >= 1e7) return `₹${(value / 1e7).toFixed(2)} Cr`;
  if (value >= 1e5) return `₹${(value / 1e5).toFixed(1)} L`;
  return `₹${Math.round(value).toLocaleString("en-IN")}`;
}

export function compactInr(value: number): string {
  if (value === 0) return "₹0";
  if (value >= 1e7) return `₹${(value / 1e7).toFixed(0)}Cr`;
  if (value >= 1e5) return `₹${(value / 1e5).toFixed(0)}L`;
  return `₹${Math.round(value / 1000)}k`;
}

export function date(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
