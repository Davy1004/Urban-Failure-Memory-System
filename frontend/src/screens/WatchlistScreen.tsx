/**
 * Screen 2 — the standing watchlist.
 *
 * A standing watchlist, never a prediction and never a forecast. It is ranked
 * on how often each ward has flooded before and it does not change with
 * tonight's weather — re-ranking it daily on three further years of history
 * moves precision@20 by 0.15 points, and weather alone ranks at chance
 * (5.63% against a 4.79% random floor).
 *
 * The achieved figure is rendered as a mark on a scale that ends at the oracle
 * ceiling, not as a stat tile. See `PrecisionScale` for why.
 */
import { PrecisionScale } from "@/components/charts/PrecisionScale";
import {
  Badge,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Empty,
  ErrorState,
  Loading,
  Table,
  Td,
  Th,
} from "@/components/ui";
import { fetchWatchlist } from "@/lib/api";
import { date, pct } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";

export function WatchlistScreen() {
  const { data, error, loading } = useAsync(fetchWatchlist, []);

  if (loading) return <Loading label="Loading the watchlist" />;
  if (error) return <ErrorState error={error} />;
  if (!data) return null;

  const { context: ctx, items } = data;
  const scored =
    ctx.precision_at_k !== null &&
    ctx.oracle_at_k !== null &&
    ctx.random_at_k !== null;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">
          Standing watchlist
        </h1>
        <p className="mt-1 max-w-3xl text-[13px] leading-relaxed text-[var(--text-secondary)]">
          The {data.k} wards with the most flooding event-days on record, frozen
          at {date(data.as_of_date)} and not re-ranked since. This is the list an
          officer already has — it is the baseline the project measures against,
          not a forecast of tonight.
        </p>
      </div>

      <Card>
        <CardHeader
          title={`How good is this list?`}
          description={
            scored
              ? `Measured on ${ctx.test_rain_days} held-out rain days after the freeze date, carrying ${ctx.test_events?.toLocaleString("en-IN")} flooding event-days citywide.`
              : undefined
          }
        />
        <CardBody>
          {scored ? (
            <PrecisionScale
              achieved={ctx.precision_at_k as number}
              ceiling={ctx.oracle_at_k as number}
              floor={ctx.random_at_k as number}
              k={data.k}
            />
          ) : (
            <Empty
              title="This snapshot has not been scored"
              hint="It was frozen without a held-out window, so there is no measured precision, ceiling or floor to show. Nothing is estimated in their place."
            />
          )}
        </CardBody>
      </Card>

      {scored ? (
        <Callout tone="info" title="Reading the figure">
          {ctx.reading}
        </Callout>
      ) : null}

      <Card>
        <CardHeader
          title={`The ${data.k} wards`}
          description="Ranked on flooding event-days up to the freeze date — that count is the entire ranking key. The right-hand column is what actually happened afterwards, on the held-out rain days."
          actions={
            <div className="flex flex-wrap items-center justify-end gap-1.5">
              <Badge tone="neutral">
                trained {date(data.train_start)} – {date(data.as_of_date)}
              </Badge>
              {ctx.test_start && ctx.test_end ? (
                <Badge tone="neutral">
                  tested {date(ctx.test_start)} – {date(ctx.test_end)}
                </Badge>
              ) : null}
            </div>
          }
        />
        <CardBody>
          {items.length === 0 ? (
            <Empty
              title="This snapshot has no wards"
              hint="Rebuild the derived tables with `python -m app.ingestion.cli derive`."
            />
          ) : (
            <Table>
              <caption className="sr-only">
                The frozen top {data.k} wards with their prior and held-out
                flooding event-days.
              </caption>
              <thead>
                <tr>
                  <Th numeric>#</Th>
                  <Th>Ward</Th>
                  <Th>Zone</Th>
                  <Th numeric>Event-days on record</Th>
                  <Th numeric>On held-out rain days</Th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <tr key={it.location_id} className="hover:bg-[var(--surface-page)]">
                    <Td numeric className="text-[var(--text-muted)]">
                      {it.rank_position}
                    </Td>
                    <Td className="font-medium">{it.ward}</Td>
                    <Td className="text-[var(--text-secondary)]">{it.zone ?? "—"}</Td>
                    <Td numeric>{it.prior_events}</Td>
                    <Td numeric className="text-[var(--text-secondary)]">
                      {it.test_events ?? "—"}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </CardBody>
      </Card>

      <Callout tone="warning" title="What this list is not">
        It is not a prediction and it does not change with the forecast. A ranking
        built from rainfall alone scores{" "}
        {ctx.random_at_k !== null ? `close to the ${pct(ctx.random_at_k)} random floor` : "at chance"}
        , and a ward-level ranking fitted with perfect foresight of the test
        period reaches only 15.66% against this list's{" "}
        {ctx.precision_at_k !== null ? pct(ctx.precision_at_k) : "measured score"} —
        so almost none of the remaining headroom is reachable by re-ordering
        wards at all.
      </Callout>
    </div>
  );
}
