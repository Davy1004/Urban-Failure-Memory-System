/**
 * The relative flooding index over 20 quarters, against the city norm.
 *
 * One series, so no legend box — the title names it. The reference line at
 * 1.00 is not decoration and is not optional: `rel` is a ratio benchmarked to
 * the citywide complaint mix, so the line is what the number means. Without it
 * the series is an unlabelled curve and a reader has no way to tell a ward
 * doing badly from a ward doing normally.
 *
 * The tooltip carries the inputs — event-days, the ward's total complaints, and
 * what the citywide mix predicts — because the index is a benchmarked ratio and
 * a reader who cannot see the denominator cannot tell a ward that flooded more
 * from a ward that complained less.
 */
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { IndexPoint } from "@/lib/api";
import { num } from "@/lib/format";

interface TooltipProps {
  active?: boolean;
  payload?: { payload: IndexPoint }[];
}

function IndexTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const above = p.rel_index >= 1;
  return (
    <div className="rounded-md border border-[var(--border-strong)] bg-[var(--surface-1)] px-3 py-2 text-[12px] shadow-sm">
      <div className="mb-1 font-semibold text-[var(--text-primary)]">{p.period}</div>
      <dl className="grid grid-cols-[auto_auto] gap-x-3 gap-y-0.5 text-[var(--text-secondary)]">
        <dt>Relative index</dt>
        <dd className="text-right font-semibold tabular-nums text-[var(--text-primary)]">
          {num(p.rel_index)}
        </dd>
        <dt>Flooding event-days</dt>
        <dd className="text-right tabular-nums">{p.event_days}</dd>
        <dt>City mix predicts</dt>
        <dd className="text-right tabular-nums">{num(p.expected_event_days, 1)}</dd>
        <dt>All complaints</dt>
        <dd className="text-right tabular-nums">
          {p.total_complaints.toLocaleString("en-IN")}
        </dd>
      </dl>
      <div className="mt-1.5 border-t border-[var(--border)] pt-1.5 text-[11px] text-[var(--text-muted)]">
        {above ? "Above" : "Below"} the city norm this quarter
      </div>
    </div>
  );
}

export function IndexChart({
  points,
  height = 300,
}: {
  points: IndexPoint[];
  height?: number;
}) {
  const max = Math.max(1.6, ...points.map((p) => p.rel_index));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart
        data={points}
        // Room on the right for the reference-line label to sit OUTSIDE the
        // plot. Inside, it lands on the series wherever the ward happens to
        // be near the city norm at the end of the window.
        margin={{ top: 8, right: 96, bottom: 4, left: 0 }}
      >
        <CartesianGrid stroke="var(--grid)" vertical={false} />
        <XAxis
          dataKey="period"
          tickLine={false}
          axisLine={{ stroke: "var(--axis)" }}
          interval="preserveStartEnd"
          minTickGap={24}
        />
        <YAxis
          domain={[0, Math.ceil(max * 10) / 10]}
          tickLine={false}
          axisLine={false}
          width={42}
          tickFormatter={(v: number) => num(v, 1)}
        />
        <ReferenceLine
          y={1}
          stroke="var(--text-muted)"
          strokeWidth={1.5}
          label={{
            value: "1.00  city norm",
            position: "right",
            fill: "var(--text-secondary)",
            fontSize: 11,
          }}
        />
        <Tooltip
          content={<IndexTooltip />}
          cursor={{ stroke: "var(--axis)", strokeWidth: 1 }}
        />
        <Line
          type="monotone"
          dataKey="rel_index"
          name="Relative flooding index"
          stroke="var(--series-1)"
          strokeWidth={2}
          dot={{ r: 4, fill: "var(--series-1)", strokeWidth: 0 }}
          activeDot={{
            r: 6,
            fill: "var(--series-1)",
            stroke: "var(--surface-1)",
            strokeWidth: 2,
          }}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
