/**
 * Screen 3 — the emerging watch.
 *
 * Three things on this screen are not presentation choices.
 *
 * **The label.** `chronically_above_norm`, rendered as "chronically above
 * norm". Never "accelerating" — flagged wards do not significantly exceed their
 * own first-half level (Wilcoxon signed-rank, p = 0.116). This output was
 * nearly retracted for exactly that overclaim.
 *
 * **`ground_truth_available: false`, on the screen.** The register KMLs carry
 * no year, so `first_listed_year` is NULL for all 398 points and there is no
 * way to check a flag against the city's own additions. A screen that implies
 * a flag has been confirmed is claiming something that cannot be checked.
 *
 * **The caveats are rendered, not stored.** They arrive as a required response
 * field and every one of them is displayed.
 */
import { LevelDumbbell } from "@/components/charts/LevelDumbbell";
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
import { fetchEmerging } from "@/lib/api";
import { num, pval, signed } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";

const LABEL_TEXT: Record<string, string> = {
  chronically_above_norm: "chronically above norm",
};

export function EmergingScreen() {
  const { data, error, loading } = useAsync(fetchEmerging, []);

  if (loading) return <Loading label="Loading the emerging watch" />;
  if (error) return <ErrorState error={error} />;
  if (!data) return null;

  const flagged = data.items.filter((i) => i.is_flagged);
  const label = LABEL_TEXT[data.label] ?? data.label.replace(/_/g, " ");
  const ev = data.evidence;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">Emerging watch</h1>
        <p className="mt-1 max-w-3xl text-[13px] leading-relaxed text-[var(--text-secondary)]">
          The {data.flagged} wards with the steepest first-half trend in relative
          flooding index, out of {data.eligible_wards} with at least{" "}
          {data.min_event_days} flooding event-days across the window. Trends are
          benchmarked to the city, never to zero.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Badge tone="accent">{label}</Badge>
          <Badge tone="neutral">
            {data.window_start.slice(0, 4)}–{data.as_of_date.slice(0, 4)}
          </Badge>
        </div>
      </div>

      {/* The instruction is that this must be visible on the screen, not just
          present in the payload. */}
      <Callout
        tone="warning"
        title={
          data.ground_truth_available
            ? "Validation available"
            : "No ground truth — these flags cannot be confirmed"
        }
      >
        {data.ground_truth_available
          ? "Flags can be checked against the city's own register additions."
          : "BBMP's flood register carries no listing years, so there is no record of which locations the city added in which year. Nothing on this screen has been validated against the city's own additions, and nothing here says a flagged ward will appear on the register."}
      </Callout>

      {flagged.length === 0 ? (
        <Card>
          <CardBody className="pt-5">
            <Empty
              title="No wards are flagged"
              hint="Rebuild the derived tables with `python -m app.ingestion.cli derive`."
            />
          </CardBody>
        </Card>
      ) : (
        <Card>
          <CardHeader
            title={`What "${label}" means`}
            description="Each ward's mean relative index in the first half of the window and in the second. The claim is that the second dot is high, not that it moved far — the detector finds wards that stay above the city norm."
          />
          <CardBody>
            <LevelDumbbell
              rows={flagged.map((i) => ({
                ward: i.ward,
                first: i.half1_level,
                second: i.half2_level,
              }))}
              comparisonMean={ev.all_half2_level}
              comparisonLabel="all eligible"
            />
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <p className="text-[13px] leading-relaxed text-[var(--text-secondary)]">
                <strong className="font-semibold text-[var(--text-primary)]">
                  {ev.flagged_above_norm} of {ev.flagged_n}
                </strong>{" "}
                flagged wards finish the second half above the city norm, at a mean
                of{" "}
                <strong className="font-semibold text-[var(--text-primary)] tabular-nums">
                  {num(ev.flagged_half2_level)}
                </strong>{" "}
                against{" "}
                <span className="tabular-nums">{num(ev.all_half2_level)}</span> for
                all eligible wards — Mann-Whitney U, one-sided,{" "}
                {pval(ev.p_vs_other_wards)}. That is the result the flag rests on.
              </p>
              <p className="text-[13px] leading-relaxed text-[var(--text-secondary)]">
                They do <strong className="font-semibold">not</strong> significantly
                exceed their own first half (
                <span className="tabular-nums">{num(ev.flagged_half1_level)}</span> →{" "}
                <span className="tabular-nums">{num(ev.flagged_half2_level)}</span>,
                Wilcoxon signed-rank, one-sided, {pval(ev.p_vs_own_first_half)}). So
                these wards are persistently bad, not measurably getting worse —
                which is why the label is “{label}” and not “accelerating”.
              </p>
            </div>
          </CardBody>
        </Card>
      )}

      <Card>
        <CardHeader
          title="The ranking"
          description="Ordered by first-half Theil-Sen slope, which is the flag rule. The p-values are shown because the ranking is a rank cut, not a significance test — no ward survives multiple-testing correction, so a high rank is a place to look, not a finding."
        />
        <CardBody>
          <Table>
            <caption className="sr-only">
              Wards ranked by first-half trend, with their trend statistics and
              half-window levels.
            </caption>
            <thead>
              <tr>
                <Th numeric>#</Th>
                <Th>Ward</Th>
                <Th>On register</Th>
                <Th numeric>Event-days</Th>
                <Th numeric>1st-half slope</Th>
                <Th numeric>Mann-Kendall</Th>
                <Th numeric>1st-half level</Th>
                <Th numeric>2nd-half level</Th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((i) => (
                <tr
                  key={i.location_id}
                  className={
                    i.is_flagged
                      ? "bg-[var(--surface-page)] hover:bg-[var(--surface-page)]"
                      : "hover:bg-[var(--surface-page)]"
                  }
                >
                  <Td numeric className="text-[var(--text-muted)]">
                    {i.rank_position}
                  </Td>
                  <Td className={i.is_flagged ? "font-medium" : undefined}>
                    {i.ward}
                    {i.is_flagged ? (
                      <span className="ml-2 align-middle">
                        <Badge tone="accent">flagged</Badge>
                      </span>
                    ) : null}
                  </Td>
                  <Td className="text-[var(--text-secondary)]">
                    {i.on_register ? "yes" : "no"}
                  </Td>
                  <Td numeric>{i.event_days}</Td>
                  <Td numeric>{signed(i.half1_slope)}</Td>
                  <Td numeric className="text-[var(--text-secondary)]">
                    {i.half1_p.toFixed(3)}
                  </Td>
                  <Td numeric className="text-[var(--text-secondary)]">
                    {num(i.half1_level)}
                  </Td>
                  <Td numeric className="font-medium">
                    {num(i.half2_level)}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Read this before acting on the list"
          description="These come from the API, not from this page. They are what the analysis established about what this detector can and cannot show."
        />
        <CardBody>
          <ul className="space-y-2.5">
            {data.caveats.map((c) => (
              <li
                key={c.slice(0, 40)}
                className="flex gap-2.5 text-[13px] leading-relaxed text-[var(--text-secondary)]"
              >
                <span
                  aria-hidden
                  className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ background: "var(--status-warning)" }}
                />
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
