/**
 * Screen 1 — the ward index.
 *
 * The project's actual quantity: flooding event-days benchmarked against what
 * the citywide complaint mix predicts for that ward's volume. 1.00 is the city
 * norm, and both the line chart and the choropleth are drawn around it.
 *
 * The reference line and the diverging midpoint are the same fact rendered
 * twice. Neither is optional: raw complaint counts doubled between 2021 and
 * 2024, so an un-benchmarked series shows reporting growth and reads as
 * flooding.
 */
import { useMemo, useState } from "react";
import type { FeatureCollection, Geometry } from "geojson";

import { IndexChart } from "@/components/charts/IndexChart";
import { WardChoropleth, type WardProps } from "@/components/charts/WardChoropleth";
import {
  Badge,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Empty,
  ErrorState,
  Input,
  Loading,
  Table,
  Td,
  Th,
} from "@/components/ui";
import {
  fetchCityIndex,
  fetchIndex,
  fetchWards,
  type IndexSeries,
  type Location,
} from "@/lib/api";
import { num } from "@/lib/format";
import { useAsync } from "@/lib/useAsync";

const DEFAULT_WARD = "Bellandur";

async function loadGeo(): Promise<FeatureCollection<Geometry, WardProps>> {
  const res = await fetch("/bbmp-wards.geojson");
  if (!res.ok) throw new Error("Ward boundaries could not be loaded.");
  return (await res.json()) as FeatureCollection<Geometry, WardProps>;
}

