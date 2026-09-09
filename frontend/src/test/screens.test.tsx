/**
 * Contract tests for the screens.
 *
 * These are not "does it render" tests. Each one pins a presentation rule the
 * analysis paid for, and would fail if a redesign quietly dropped it:
 *
 * - precision@k never appears without its ceiling and its floor in the DOM;
 * - the emerging screen never says "accelerating", and says out loud that its
 *   flags cannot be validated;
 * - the allocation screen renders the retraction and shows no coefficient;
 * - an unscored snapshot shows a blank, not a borrowed number.
 *
 * The server already carries these as required response fields. This is the
 * other half of that guarantee: the field arriving is not the same as the field
 * being shown.
 */
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AllocationScreen } from "@/screens/AllocationScreen";
import { EmergingScreen } from "@/screens/EmergingScreen";
import { WatchlistScreen } from "@/screens/WatchlistScreen";
import * as fx from "@/test/fixtures";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchWatchlist: vi.fn(),
    fetchEmerging: vi.fn(),
    fetchAllocation: vi.fn(),
  };
});

const api = await import("@/lib/api");

function renderScreen(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

beforeEach(() => {
  vi.mocked(api.fetchWatchlist).mockResolvedValue(fx.watchlist);
  vi.mocked(api.fetchEmerging).mockResolvedValue(fx.emerging);
  vi.mocked(api.fetchAllocation).mockResolvedValue(fx.allocation);
});

describe("Watchlist screen", () => {
  it("renders the ceiling and the floor beside the achieved figure", async () => {
    renderScreen(<WatchlistScreen />);
    await screen.findByText(/Standing watchlist/i);

    // The three figures, all present in the rendered DOM. This is the whole
    // reason the scale exists: 14.08% alone reads as a failed model.
    expect(await screen.findAllByText("14.08%")).not.toHaveLength(0);
    expect(screen.getAllByText("37.72%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("4.79%").length).toBeGreaterThan(0);
  });

  it("labels the two reference points so neither reads as the score", async () => {
    renderScreen(<WatchlistScreen />);
    expect(await screen.findByText("ceiling")).toBeInTheDocument();
    expect(screen.getByText("chance")).toBeInTheDocument();
  });

  it("gives the scale an accessible description carrying all three", async () => {
    renderScreen(<WatchlistScreen />);
    const fig = await screen.findByRole("img", { name: /precision@20/i });
    const name = fig.getAttribute("aria-label") ?? "";
    expect(name).toContain("14.08%");
    expect(name).toContain("37.72%");
    expect(name).toContain("4.79%");
  });

  it("calls itself a standing watchlist, and never claims to forecast", async () => {
    const { container } = renderScreen(<WatchlistScreen />);
    await screen.findByText(/Standing watchlist/i);
    const text = container.textContent ?? "";
    expect(text).toMatch(/standing watchlist/i);
    expect(text).toMatch(/not a prediction/i);

    // Every sentence that reaches for "forecast" or "predict" has to negate
    // it. A bare one on this screen would be a claim the data cannot carry.
    for (const sentence of text.split(/(?<=[.?!])\s+/)) {
      if (!/forecast|predict/i.test(sentence)) continue;
      expect(sentence).toMatch(/\bnot\b|\bnone\b|\bcannot\b|does not/i);
    }
  });

  it("shows the ranked wards with their ranking key", async () => {
    renderScreen(<WatchlistScreen />);
    const row = (await screen.findByText("Bellandur")).closest("tr")!;
    expect(within(row).getByText("156")).toBeInTheDocument();
  });

  it("shows a blank rather than a borrowed number when unscored", async () => {
    vi.mocked(api.fetchWatchlist).mockResolvedValue(fx.unscoredWatchlist);
    const { container } = renderScreen(<WatchlistScreen />);
    expect(
      await screen.findByText(/has not been scored/i),
    ).toBeInTheDocument();
    expect(container.textContent).not.toContain("14.08%");
    expect(container.textContent).not.toContain("37.72%");
  });
});

describe("Emerging screen", () => {
  it("renders the measured label and never the word 'accelerating'", async () => {
    const { container } = renderScreen(<EmergingScreen />);
    await screen.findByText(/Emerging watch/i);

    expect(screen.getAllByText(/chronically above norm/i).length).toBeGreaterThan(0);
    // The one permitted use is the caveat that explicitly rules it out.
    const uses = (container.textContent ?? "").match(/accelerating/gi) ?? [];
    const ruledOut =
      (container.textContent ?? "").match(
        /not ['"“]?accelerating|not ['"“]accelerating['"”]/gi,
      ) ?? [];
    expect(uses.length).toBe(ruledOut.length);
  });

  it("states on the screen that flags cannot be validated", async () => {
    renderScreen(<EmergingScreen />);
    // The banner, not the caveat list — the instruction is that this is
    // visible on the screen, not buried among the footnotes.
    expect(
      await screen.findByText(/No ground truth — these flags cannot be confirmed/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/register carries no listing years/i),
    ).toBeInTheDocument();
  });

  it("renders every caveat the API returned", async () => {
    const { container } = renderScreen(<EmergingScreen />);
    await screen.findByText(/Emerging watch/i);
    for (const caveat of fx.emerging.caveats) {
      expect(container.textContent).toContain(caveat);
    }
  });

  it("shows the persistence evidence, including the null result", async () => {
    const { container } = renderScreen(<EmergingScreen />);
    await screen.findByText(/Emerging watch/i);
    const text = container.textContent ?? "";
    // The comparison that holds…
    expect(text).toMatch(/Mann-Whitney/i);
    // …and the one that does not, which is why the label is what it is.
    expect(text).toMatch(/Wilcoxon signed-rank/i);
    expect(text).toMatch(/p = 0\.116/);
  });

  it("names the test behind every p-value it shows", async () => {
    const { container } = renderScreen(<EmergingScreen />);
    await screen.findByText(/Emerging watch/i);
    const text = container.textContent ?? "";
    expect(text).toMatch(/Mann-Kendall/);
    expect(text).toMatch(/Theil-Sen/);
  });
});

describe("Allocation screen", () => {
  it("renders the retraction in full", async () => {
    const { container } = renderScreen(<AllocationScreen />);
    await screen.findByText(/Drainage allocation/i);
    expect(container.textContent).toContain(fx.allocation.retraction);
    expect(screen.getByText(/outcome claim is retracted/i)).toBeInTheDocument();
  });

  it("shows the two panels that make the finding", async () => {
    renderScreen(<AllocationScreen />);
    await screen.findByText(/Drainage allocation/i);

    // Two scatter panels, side by side. Their headings also appear as rows in
    // the correlation table, so match the plots by their accessible names.
    const plots = screen.getAllByRole("img", { name: /Drainage spend against/i });
    expect(plots).toHaveLength(2);
    expect(plots[0]).toHaveAccessibleName(/Ward area/i);
    expect(plots[1]).toHaveAccessibleName(/Relative index before the works/i);

    expect(screen.getByText("Bigger wards get more money.")).toBeInTheDocument();
    expect(screen.getByText("Worse-flooding wards do not.")).toBeInTheDocument();
  });

  it("shows the partial correlation that answers the targeting objection", async () => {
    const { container } = renderScreen(<AllocationScreen />);
    await screen.findByText(/Drainage allocation/i);
    const text = container.textContent ?? "";
    expect(text).toContain("0.474");
    expect(text).toContain("-0.050");
    expect(text).toMatch(/controlling for area/i);
  });

  it("mentions the dose-response only to disown it", async () => {
    const { container } = renderScreen(<AllocationScreen />);
    await screen.findByText(/Drainage allocation/i);
    const text = container.textContent ?? "";

    // "dose-response" is allowed exactly where the retraction retracts it, and
    // nowhere else. Everything outside that block must be free of it.
    expect(text).toContain(fx.allocation.retraction);
    const outside = text.split(fx.allocation.retraction).join(" ");
    expect(outside).not.toMatch(/dose-response|coefficient|regression|fitted/i);
    expect(text).toMatch(/allocation, not outcome/i);
  });

  it("labels the index change as descriptive", async () => {
    const { container } = renderScreen(<AllocationScreen />);
    await screen.findByText(/Drainage allocation/i);
    expect(container.textContent).toMatch(
      /not because spend explains it|no model on this page relates the two/i,
    );
  });
});
