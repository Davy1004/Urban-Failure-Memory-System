/**
 * First half → second half of the window, per flagged ward.
 *
 * This chart exists to show what the detector was *measured* to do. Ranking
 * wards by a rising slope invites the reading "these wards are accelerating",
 * and that reading is not supported: flagged wards do not significantly exceed
 * their own first-half level (Wilcoxon signed-rank, p = 0.116). What does hold
 * is that they stay above the city norm — 10 of 10 finish above 1.00, at a mean
 * of 1.77 against 1.16 for all eligible wards (Mann-Whitney, p = 0.0001).
 *
 * A dumbbell is the honest form for that: it shows both levels and the distance
 * between them, so a reader can see for themselves that the second dot is high
 * rather than that it moved a long way. A slope chart or an arrow would put the
 * emphasis on the movement, which is the claim that failed.
 *
 * Two shades of one hue, not two hues — the two dots are the same quantity at
 * two times, not two different series.
 */
import { useState } from "react";

import { num } from "@/lib/format";

export interface DumbbellRow {
  ward: string;
  first: number;
  second: number;
}

const ROW_H = 26;
const PAD_TOP = 26;
const PAD_BOTTOM = 30;
const LABEL_W = 214;
const MAX_LABEL_CHARS = 26;
const VALUE_W = 46;

export function LevelDumbbell({
  rows,
  cityNorm = 1,
  comparisonMean,
  comparisonLabel = "all eligible wards",
}: {
  rows: DumbbellRow[];
  cityNorm?: number;
  comparisonMean?: number;
  comparisonLabel?: string;
}) {
  const [hover, setHover] = useState<number | null>(null);

  const width = 720;
  const plotX0 = LABEL_W;
  const plotX1 = width - VALUE_W - 8;
  const span = plotX1 - plotX0;

  const maxValue = Math.max(
    2,
    ...rows.flatMap((r) => [r.first, r.second]),
    comparisonMean ?? 0,
  );
  const domainMax = Math.ceil(maxValue * 2) / 2;
  const x = (v: number) => plotX0 + (v / domainMax) * span;
  const height = PAD_TOP + rows.length * ROW_H + PAD_BOTTOM;

  const ticks = Array.from({ length: Math.floor(domainMax * 2) + 1 }, (_, i) => i / 2);

  return (
    <figure className="m-0">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="block h-auto w-full"
        role="img"
        aria-label={
          `First-half and second-half relative index for ${rows.length} flagged wards. ` +
          `All finish above the city norm of ${num(cityNorm)}.`
        }
      >
        {/* Recessive grid. */}
        {ticks.map((t) => (
          <line
            key={t}
            x1={x(t)}
            x2={x(t)}
            y1={PAD_TOP - 8}
            y2={height - PAD_BOTTOM}
            stroke="var(--grid)"
            strokeWidth={1}
          />
        ))}

        {/* The city norm. The whole claim is "they stay above this line". */}
        <line
          x1={x(cityNorm)}
          x2={x(cityNorm)}
          y1={PAD_TOP - 14}
          y2={height - PAD_BOTTOM + 2}
          stroke="var(--text-muted)"
          strokeWidth={1.5}
        />
        <text
          x={x(cityNorm)}
          y={PAD_TOP - 18}
          fill="var(--text-secondary)"
          fontSize={11}
          textAnchor="middle"
        >
          city norm
        </text>

        {comparisonMean !== undefined ? (
          <>
            <line
              x1={x(comparisonMean)}
              x2={x(comparisonMean)}
              y1={PAD_TOP - 4}
              y2={height - PAD_BOTTOM + 2}
              stroke="var(--axis)"
              strokeWidth={1}
              strokeDasharray="0"
              opacity={0.9}
            />
            <text
              x={x(comparisonMean)}
              y={height - PAD_BOTTOM + 26}
              fill="var(--text-muted)"
              fontSize={10}
              textAnchor="middle"
            >
              {comparisonLabel} {num(comparisonMean)}
            </text>
          </>
        ) : null}

        {rows.map((r, i) => {
          const y = PAD_TOP + i * ROW_H + ROW_H / 2;
          const active = hover === i;
          return (
            <g
              key={r.ward}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(i)}
              onBlur={() => setHover(null)}
              tabIndex={0}
              role="listitem"
              aria-label={`${r.ward}: first half ${num(r.first)}, second half ${num(r.second)}`}
              style={{ outline: "none" }}
            >
              {/* A full-row hit target, so nobody has to land on an 8px dot. */}
              <rect
                x={0}
                y={y - ROW_H / 2}
                width={width}
                height={ROW_H}
                fill={active ? "var(--surface-page)" : "transparent"}
              />
              <text
                x={plotX0 - 10}
                y={y + 4}
                fill="var(--text-primary)"
                fontSize={12}
                textAnchor="end"
              >
                {/* Ward names run to 27 characters ("Dharmarayaswamy Temple
                    Ward"). Anchored at the end, an over-long one runs off the
                    left of the viewBox and is silently clipped, so truncate
                    explicitly and keep the full name reachable. */}
                <title>{r.ward}</title>
                {r.ward.length > MAX_LABEL_CHARS
                  ? `${r.ward.slice(0, MAX_LABEL_CHARS - 1)}…`
                  : r.ward}
              </text>
              <line
                x1={x(r.first)}
                x2={x(r.second)}
                y1={y}
                y2={y}
                stroke="var(--series-1)"
                strokeWidth={2}
                opacity={0.45}
              />
              {/* First half: the lighter shade. */}
              <circle
                cx={x(r.first)}
                cy={y}
                r={4.5}
                fill="var(--series-1-muted)"
                stroke="var(--surface-1)"
                strokeWidth={2}
              />
              {/* Second half: the value the claim is about. */}
              <circle
                cx={x(r.second)}
                cy={y}
                r={5}
                fill="var(--series-1)"
                stroke="var(--surface-1)"
                strokeWidth={2}
              />
              <text
                x={plotX1 + 10}
                y={y + 4}
                fill="var(--text-primary)"
                fontSize={12}
                fontWeight={active ? 700 : 500}
                textAnchor="start"
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {num(r.second)}
              </text>
            </g>
          );
        })}

        {/* Axis. */}
        <line
          x1={plotX0}
          x2={plotX1}
          y1={height - PAD_BOTTOM}
          y2={height - PAD_BOTTOM}
          stroke="var(--axis)"
          strokeWidth={1}
        />
        {ticks.map((t) => (
          <text
            key={t}
            x={x(t)}
            y={height - PAD_BOTTOM + 14}
            fill="var(--text-muted)"
            fontSize={10}
            textAnchor="middle"
            style={{ fontVariantNumeric: "tabular-nums" }}
          >
            {num(t, 1)}
          </text>
        ))}
      </svg>

      {/* Two marks on screen, so the legend is present. */}
      <div className="mt-2 flex flex-wrap items-center gap-4">
        <span className="flex items-center gap-1.5 text-[12px] text-[var(--text-secondary)]">
          <span
            aria-hidden
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{
              background: "var(--series-1-muted)",
              boxShadow: "0 0 0 2px var(--surface-1)",
            }}
          />
          First half
        </span>
        <span className="flex items-center gap-1.5 text-[12px] text-[var(--text-secondary)]">
          <span
            aria-hidden
            className="inline-block h-3 w-3 rounded-full"
            style={{ background: "var(--series-1)" }}
          />
          Second half
        </span>
      </div>
    </figure>
  );
}
