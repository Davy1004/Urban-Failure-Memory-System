/**
 * Screen 4 — allocation.
 *
 * Two scatterplots side by side, and the pairing *is* the finding: drainage
 * spend tracks ward AREA and does not track flooding NEED. Put the two panels
 * next to each other and a reader sees it without being told.
 *
 * What this screen does not have, deliberately:
 *
 * - **No dose-response, and no fitted line anywhere.** The published estimate
 *   is retracted; it did not survive dropping the seven zero-dose wards. A
 *   trend line through a scatter reads as an effect estimate whatever the
 *   caption says.
 * - **No spend-against-outcome panel.** `delta_index` appears only in the
 *   table, labelled descriptive, never plotted against spend.
 *
 * The `retraction` field is rendered in full.
 */
import {
  AllocationScatter,
  type ScatterPoint,
} from "@/components/charts/AllocationScatter";
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
import { fetchAllocation } from "@/lib/api";
import { inr, num, pval, signed } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";

export function AllocationScreen() {
  const { data, error, loading } = useAsync(fetchAllocation, []);

  if (loading) return <Loading label="Loading the allocation panel" />;
  if (error) return <ErrorState error={error} />;
  if (!data) return null;

  const f = data.finding;

  const areaPoints: ScatterPoint[] = data.items.map((i) => ({
    ward: i.ward,
    spend: i.drainage_spend,
    value: i.ward_area_sqkm,
    treated: i.is_treated,
  }));
  const needPoints: ScatterPoint[] = data.items.map((i) => ({
    ward: i.ward,
    spend: i.drainage_spend,
    value: i.pre_index,
    treated: i.is_treated,
  }));

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">
          Drainage allocation
        </h1>
        <p className="mt-1 max-w-3xl text-[13px] leading-relaxed text-[var(--text-secondary)]">
          {f.n_wards} wards, {f.n_treated} with drainage work completing between{" "}
          {data.window_start.slice(0, 7)} and {data.window_end.slice(0, 7)} —{" "}
          {inr(f.total_spend)} in total, median {inr(f.median_spend_treated)} per
          treated ward.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Badge tone="neutral">allocation, not outcome</Badge>
          <Badge tone="muted">
            {data.window_start.slice(0, 7)} – {data.window_end.slice(0, 7)}
          </Badge>
        </div>
      </div>

      <Callout tone="critical" title="The outcome claim is retracted">
        {data.retraction}
      </Callout>

      {data.items.length === 0 ? (
        <Card>
          <CardBody className="pt-5">
            <Empty
              title="No allocation panel"
              hint="Rebuild the derived tables with `python -m app.ingestion.cli derive`."
            />
          </CardBody>
        </Card>
      ) : (
        <Card>
          <CardHeader
            title="What spend tracks, and what it does not"
            description="The same spend on both axes. Ward area on the left, the ward's relative flooding index before the works on the right. The difference between the two panels is the finding."
          />
          <CardBody>
            <div className="grid gap-6 lg:grid-cols-2">
              <div>
                <h3 className="mb-1 text-[13px] font-semibold text-[var(--text-primary)]">
                  Spend vs ward area
                </h3>
                <p className="mb-2 text-[12px] text-[var(--text-secondary)]">
                  Bigger wards get more money.
                </p>
                <AllocationScatter
                  points={areaPoints}
                  yLabel="Ward area"
                  yUnit="km²"
                  correlation={f.spend_vs_area}
                />
              </div>
              <div>
                <h3 className="mb-1 text-[13px] font-semibold text-[var(--text-primary)]">
                  Spend vs flooding need
                </h3>
                <p className="mb-2 text-[12px] text-[var(--text-secondary)]">
                  Worse-flooding wards do not.
                </p>
                <AllocationScatter
                  points={needPoints}
                  yLabel="Relative index before the works"
                  correlation={f.spend_vs_pre_index}
                  yReference={1}
                  yReferenceLabel="city norm"
                />
              </div>
            </div>

            <p className="mt-5 max-w-4xl text-[13px] leading-relaxed text-[var(--text-secondary)]">
              {data.headline}
            </p>
          </CardBody>
        </Card>
      )}

      <Card>
        <CardHeader
          title="The correlations behind it"
          description="Spearman rank correlations across all wards in the panel. Rank correlations describe the scatter; none of them is a model of it."
        />
        <CardBody>
          <Table>
            <caption className="sr-only">
              Rank correlations between drainage spend and ward attributes.
            </caption>
            <thead>
              <tr>
                <Th>Relationship</Th>
                <Th numeric>Spearman ρ</Th>
                <Th numeric>p</Th>
                <Th>Reading</Th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <Td className="font-medium">Spend vs ward area</Td>
                <Td numeric>{num(f.spend_vs_area.rho, 3)}</Td>
                <Td numeric className="text-[var(--text-secondary)]">
                  {pval(f.spend_vs_area.p)}
                </Td>
                <Td className="text-[var(--text-secondary)]">
                  Money follows size.
                </Td>
              </tr>
              <tr>
                <Td className="font-medium">Spend vs relative flooding need</Td>
                <Td numeric>{num(f.spend_vs_pre_index.rho, 3)}</Td>
                <Td numeric className="text-[var(--text-secondary)]">
                  {pval(f.spend_vs_pre_index.p)}
                </Td>
                <Td className="text-[var(--text-secondary)]">
                  Indistinguishable from no relationship.
                </Td>
              </tr>
              <tr>
                <Td className="font-medium">Spend vs absolute complaint counts</Td>
                <Td numeric>{num(f.spend_vs_absolute_events.rho, 3)}</Td>
                <Td numeric className="text-[var(--text-secondary)]">
                  {pval(f.spend_vs_absolute_events.p)}
                </Td>
                <Td className="text-[var(--text-secondary)]">
                  Looks like targeting.
                </Td>
              </tr>
              <tr>
                <Td className="font-medium">Area vs absolute complaint counts</Td>
                <Td numeric>{num(f.area_vs_absolute_events.rho, 3)}</Td>
                <Td numeric className="text-[var(--text-secondary)]">
                  {pval(f.area_vs_absolute_events.p)}
                </Td>
                <Td className="text-[var(--text-secondary)]">
                  Big wards generate more of everything.
                </Td>
              </tr>
              <tr className="bg-[var(--surface-page)]">
                <Td className="font-medium">
                  Spend vs complaint counts, controlling for area
                </Td>
                <Td numeric className="font-semibold">
                  {num(f.spend_vs_events_controlling_area.rho, 3)}
                </Td>
                <Td numeric className="text-[var(--text-secondary)]">
                  {pval(f.spend_vs_events_controlling_area.p)}
                </Td>
                <Td className="text-[var(--text-secondary)]">
                  It was not targeting. Area explains all of it.
                </Td>
              </tr>
            </tbody>
          </Table>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Per ward"
          description="Ordered by spend. The change in relative index is shown because it is what happened, not because spend explains it — no model on this page relates the two."
        />
        <CardBody>
          <Table>
            <caption className="sr-only">
              Drainage spend, ward area and relative index per ward.
            </caption>
            <thead>
              <tr>
                <Th>Ward</Th>
                <Th numeric>Works</Th>
                <Th numeric>Spend</Th>
                <Th numeric>Area km²</Th>
                <Th numeric>Spend per km²</Th>
                <Th numeric>Index before</Th>
                <Th numeric>Index after</Th>
                <Th numeric>Change</Th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((i) => (
                <tr key={i.location_id} className="hover:bg-[var(--surface-page)]">
                  <Td className="font-medium">
                    {i.ward}
                    {i.is_treated ? null : (
                      <span className="ml-2 align-middle">
                        <Badge tone="muted">no work in window</Badge>
                      </span>
                    )}
                  </Td>
                  <Td numeric>{i.drainage_works}</Td>
                  <Td numeric>{inr(i.drainage_spend)}</Td>
                  <Td numeric className="text-[var(--text-secondary)]">
                    {i.ward_area_sqkm === null ? "—" : num(i.ward_area_sqkm, 1)}
                  </Td>
                  <Td numeric className="text-[var(--text-secondary)]">
                    {i.spend_per_sqkm === null || i.spend_per_sqkm === 0
                      ? "—"
                      : inr(i.spend_per_sqkm)}
                  </Td>
                  <Td numeric className="text-[var(--text-secondary)]">
                    {num(i.pre_index)}
                  </Td>
                  <Td numeric className="text-[var(--text-secondary)]">
                    {num(i.post_index)}
                  </Td>
                  <Td numeric>{signed(i.delta_index, 2)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </CardBody>
      </Card>

      <Callout tone="warning" title="Why there is no “did it work?” chart here">
        {f.n_treated} of {f.n_wards} wards in this panel received drainage work
        inside the window, and every ward in the city has been receiving drainage
        work continuously since 2013. A unit that is always treated has no before,
        so there is no comparison to draw — not weak evidence of an effect, but no
        design capable of measuring one.
      </Callout>
    </div>
  );
}
