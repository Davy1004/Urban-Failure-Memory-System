/**
 * Drainage spend against one ward attribute. Two of these side by side are the
 * allocation finding: money tracks ward SIZE, not flooding NEED.
 *
 * Two separate charts rather than one with two y-axes. A dual-axis plot would
 * let the two scales be aligned arbitrarily and invent a relationship that is
 * not in the data — and "these two look different" is the entire point here, so
 * a chart form that can fake agreement is disqualified.
 *
 * **No fitted trend line.** The dose-response of the change in index on spend
 * is retracted (it does not survive dropping the seven zero-dose wards), and a
 * regression line through a scatter is read as an effect estimate whatever the
 * caption says. Each panel carries its Spearman ρ and p instead — a rank
 * correlation is a description of the scatter, not a model of it.
 *
 * Spend is on a log axis because it spans ₹0 to ₹63 crore; on a linear axis
 * ninety wards pile into the first tenth of the plot and the shape is unreadable.
 * Untreated wards (spend = ₹0) cannot be placed on a log axis at all, so they
 * are drawn in a separate marked lane rather than silently dropped — the seven
 * of them are the reason the published outcome estimate was retracted.
 */
import { useState } from "react";

import type { Correlation } from "@/lib/api";
import { compactInr, inr, num, pval } from "@/lib/format";

export interface ScatterPoint {
  ward: string;
  spend: number;
  value: number | null;
  treated: boolean;
}

const W = 460;
const H = 300;
const PAD = { top: 12, right: 14, bottom: 46, left: 52 };
const ZERO_LANE = 34;

function niceTicks(min: number, max: number, count = 5): number[] {
  if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) return [min];
  const raw = (max - min) / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? mag * 10;
  const start = Math.ceil(min / step) * step;
  const out: number[] = [];
  for (let v = start; v <= max + step / 2; v += step) out.push(Number(v.toFixed(10)));
  return out;
}

