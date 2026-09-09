/**
 * precision@k as a position on a scale, never as a stat tile.
 *
 * This is the most load-bearing component on the dashboard and the reason is
 * worth stating. "precision@20 = 14.08%" read alone looks like a failed model.
 * The same number against a 4.79% chance floor and a 37.72% oracle ceiling is
 * 37% of everything achievable — and the ceiling is low because a median rain
 * night carries about six flooding events across the whole city, so twenty crew
 * slots cannot all be right.
 *
 * A caption saying that can be dropped in a redesign. **A mark cannot be drawn
 * without its scale.** So the context is structural here rather than adjacent:
 * the axis ends at the ceiling, the chance floor is a region of the track, and
 * the achieved figure is one mark positioned between them. Deleting either
 * reference point breaks the drawing rather than quietly weakening the claim.
 *
 * The bar is split at the floor rather than filled from zero. The first segment
 * is what k wards drawn at random would score, so it is not an achievement and
 * is not coloured as one; the accent segment is what memory adds on top of it.
 *
 * Laid out in HTML rather than a fixed-viewBox SVG on purpose: an SVG scaled to
 * a 390px screen takes its labels down with it, and a scale whose numbers are
 * six pixels tall is a scale nobody reads. Here only the track scales.
 */
import { num, pct } from "@/lib/format";

export interface PrecisionScaleProps {
  achieved: number;
  ceiling: number;
  floor: number;
  k: number;
  /** What the mark is measuring, for the accessible name. */
  label?: string;
}

export function PrecisionScale({
  achieved,
  ceiling,
  floor,
  k,
  label = "precision",
}: PrecisionScaleProps) {
  // The scale runs from zero to the ceiling. The ceiling is the end of the
  // axis, so it is not possible to render this without it.
  const at = (v: number) => (Math.max(0, Math.min(v, ceiling)) / ceiling) * 100;
  const pFloor = at(floor);
  const pAchieved = at(achieved);

  const shareOfCeiling = achieved / ceiling;
  const timesChance = achieved / floor;

  const description =
    `${label}@${k} is ${pct(achieved)}, on a scale ending at the ` +
    `${pct(ceiling)} oracle ceiling, with a random-order floor at ${pct(floor)}. ` +
    `That is ${pct(shareOfCeiling, 0)} of the ceiling and ` +
    `${num(timesChance, 1)} times the floor.`;

  return (
    <figure className="m-0">
      <div role="img" aria-label={description}>
        {/* The track: everything achievable, ending at the ceiling. */}
        <div
          className="relative h-[30px] w-full overflow-hidden rounded"
          style={{ background: "var(--series-1-soft)" }}
        >
          {/* Chance. Anything inside this is indistinguishable from drawing k
              wards at random, so it is not coloured as an achievement. */}
          <div
            className="absolute inset-y-0 left-0"
            style={{ width: `${pFloor}%`, background: "var(--no-data)" }}
          />
          {/* What memory adds on top of chance. A 2px surface gap separates the
              two fills rather than a border drawn around either. */}
          <div
            className="absolute inset-y-0 rounded-r"
            style={{
              left: `calc(${pFloor}% + 2px)`,
              width: `calc(${pAchieved - pFloor}% - 2px)`,
              background: "var(--series-1)",
            }}
          />
          {/* The single mark. */}
          <div
            className="absolute inset-y-0 w-[2px]"
            style={{ left: `calc(${pAchieved}% - 1px)`, background: "var(--text-primary)" }}
          />
        </div>

        {/* Direct labels, at their natural size. Three values, three labels —
            no tooltip needed, and none is reachable only by hovering. */}
        <div className="relative mt-1.5 h-9 text-[11px]">
          <span className="absolute left-0 top-0 text-[var(--text-muted)]">0%</span>

          <span
            className="absolute top-0 flex -translate-x-1/2 flex-col items-center whitespace-nowrap text-[var(--text-muted)]"
            style={{ left: `${pFloor}%` }}
          >
            <span className="tabular-nums">{pct(floor)}</span>
            <span>chance</span>
          </span>

          <span
            className="absolute top-0 flex -translate-x-1/2 flex-col items-center whitespace-nowrap"
            style={{ left: `${pAchieved}%` }}
          >
            <span className="text-[13px] font-semibold tabular-nums text-[var(--text-primary)]">
              {pct(achieved)}
            </span>
            <span className="text-[var(--text-secondary)]">this list</span>
          </span>

          <span className="absolute right-0 top-0 flex flex-col items-end whitespace-nowrap">
            <span className="text-[12px] font-semibold tabular-nums text-[var(--text-primary)]">
              {pct(ceiling)}
            </span>
            <span className="text-[var(--text-muted)]">ceiling</span>
          </span>
        </div>
      </div>

      <figcaption className="mt-3 text-[13px] leading-relaxed text-[var(--text-secondary)]">
        The frozen list finds a flooded ward in{" "}
        <strong className="font-semibold text-[var(--text-primary)]">
          {pct(achieved)}
        </strong>{" "}
        of the {k} slots it fills — {pct(shareOfCeiling, 0)} of the{" "}
        <strong className="font-semibold text-[var(--text-primary)]">
          {pct(ceiling)}
        </strong>{" "}
        a perfect oracle could reach, and {num(timesChance, 1)}× the{" "}
        <strong className="font-semibold text-[var(--text-primary)]">
          {pct(floor)}
        </strong>{" "}
        a random {k} wards would score. The ceiling is under 40% because a median
        rain night carries about six flooding events across the whole city, so{" "}
        {k} slots cannot all be right.
      </figcaption>
    </figure>
  );
}
