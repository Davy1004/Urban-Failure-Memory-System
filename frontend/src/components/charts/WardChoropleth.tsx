/**
 * The 198 wards shaded by their relative flooding index for one quarter.
 *
 * **Diverging, not sequential.** `rel = 1.00` is the city norm and it is a real
 * midpoint, so the encoding is blue↔red with a neutral gray at the middle — the
 * midpoint has to read as "nothing", and a sequential ramp would make an
 * ordinary ward look like a mild version of a bad one.
 *
 * **Binned on ratio, not on difference.** `rel` is a ratio, so its natural
 * symmetry is multiplicative: the classes are ×/÷ 1.41 and 2 around 1.00, which
 * puts "half the city norm" and "twice the city norm" the same distance from the
 * middle. Equal-width linear bins would squash the whole below-norm arm into one
 * class, because a ratio cannot go below zero but can go to 8.
 *
 * Six classes, three per arm, each arm a single validated hue ramp.
 * Wards with no index row are drawn in the no-data grey and named as such —
 * never shaded as if they were at the norm.
 */
import { useEffect, useMemo, useRef } from "react";
import { GeoJSON, MapContainer, useMap } from "react-leaflet";
import type { Layer, LeafletMouseEvent, PathOptions } from "leaflet";
import type { Feature, FeatureCollection, Geometry } from "geojson";

import { num } from "@/lib/format";

export interface WardProps {
  ward_no: string;
  ward_name: string;
  zone: string | null;
}

/** Class breaks on the ratio scale, symmetric in log space about 1.00. */
const BREAKS = [0.5, 0.71, 1, 1.41, 2] as const;

const CLASSES = [
  { key: "cool3", label: "< 0.50", note: "far below norm", color: "var(--div-cool-3)" },
  { key: "cool2", label: "0.50 – 0.71", note: "below", color: "var(--div-cool-2)" },
  { key: "cool1", label: "0.71 – 1.00", note: "just below", color: "var(--div-cool-1)" },
  { key: "warm1", label: "1.00 – 1.41", note: "just above", color: "var(--div-warm-1)" },
  { key: "warm2", label: "1.41 – 2.00", note: "above", color: "var(--div-warm-2)" },
  { key: "warm3", label: "≥ 2.00", note: "far above norm", color: "var(--div-warm-3)" },
] as const;

export function classOf(rel: number | undefined): (typeof CLASSES)[number] | null {
  if (rel === undefined || Number.isNaN(rel)) return null;
  let i = 0;
  while (i < BREAKS.length && rel >= BREAKS[i]) i += 1;
  return CLASSES[i];
}

/** Leaflet measures the container on mount; a tab or card that was hidden
 *  needs telling once it is visible or the map renders as a grey strip. */
function Invalidate() {
  const map = useMap();
  useEffect(() => {
    const t = window.setTimeout(() => map.invalidateSize(), 0);
    return () => window.clearTimeout(t);
  }, [map]);
  return null;
}

export function WardChoropleth({
  geo,
  values,
  period,
  selectedWardNo,
  onSelect,
  height = 420,
}: {
  geo: FeatureCollection<Geometry, WardProps>;
  /** ward_no → relative index for the quarter being shown. */
  values: Map<string, number>;
  period: string;
  selectedWardNo?: string | null;
  onSelect?: (wardNo: string) => void;
  height?: number;
}) {
  // Leaflet mutates layers in place, so the style callback has to read the
  // current selection from a ref rather than close over a stale prop.
  const selectedRef = useRef(selectedWardNo);
  selectedRef.current = selectedWardNo;

  const style = useMemo(
    () =>
      (feature?: Feature<Geometry, WardProps>): PathOptions => {
        const wardNo = feature?.properties.ward_no ?? "";
        const cls = classOf(values.get(wardNo));
        const selected = selectedRef.current === wardNo;
        return {
          // A 2px surface-coloured gap between fills rather than a border
          // drawn around each mark.
          weight: selected ? 2.5 : 1,
          color: selected ? "var(--text-primary)" : "var(--surface-1)",
          fillColor: cls ? cls.color : "var(--no-data)",
          fillOpacity: cls ? 0.85 : 0.4,
          opacity: 1,
        };
      },
    [values],
  );

  const onEachFeature = useMemo(
    () => (feature: Feature<Geometry, WardProps>, layer: Layer) => {
      const { ward_no, ward_name, zone } = feature.properties;
      const rel = values.get(ward_no);
      const cls = classOf(rel);
      // Name, index and quarter, all three. There is no basemap, so the
      // tooltip is the only thing that says which ward a polygon is — and the
      // quarter belongs here, not only in the legend below, because an index
      // without its period is a number on an unnamed scale.
      layer.bindTooltip(
        `<strong>${ward_name}</strong><br>` +
          `Ward ${ward_no}${zone ? ` · ${zone}` : ""}<br>` +
          (rel === undefined
            ? `No index for ${period}`
            : `Index ${num(rel)}, ${period} — ${cls?.note ?? ""}`),
        { sticky: true },
      );
      layer.on("click", (e: LeafletMouseEvent) => {
        onSelect?.((e.target as { feature: Feature<Geometry, WardProps> }).feature
          .properties.ward_no);
      });
    },
    [values, onSelect, period],
  );

  return (
    <div>
      <div
        className="overflow-hidden rounded-md border border-[var(--border)]"
        style={{ height }}
      >
        <MapContainer
          center={[12.9716, 77.5946]}
          zoom={11}
          scrollWheelZoom={false}
          style={{ height: "100%", width: "100%" }}
          attributionControl={false}
        >
          <Invalidate />
          {/* No tile layer, on purpose. The 198 wards tile the whole city, so
              the polygons are the map — and a photographic or road basemap
              underneath a diverging choropleth competes with the encoding it
              is supposed to support. It also removes a third-party dependency
              that can start demanding an API key, which is exactly what the
              CARTO basemap did. */}
          <GeoJSON
            key={period}
            data={geo}
            style={style}
            onEachFeature={onEachFeature}
          />
        </MapContainer>
      </div>

      <p className="mt-1.5 text-[11px] text-[var(--text-muted)]">
        Ward boundaries: BBMP 198-ward delimitation, 2015.
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="text-[11px] font-medium tracking-wide text-[var(--text-muted)] uppercase">
          Index, {period}
        </span>
        <ul className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          {CLASSES.map((c) => (
            <li key={c.key} className="flex items-center gap-1.5">
              <span
                aria-hidden
                className="inline-block h-3 w-3 rounded-[2px]"
                style={{ background: c.color }}
              />
              <span className="text-[11px] tabular-nums text-[var(--text-secondary)]">
                {c.label}
              </span>
            </li>
          ))}
          <li className="flex items-center gap-1.5">
            <span
              aria-hidden
              className="inline-block h-3 w-3 rounded-[2px] opacity-40"
              style={{ background: "var(--no-data)" }}
            />
            <span className="text-[11px] text-[var(--text-secondary)]">no data</span>
          </li>
        </ul>
      </div>
      <p className="mt-2 text-[12px] leading-relaxed text-[var(--text-muted)]">
        1.00 is the city norm. Classes are multiplicative — each step is ×1.41 —
        because the index is a ratio, so ×2 and ÷2 sit the same distance from the
        middle.
      </p>
    </div>
  );
}
