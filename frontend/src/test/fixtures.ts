/**
 * Fixtures carrying the project's real measured figures.
 *
 * Not invented numbers: precision@20 = 14.0809%, oracle 37.7206%, random
 * 4.7868%, the frozen top-20's leading wards, and the allocation correlations
 * are all what the API actually returns from the loaded database. Tests that
 * assert on them are asserting the screens render the project's own results.
 */
import type {
  Allocation,
  CityIndexSnapshot,
  Emerging,
  IndexSeries,
  Watchlist,
} from "@/lib/api";

export const watchlist: Watchlist = {
  snapshot_id: 1,
  city: "Bengaluru",
  failure_type: "WATERLOG",
  as_of_date: "2023-12-31",
  k: 20,
  train_start: "2020-02-08",
  computed_at: "2026-09-09T01:49:54",
  context: {
    precision_at_k: 0.14080882,
    oracle_at_k: 0.37720588,
    random_at_k: 0.04786751,
    share_of_ceiling: 0.37327,
    test_rain_days: 136,
    test_events: 1289,
    test_start: "2024-01-01",
    test_end: "2025-06-19",
    rain_threshold_mm: 2.5,
    weather_model: "ecmwf_ifs",
    reading:
      "Report all three together, always. A precision@20 of 14% reads as " +
      "failure alone; against a 4.8% random floor and a 37.7% oracle ceiling " +
      "it is 37% of everything achievable.",
  },
  items: [
    { rank_position: 1, location_id: 11, ward: "Bellandur", ward_no: "150", zone: "Mahadevapura", prior_events: 156, test_events: 22 },
    { rank_position: 2, location_id: 12, ward: "Horamavu", ward_no: "25", zone: "Mahadevapura", prior_events: 130, test_events: 35 },
    { rank_position: 3, location_id: 13, ward: "Thanisandra", ward_no: "6", zone: "Yelahanka", prior_events: 100, test_events: 24 },
  ],
};

export const unscoredWatchlist: Watchlist = {
  ...watchlist,
  snapshot_id: 2,
  as_of_date: "2026-09-09",
  context: {
    ...watchlist.context,
    precision_at_k: null,
    oracle_at_k: null,
    random_at_k: null,
    share_of_ceiling: null,
    test_rain_days: null,
    test_events: null,
    test_start: null,
    test_end: null,
    rain_threshold_mm: null,
    weather_model: null,
  },
  items: [],
};

export const emerging: Emerging = {
  city: "Bengaluru",
  as_of_date: "2025-03-31",
  window_start: "2020-04-01",
  eligible_wards: 103,
  min_event_days: 15,
  flagged: 2,
  label: "chronically_above_norm",
  ground_truth_available: false,
  evidence: {
    flagged_n: 10,
    flagged_half1_level: 1.4194696618725022,
    flagged_half2_level: 1.7738537743951888,
    all_half2_level: 1.1605451491709675,
    flagged_above_norm: 10,
    p_vs_other_wards: 0.0001441289643413036,
    p_vs_own_first_half: 0.1162109375,
  },
  items: [
    {
      rank_position: 1, location_id: 40, ward: "Gandhi Nagar", ward_no: "94",
      zone: "West", is_flagged: true, on_register: false, event_days: 21,
      half1_slope: 0.171, half1_p: 0.0201, half1_level: 1.02, half2_level: 1.55,
      level_delta: 0.53, full_slope: 0.0512, full_p: 0.041,
    },
    {
      rank_position: 2, location_id: 41, ward: "Ulsoor", ward_no: "89",
      zone: "East", is_flagged: true, on_register: true, event_days: 18,
      half1_slope: 0.1547, half1_p: 0.0339, half1_level: 1.11, half2_level: 1.56,
      level_delta: 0.45, full_slope: 0.0438, full_p: 0.058,
    },
    {
      rank_position: 3, location_id: 42, ward: "Jakkur", ward_no: "5",
      zone: "Yelahanka", is_flagged: false, on_register: false, event_days: 97,
      half1_slope: 0.0421, half1_p: 0.19, half1_level: 0.71, half2_level: 1.33,
      level_delta: 0.62, full_slope: 0.0603, full_p: 0.0047,
    },
  ],
  caveats: [
    "The label is 'chronically above norm', not 'accelerating'. Wards in the top 10 by first-half slope end the second half at mean relative index 1.77 against 1.16 for all eligible wards (p = 0.0001).",
    "The ranking is a rank cut, not a significance test. Benjamini-Hochberg over all 103 eligible wards leaves zero survivors.",
    "There is no ground truth for a flag. The register KMLs carry no year.",
  ],
};