function WardPicker({
  wards,
  value,
  onChange,
}: {
  wards: Location[];
  value: string;
  onChange: (ward: string) => void;
}) {
  const [query, setQuery] = useState("");
  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    const pool = q
      ? wards.filter(
          (w) =>
            w.area_name.toLowerCase().includes(q) || (w.ward_no ?? "").startsWith(q),
        )
      : wards;
    return pool.slice(0, 60);
  }, [wards, query]);

  return (
    <div className="w-full max-w-xs">
      <Input
        type="search"
        placeholder="Find a ward…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="Filter wards"
      />
      <ul
        className="mt-2 max-h-[420px] overflow-y-auto rounded-md border border-[var(--border)]"
        role="listbox"
        aria-label="Wards"
      >
        {matches.length === 0 ? (
          <li className="px-3 py-2 text-[12px] text-[var(--text-muted)]">
            No ward matches “{query}”.
          </li>
        ) : (
          matches.map((w) => (
            <li key={w.location_id}>
              <button
                type="button"
                role="option"
                aria-selected={w.area_name === value}
                onClick={() => onChange(w.area_name)}
                className={
                  "flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left text-[13px] " +
                  (w.area_name === value
                    ? "bg-[var(--series-1-soft)] font-medium text-[var(--series-1)]"
                    : "text-[var(--text-primary)] hover:bg-[var(--surface-page)]")
                }
              >
                <span className="truncate">{w.area_name}</span>
                <span className="shrink-0 text-[11px] text-[var(--text-muted)] tabular-nums">
                  {w.ward_no ?? ""}
                </span>
              </button>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}

function SeriesCard({ series }: { series: IndexSeries }) {
  const last = series.points.at(-1);
  const above = series.points.filter((p) => p.rel_index > 1).length;

  return (
    <Card>
      <CardHeader
        title={`${series.ward} — relative flooding index`}
        description={series.definition}
        actions={
          <div className="flex flex-wrap items-center justify-end gap-1.5">
            {series.ward_no ? <Badge tone="neutral">Ward {series.ward_no}</Badge> : null}
            {series.zone ? <Badge tone="muted">{series.zone}</Badge> : null}
          </div>
        }
      />
      <CardBody>
        <IndexChart points={series.points} />
        <p className="mt-3 text-[13px] leading-relaxed text-[var(--text-secondary)]">
          Mean over {series.quarters} quarters:{" "}
          <strong className="font-semibold text-[var(--text-primary)] tabular-nums">
            {num(series.mean_rel_index)}
          </strong>
          . Above the city norm in {above} of {series.quarters} quarters
          {last ? `; ${num(last.rel_index)} in ${last.period}` : ""}.
        </p>
      </CardBody>
    </Card>
  );
}

export function IndexScreen() {
  const [ward, setWard] = useState(DEFAULT_WARD);

  const [period, setPeriod] = useState<string | undefined>(undefined);

  const wardsState = useAsync(fetchWards, []);
  const wards = useMemo(() => wardsState.data ?? [], [wardsState.data]);
  const geoState = useAsync(loadGeo, []);
  const cityState = useAsync(() => fetchCityIndex(period), [period]);
  const seriesState = useAsync(() => fetchIndex(ward), [ward]);

  // ward_no is the join key: the GeoJSON carries it, and so does every row.
  const mapValues = useMemo(() => {
    const m = new Map<string, number>();
    for (const w of cityState.data?.wards ?? []) {
      if (w.ward_no) m.set(w.ward_no, w.rel_index);
    }
    return m;
  }, [cityState.data]);

  const selectedWardNo =
    wards.find((w) => w.area_name === ward)?.ward_no ?? null;

  const handleSelectFromMap = (wardNo: string) => {
    const match = wards.find((w) => w.ward_no === wardNo);
    if (match) setWard(match.area_name);
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">Ward index</h1>
        <p className="mt-1 max-w-3xl text-[13px] leading-relaxed text-[var(--text-secondary)]">
          Flooding event-days per ward-quarter, benchmarked against what the
          citywide complaint mix predicts for that ward's volume. 1.00 is the
          city norm.
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-[280px_1fr]">
        <Card>
          <CardHeader title="Ward" />
          <CardBody>
            {wardsState.loading ? (
              <Loading label="Loading wards" />
            ) : wardsState.error ? (
              <ErrorState error={wardsState.error} />
            ) : (
              <WardPicker wards={wards} value={ward} onChange={setWard} />
            )}
          </CardBody>
        </Card>

        <div className="min-w-0">
          {seriesState.loading ? (
            <Card>
              <CardBody>
                <Loading label={`Loading ${ward}`} />
              </CardBody>
            </Card>
          ) : seriesState.error ? (
            <Card>
              <CardBody className="pt-5">
                <ErrorState error={seriesState.error} />
              </CardBody>
            </Card>
          ) : seriesState.data ? (
            <div className={seriesState.refreshing ? "opacity-60" : undefined}>
              <SeriesCard series={seriesState.data} />
            </div>
          ) : null}
        </div>
      </div>

      <Card>
        <CardHeader
          title="Every ward, latest quarter"
          description="Shaded by relative index. Blue is below the city norm, red above; the midpoint is the norm itself. Click a ward to chart it."
          actions={
            cityState.data ? (
              <label className="flex items-center gap-2 text-[12px] text-[var(--text-secondary)]">
                Quarter
                <select
                  value={cityState.data.period}
                  onChange={(e) => setPeriod(e.target.value)}
                  className="h-8 rounded-md border border-[var(--border-strong)] bg-[var(--surface-1)] px-2 text-[12px] text-[var(--text-primary)]"
                >
                  {cityState.data.available_periods.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </label>
            ) : null
          }
        />
        <CardBody>
          {geoState.error ? (
            <ErrorState error={geoState.error} />
          ) : cityState.error ? (
            <ErrorState error={cityState.error} />
          ) : geoState.loading || cityState.loading ? (
            <Loading label="Loading ward boundaries" />
          ) : geoState.data && cityState.data ? (
            mapValues.size === 0 ? (
              <Empty
                title="No index rows for any ward"
                hint="Build the derived tables with `python -m app.ingestion.cli derive`, then reload."
              />
            ) : (
              <div className={cityState.refreshing ? "opacity-60" : undefined}>
                <WardChoropleth
                  geo={geoState.data}
                  values={mapValues}
                  period={cityState.data.period}
                  selectedWardNo={selectedWardNo}
                  onSelect={handleSelectFromMap}
                />
              </div>
            )
          ) : null}
        </CardBody>
      </Card>

      {seriesState.data ? (
        <Card>
          <CardHeader
            title={`${seriesState.data.ward} — the numbers behind the line`}
            description="The index is a ratio, so the inputs matter as much as the result: a ward can rise because it flooded more or because it complained less about everything else."
          />
          <CardBody>
            <Table>
              <caption className="sr-only">
                Quarterly relative index for {seriesState.data.ward} with its
                inputs.
              </caption>
              <thead>
                <tr>
                  <Th>Quarter</Th>
                  <Th numeric>Flooding event-days</Th>
                  <Th numeric>All complaints</Th>
                  <Th numeric>City mix predicts</Th>
                  <Th numeric>Relative index</Th>
                </tr>
              </thead>
              <tbody>
                {seriesState.data.points.map((p) => (
                  <tr key={p.period} className="hover:bg-[var(--surface-page)]">
                    <Td>{p.period}</Td>
                    <Td numeric>{p.event_days}</Td>
                    <Td numeric className="text-[var(--text-secondary)]">
                      {p.total_complaints.toLocaleString("en-IN")}
                    </Td>
                    <Td numeric className="text-[var(--text-secondary)]">
                      {num(p.expected_event_days, 1)}
                    </Td>
                    <Td numeric className="font-medium">
                      {num(p.rel_index)}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </CardBody>
        </Card>
      ) : null}

      <Callout tone="info" title="Why the benchmark">
        Complaint volume in Bengaluru roughly doubled between 2021 and 2024, and
        not evenly — ward growth runs from 0.87× to 4.81×. A trend on raw counts
        finds app adoption, not flooding. Benchmarking each ward-quarter to the
        citywide mix is what separates the two, and it is why a ward can have
        more flooding complaints than last year and still sit below 1.00.
      </Callout>
    </div>
  );
}