export function AllocationScatter({
  points,
  yLabel,
  yUnit,
  correlation,
  yReference,
  yReferenceLabel,
}: {
  points: ScatterPoint[];
  yLabel: string;
  yUnit?: string;
  correlation: Correlation;
  /** A horizontal reference where the y quantity has a meaningful level. */
  yReference?: number;
  yReferenceLabel?: string;
}) {
  const [hover, setHover] = useState<number | null>(null);

  const usable = points.filter((p) => p.value !== null) as (ScatterPoint & {
    value: number;
  })[];
  const treated = usable.filter((p) => p.treated && p.spend > 0);
  const untreated = usable.filter((p) => !p.treated || p.spend <= 0);

  const yMin = Math.min(...usable.map((p) => p.value));
  const yMax = Math.max(...usable.map((p) => p.value));
  const yPad = (yMax - yMin) * 0.08 || 1;
  const y0 = yMin - yPad;
  const y1 = yMax + yPad;

  const spends = treated.map((p) => p.spend);
  const lx0 = Math.log10(Math.max(1, Math.min(...spends)));
  const lx1 = Math.log10(Math.max(...spends));

  const plotLeft = PAD.left + (untreated.length ? ZERO_LANE : 0);
  const plotRight = W - PAD.right;
  const plotTop = PAD.top;
  const plotBottom = H - PAD.bottom;

  const sx = (spend: number) =>
    plotLeft + ((Math.log10(spend) - lx0) / (lx1 - lx0)) * (plotRight - plotLeft);
  const sy = (v: number) =>
    plotBottom - ((v - y0) / (y1 - y0)) * (plotBottom - plotTop);
  const zeroX = PAD.left + ZERO_LANE / 2;

  const yTicks = niceTicks(y0, y1, 4);
  const decades: number[] = [];
  for (let d = Math.ceil(lx0); d <= Math.floor(lx1); d += 1) decades.push(10 ** d);

  const active = hover === null ? null : usable[hover];

  return (
    <figure className="m-0">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="block h-auto w-full"
        role="img"
        aria-label={
          `Drainage spend against ${yLabel} for ${usable.length} wards. ` +
          `Spearman rho ${num(correlation.rho, 3)}, ${pval(correlation.p)}.`
        }
      >
        {yTicks.map((t) => (
          <g key={t}>
            <line
              x1={PAD.left}
              x2={plotRight}
              y1={sy(t)}
              y2={sy(t)}
              stroke="var(--grid)"
              strokeWidth={1}
            />
            <text
              x={PAD.left - 8}
              y={sy(t) + 3.5}
              fill="var(--text-muted)"
              fontSize={10}
              textAnchor="end"
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {Math.abs(t) >= 1000 ? t.toLocaleString("en-IN") : num(t, 1)}
            </text>
          </g>
        ))}

        {yReference !== undefined ? (
          <>
            <line
              x1={PAD.left}
              x2={plotRight}
              y1={sy(yReference)}
              y2={sy(yReference)}
              stroke="var(--text-muted)"
              strokeWidth={1.5}
            />
            {yReferenceLabel ? (
              <text
                x={plotRight}
                y={sy(yReference) - 5}
                fill="var(--text-secondary)"
                fontSize={10}
                textAnchor="end"
              >
                {yReferenceLabel}
              </text>
            ) : null}
          </>
        ) : null}

        {/* The zero-spend lane, kept visibly apart from the log axis. */}
        {untreated.length ? (
          <>
            <line
              x1={PAD.left + ZERO_LANE}
              x2={PAD.left + ZERO_LANE}
              y1={plotTop}
              y2={plotBottom}
              stroke="var(--axis)"
              strokeWidth={1}
            />
            <text
              x={zeroX}
              y={plotBottom + 14}
              fill="var(--text-muted)"
              fontSize={10}
              textAnchor="middle"
            >
              ₹0
            </text>
            <text
              x={zeroX}
              y={plotBottom + 26}
              fill="var(--text-muted)"
              fontSize={9}
              textAnchor="middle"
            >
              ({untreated.length})
            </text>
          </>
        ) : null}

        {decades.map((d) => (
          <text
            key={d}
            x={sx(d)}
            y={plotBottom + 14}
            fill="var(--text-muted)"
            fontSize={10}
            textAnchor="middle"
          >
            {compactInr(d)}
          </text>
        ))}

        <line
          x1={PAD.left}
          x2={plotRight}
          y1={plotBottom}
          y2={plotBottom}
          stroke="var(--axis)"
          strokeWidth={1}
        />

        {usable.map((p, i) => {
          const isZero = !p.treated || p.spend <= 0;
          const cx = isZero ? zeroX : sx(p.spend);
          const cy = sy(p.value);
          const on = hover === i;
          return (
            <g
              key={p.ward}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(i)}
              onBlur={() => setHover(null)}
              tabIndex={0}
              aria-label={`${p.ward}: ${inr(p.spend)}, ${yLabel} ${num(p.value)}`}
              style={{ outline: "none" }}
            >
              {/* A 24px hit target around an 9px mark. */}
              <circle cx={cx} cy={cy} r={12} fill="transparent" />
              <circle
                cx={cx}
                cy={cy}
                r={on ? 6 : 4.5}
                fill={isZero ? "var(--surface-1)" : "var(--series-1)"}
                stroke={isZero ? "var(--series-1)" : "var(--surface-1)"}
                strokeWidth={2}
                fillOpacity={isZero ? 1 : 0.85}
              />
            </g>
          );
        })}

        <text
          x={(plotLeft + plotRight) / 2}
          y={H - 6}
          fill="var(--text-secondary)"
          fontSize={11}
          textAnchor="middle"
        >
          Drainage spend, log scale
        </text>
        <text
          x={12}
          y={(plotTop + plotBottom) / 2}
          fill="var(--text-secondary)"
          fontSize={11}
          textAnchor="middle"
          transform={`rotate(-90 12 ${(plotTop + plotBottom) / 2})`}
        >
          {yLabel}
          {yUnit ? ` (${yUnit})` : ""}
        </text>
      </svg>

      <div className="mt-1 min-h-[34px] text-[12px] leading-snug">
        {active ? (
          <span className="text-[var(--text-primary)]">
            <strong className="font-semibold">{active.ward}</strong> — {inr(active.spend)},{" "}
            {yLabel.toLowerCase()} {num(active.value)}
            {active.treated ? "" : " · no drainage work in the window"}
          </span>
        ) : (
          <span className="text-[var(--text-muted)]">
            Spearman ρ ={" "}
            <strong className="font-semibold text-[var(--text-secondary)] tabular-nums">
              {num(correlation.rho, 3)}
            </strong>
            , {pval(correlation.p)} · hover a ward for its values
          </span>
        )}
      </div>
    </figure>
  );
}