export const allocation: Allocation = {
  city: "Bengaluru",
  window_start: "2021-01-01",
  window_end: "2022-12-31",
  finding: {
    n_wards: 110,
    n_treated: 103,
    n_untreated: 7,
    total_spend: 6677331368,
    median_spend_treated: 20242441,
    spend_vs_area: { rho: 0.4740945947284659, p: 1.6789480159021492e-7 },
    spend_vs_pre_index: { rho: 0.08245317073394623, p: 0.3918004463485205 },
    spend_vs_absolute_events: { rho: 0.273907527096652, p: 0.0037850635333234258 },
    area_vs_absolute_events: { rho: 0.6485610232178333, p: 1.8473913595114384e-14 },
    spend_vs_events_controlling_area: {
      rho: -0.05009333987091936,
      p: 0.603267016538981,
    },
  },
  headline:
    "BBMP allocates drainage spend by ward size, not by flooding need. Spend " +
    "correlates with ward area at Spearman +0.474 and with the ward's relative " +
    "flooding index at +0.082 (p = 0.39).",
  retraction:
    "This screen shows allocation, not outcome. The published dose-response of " +
    "the change in relative index on log drainage spend (-0.0240, p = 0.0138, " +
    "n = 110) is RETRACTED: refitted on treated wards only it is -0.0064 " +
    "(p = 0.833).",
  items: [
    {
      location_id: 3, ward: "Someshwara", ward_no: "3", zone: "Yelahanka",
      is_treated: true, drainage_works: 45, drainage_spend: 631617283,
      ward_area_sqkm: 22.6, spend_per_sqkm: 27947667, event_days_total: 83,
      pre_index: 1.21, post_index: 1.04, delta_index: -0.17,
    },
    {
      location_id: 5, ward: "Jakkur", ward_no: "5", zone: "Yelahanka",
      is_treated: true, drainage_works: 51, drainage_spend: 494203600,
      ward_area_sqkm: 15.2, spend_per_sqkm: 32513395, event_days_total: 97,
      pre_index: 0.55, post_index: 1.42, delta_index: 0.87,
    },
    {
      location_id: 9, ward: "A.Narayanapura", ward_no: "56", zone: "Mahadevapura",
      is_treated: false, drainage_works: 0, drainage_spend: 0,
      ward_area_sqkm: 2.1, spend_per_sqkm: 0, event_days_total: 35,
      pre_index: 3.0, post_index: 1.45, delta_index: -1.55,
    },
  ],
};

const QUARTERS = [
  "2020Q2", "2020Q3", "2020Q4", "2021Q1", "2021Q2", "2021Q3", "2021Q4",
  "2022Q1", "2022Q2", "2022Q3", "2022Q4", "2023Q1", "2023Q2", "2023Q3",
  "2023Q4", "2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1",
];

export const indexSeries: IndexSeries = {
  location_id: 11,
  ward: "Bellandur",
  ward_no: "150",
  zone: "Mahadevapura",
  smoothing: 0.5,
  mean_rel_index: 1.86,
  quarters: QUARTERS.length,
  points: QUARTERS.map((period, i) => ({
    period,
    period_start: `20${period.slice(2, 4)}-01-01`,
    event_days: 4 + (i % 5),
    total_complaints: 300 + i * 20,
    city_share: 0.0085,
    expected_event_days: (300 + i * 20) * 0.0085,
    rel_index: 1.2 + Math.sin(i / 3) * 0.6,
  })),
  definition:
    "rel = (event_days + s) / (total_complaints * city_share + s). Above 1.00 " +
    "the ward had more flooding event-days than the citywide complaint mix " +
    "predicts for its volume; below 1.00, fewer. Normalising by the ward's own " +
    "complaint volume is mandatory.",
};

export const cityIndex: CityIndexSnapshot = {
  city: "Bengaluru",
  period: "2025Q1",
  period_start: "2025-01-01",
  city_share: 0.0067,
  available_periods: QUARTERS,
  wards: [
    {
      location_id: 11, ward: "Bellandur", ward_no: "150", zone: "Mahadevapura",
      event_days: 9, total_complaints: 640, expected_event_days: 4.288,
      rel_index: 1.98,
    },
    {
      location_id: 12, ward: "Horamavu", ward_no: "25", zone: "Mahadevapura",
      event_days: 3, total_complaints: 700, expected_event_days: 4.69,
      rel_index: 0.67,
    },
  ],
  definition: indexSeries.definition,
};

export const wards = [
  {
    location_id: 11, area_name: "Bellandur", ward_no: "150",
    zone: "Mahadevapura", latitude: 12.93, longitude: 77.67, geom_level: "ward",
  },
  {
    location_id: 12, area_name: "Horamavu", ward_no: "25",
    zone: "Mahadevapura", latitude: 13.03, longitude: 77.65, geom_level: "ward",
  },
];
