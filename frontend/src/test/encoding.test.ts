/**
 * The encoding decisions, pinned.
 *
 * The choropleth's class breaks and the number formats are where a chart can
 * be wrong without looking wrong, so they are tested rather than eyeballed.
 */
import { describe, expect, it } from "vitest";

import { classOf } from "@/components/charts/WardChoropleth";
import { inr, num, pct, pval, signed } from "@/lib/format";

describe("choropleth class breaks", () => {
  it("puts the city norm at the boundary between the two arms", () => {
    // 1.00 is not "slightly bad" — it is the midpoint, and the first warm
    // class starts exactly there.
    expect(classOf(0.999)?.key).toBe("cool1");
    expect(classOf(1)?.key).toBe("warm1");
  });

  it("is symmetric in ratio, not in difference", () => {
    // Half the norm and twice the norm land in the outermost class on each
    // arm. Equal-width linear bins would collapse the whole below-norm arm,
    // because a ratio cannot go below zero but can go to 8.
    expect(classOf(0.49)?.key).toBe("cool3");
    expect(classOf(2.01)?.key).toBe("warm3");
    expect(classOf(0.5)?.key).toBe("cool2");
    expect(classOf(2)?.key).toBe("warm3");
  });

  it("gives three classes per arm and no more", () => {
    const keys = [0.2, 0.6, 0.8, 1.1, 1.6, 4].map((v) => classOf(v)?.key);
    expect(keys).toEqual(["cool3", "cool2", "cool1", "warm1", "warm2", "warm3"]);
    expect(new Set(keys).size).toBe(6);
  });

  it("returns null for a ward with no index, rather than a colour", () => {
    // A ward shaded as if it were at the norm would be a claim; a ward with no
    // colour is an absence.
    expect(classOf(undefined)).toBeNull();
    expect(classOf(Number.NaN)).toBeNull();
  });
});

describe("number formats", () => {
  it("keeps two decimals on percentages", () => {
    // The second decimal is the difference between the two measurement bases
    // (14.08% IFS vs 13.55% ERA5) and the paper quotes it.
    expect(pct(0.14080882)).toBe("14.08%");
    expect(pct(0.04786751)).toBe("4.79%");
    expect(pct(0.37720588)).toBe("37.72%");
  });

  it("never prints a spuriously precise p-value", () => {
    expect(pval(1.6789e-7)).toBe("p < 0.0001");
    expect(pval(0.0037850635)).toBe("p = 0.0038");
    expect(pval(0.603267)).toBe("p = 0.603");
  });

  it("signs a slope, because the direction is the point", () => {
    expect(signed(0.171)).toBe("+0.171");
    expect(signed(-0.05009333987091936)).toBe("−0.050");
    expect(signed(0)).toBe("+0.000");
  });

  it("shows rupees in the units a municipal budget uses", () => {
    expect(inr(631617283)).toBe("₹63.16 Cr");
    expect(inr(20242441)).toBe("₹2.02 Cr");
    expect(inr(0)).toBe("₹0");
  });

  it("rounds the index to two places", () => {
    expect(num(1.7738537743951888)).toBe("1.77");
    expect(num(1.1605451491709675)).toBe("1.16");
  });
});
