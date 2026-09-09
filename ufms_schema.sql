-- =====================================================================
-- URBAN FAILURE MEMORY SYSTEM (UFMS)
-- MySQL 8.0 schema — rev 2 (decision-support framing)
--
-- Primary city : Bengaluru (BBMP)  — trains, evaluates, all measured results
-- Demo city    : Delhi (PWD/MCD)   — same method, no ground truth
--
-- Design notes that answer likely viva questions:
--   * 3NF throughout; every repeated string is an ENUM or a lookup table.
--   * Weather is stored per ERA5 GRID CELL, not per location. Delhi and
--     Bengaluru each need only a handful of cells, which keeps the whole
--     database inside a 1 GB free tier.
--   * risk_predictions.actual_outcome closes the feedback loop. Without it
--     the system can never be shown to have worked. Do not defer this.
--   * daily_rankings persists every night's list. Computing rankings on the
--     fly leaves no evidence for the ranking-dynamism proof.
--   * Every ingested row carries a source_id, so results are reproducible.
--
-- Run order matters (foreign keys). Execute this file top to bottom.
-- =====================================================================

-- NOT destructive. This will fail loudly if the tables already exist,
-- which is deliberate: once Phase 1 has loaded data, a silent re-run
-- would wipe it. To start clean on purpose, run scripts/reset_db.sql first.
CREATE DATABASE IF NOT EXISTS ufms
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
USE ufms;

SET FOREIGN_KEY_CHECKS = 1;


-- =====================================================================
-- 1. REFERENCE / GEOGRAPHY
-- =====================================================================

CREATE TABLE cities (
    city_id         SMALLINT UNSIGNED   NOT NULL AUTO_INCREMENT,
    name            VARCHAR(80)         NOT NULL,
    state           VARCHAR(80)         NOT NULL,
    country         CHAR(2)             NOT NULL DEFAULT 'IN',
    centroid_lat    DECIMAL(9,6)        NOT NULL,
    centroid_lng    DECIMAL(9,6)        NOT NULL,
    timezone        VARCHAR(40)         NOT NULL DEFAULT 'Asia/Kolkata',
    -- 'primary'  = full pipeline, labels available, all metrics reported
    -- 'demo'     = method applied, no ground truth, results are illustrative
    role            ENUM('primary','demo') NOT NULL,
    monsoon_start_month TINYINT UNSIGNED NOT NULL COMMENT 'local season start, for season_position feature',
    monsoon_end_month   TINYINT UNSIGNED NOT NULL,
    created_at      TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (city_id),
    UNIQUE KEY uq_cities_name (name, state)
) ENGINE=InnoDB;


-- ERA5 reanalysis grid cells (~25 km). A city needs only a few.
CREATE TABLE weather_cells (
    cell_id         INT UNSIGNED        NOT NULL AUTO_INCREMENT,
    city_id         SMALLINT UNSIGNED   NOT NULL,
    -- Two reanalyses are in play (profile 17): ERA5 at ~25 km resolves BBMP
    -- into 3 cells, ECMWF-IFS at ~9 km into 14. Cells from different models
    -- are DIFFERENT cells even at the same coordinate, which is why the
    -- model is part of uq_cell_coords and not just a label.
    model           ENUM('era5','ecmwf_ifs','era5_land')
                    NOT NULL DEFAULT 'era5' COMMENT 'which reanalysis this cell belongs to',
    latitude        DECIMAL(9,6)        NOT NULL,
    longitude       DECIMAL(9,6)        NOT NULL,
    elevation_m     DECIMAL(7,2)        NULL,
    PRIMARY KEY (cell_id),
    UNIQUE KEY uq_cell_coords (model, latitude, longitude),
    KEY idx_cell_city (city_id),
    CONSTRAINT fk_cell_city FOREIGN KEY (city_id)
        REFERENCES cities (city_id) ON DELETE CASCADE
) ENGINE=InnoDB;


CREATE TABLE data_sources (
    source_id       SMALLINT UNSIGNED   NOT NULL AUTO_INCREMENT,
    name            VARCHAR(120)        NOT NULL,
    url             VARCHAR(500)        NULL,
    licence         VARCHAR(120)        NULL,
    description     VARCHAR(500)        NULL,
    PRIMARY KEY (source_id),
    UNIQUE KEY uq_source_name (name)
) ENGINE=InnoDB;


CREATE TABLE ingestion_runs (
    run_id          BIGINT UNSIGNED     NOT NULL AUTO_INCREMENT,
    source_id       SMALLINT UNSIGNED   NOT NULL,
    started_at      DATETIME            NOT NULL,
    finished_at     DATETIME            NULL,
    rows_ingested   INT UNSIGNED        NOT NULL DEFAULT 0,
    rows_rejected   INT UNSIGNED        NOT NULL DEFAULT 0,
    status          ENUM('running','success','failed','partial') NOT NULL DEFAULT 'running',
    error_message   TEXT                NULL,
    PRIMARY KEY (run_id),
    KEY idx_run_source_time (source_id, started_at),
    CONSTRAINT fk_run_source FOREIGN KEY (source_id)
        REFERENCES data_sources (source_id) ON DELETE RESTRICT
) ENGINE=InnoDB;


CREATE TABLE failure_types (
    failure_type_id TINYINT UNSIGNED    NOT NULL AUTO_INCREMENT,
    code            VARCHAR(30)         NOT NULL,
    name            VARCHAR(80)         NOT NULL,
    description     VARCHAR(400)        NULL,
    -- scope flag: only 'modelled' types get the full ML pipeline
    scope           ENUM('modelled','operational','schema_only') NOT NULL DEFAULT 'schema_only',
    PRIMARY KEY (failure_type_id),
    UNIQUE KEY uq_failure_code (code)
) ENGINE=InnoDB;


CREATE TABLE locations (
    location_id     INT UNSIGNED        NOT NULL AUTO_INCREMENT,
    city_id         SMALLINT UNSIGNED   NOT NULL,
    cell_id         INT UNSIGNED        NULL COMMENT 'nearest ERA5 weather cell',
    area_name       VARCHAR(200)        NOT NULL,
    ward_no         VARCHAR(20)         NULL,
    ward_name       VARCHAR(150)        NULL,
    zone            VARCHAR(100)        NULL,
    latitude        DECIMAL(9,6)        NULL,
    longitude       DECIMAL(9,6)        NULL,
    -- the analysis unit: 'ward' for BBMP, 'point' for a named Delhi hotspot
    geom_level      ENUM('ward','point','grid') NOT NULL DEFAULT 'ward',
    -- is this on the municipality's own published hotspot register?
    is_known_hotspot   BOOLEAN          NOT NULL DEFAULT FALSE,
    hotspot_source     VARCHAR(120)     NULL,
    first_listed_year  SMALLINT UNSIGNED NULL COMMENT 'year it first appeared on the official list',
    last_listed_year   SMALLINT UNSIGNED NULL COMMENT 'NULL if still listed, set when it drops off',
    elevation_m     DECIMAL(7,2)        NULL,
    imperviousness  DECIMAL(5,2)        NULL COMMENT 'percent, from land cover',
    drain_distance_m DECIMAL(9,2)       NULL,
    population      INT UNSIGNED        NULL,
    created_at      TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (location_id),
    UNIQUE KEY uq_location_city_area (city_id, area_name, geom_level),
    KEY idx_location_city (city_id),
    KEY idx_location_cell (cell_id),
    KEY idx_location_ward (city_id, ward_no),
    KEY idx_location_hotspot (city_id, is_known_hotspot),
    KEY idx_location_coords (latitude, longitude),
    CONSTRAINT fk_location_city FOREIGN KEY (city_id)
        REFERENCES cities (city_id) ON DELETE CASCADE,
    CONSTRAINT fk_location_cell FOREIGN KEY (cell_id)
        REFERENCES weather_cells (cell_id) ON DELETE SET NULL
) ENGINE=InnoDB;


CREATE TABLE infrastructure_assets (
    asset_id        INT UNSIGNED        NOT NULL AUTO_INCREMENT,
    location_id     INT UNSIGNED        NOT NULL,
    asset_type      ENUM('drain','culvert','pump','underpass','sewer_line',
                         'catch_basin','road','other') NOT NULL,
    installation_date DATE              NULL,
    capacity_note   VARCHAR(200)        NULL,
    status          ENUM('operational','degraded','failed','unknown')
                    NOT NULL DEFAULT 'unknown',
    PRIMARY KEY (asset_id),
    KEY idx_asset_location (location_id),
    CONSTRAINT fk_asset_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- =====================================================================
-- 2. USERS AND ACCESS
-- =====================================================================

CREATE TABLE users (
    user_id         INT UNSIGNED        NOT NULL AUTO_INCREMENT,
    name            VARCHAR(120)        NOT NULL,
    email           VARCHAR(190)        NOT NULL,
    password_hash   VARCHAR(255)        NOT NULL COMMENT 'bcrypt/argon2 — never store plaintext',
    role            ENUM('admin','officer') NOT NULL DEFAULT 'officer',
    department      VARCHAR(120)        NULL,
    city_id         SMALLINT UNSIGNED   NULL,
    is_active       BOOLEAN             NOT NULL DEFAULT TRUE,
    last_login_at   DATETIME            NULL,
    created_at      TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP
                                        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_users_email (email),
    KEY idx_users_city (city_id),
    CONSTRAINT fk_user_city FOREIGN KEY (city_id)
        REFERENCES cities (city_id) ON DELETE SET NULL
) ENGINE=InnoDB;


-- =====================================================================
-- 3. OBSERVATIONS  (the "memory" — raw signal)
-- =====================================================================

-- Hourly reanalysis, one row per cell per hour.
-- UNIQUE(cell_id, recorded_at) is what stops a retried scheduler run from
-- silently double-inserting and skewing every downstream aggregate.
CREATE TABLE weather_observations (
    weather_id      BIGINT UNSIGNED     NOT NULL AUTO_INCREMENT,
    cell_id         INT UNSIGNED        NOT NULL,
    recorded_at     DATETIME            NOT NULL,
    rainfall_mm     DECIMAL(7,3)        NULL,
    temperature_c   DECIMAL(5,2)        NULL,
    humidity_pct    DECIMAL(5,2)        NULL,
    wind_speed_ms   DECIMAL(6,2)        NULL,
    source_id       SMALLINT UNSIGNED   NULL,
    PRIMARY KEY (weather_id),
    UNIQUE KEY uq_weather_cell_time (cell_id, recorded_at),
    KEY idx_weather_time (recorded_at),
    CONSTRAINT fk_weather_cell FOREIGN KEY (cell_id)
        REFERENCES weather_cells (cell_id) ON DELETE CASCADE,
    CONSTRAINT fk_weather_source FOREIGN KEY (source_id)
        REFERENCES data_sources (source_id) ON DELETE SET NULL
) ENGINE=InnoDB;


-- Derived daily features. Intensity matters more than totals:
-- 60 mm in one hour floods a road, 60 mm over a day usually does not.
CREATE TABLE weather_daily (
    cell_id             INT UNSIGNED    NOT NULL,
    obs_date            DATE            NOT NULL,
    rain_24h_mm         DECIMAL(7,2)    NULL,
    rain_1h_max_mm      DECIMAL(7,2)    NULL,
    rain_3h_max_mm      DECIMAL(7,2)    NULL,
    antecedent_7d_mm    DECIMAL(8,2)    NULL COMMENT 'prior-week total, a soil saturation proxy',
    -- normalised, city-invariant features (see plan: normalise before modelling)
    rain_percentile     DECIMAL(6,5)    NULL COMMENT 'rank of rain_24h in this cell own history',
    return_period_yrs   DECIMAL(8,3)    NULL,
    season_position     SMALLINT        NULL COMMENT 'days into the LOCAL monsoon, not calendar month',
    temp_mean_c         DECIMAL(5,2)    NULL,
    humidity_mean_pct   DECIMAL(5,2)    NULL,
    PRIMARY KEY (cell_id, obs_date),
    KEY idx_wd_date (obs_date),
    CONSTRAINT fk_wd_cell FOREIGN KEY (cell_id)
        REFERENCES weather_cells (cell_id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- Citizen complaints: the RAW SIGNAL, not the confirmed failure.
-- Note this is a complaint, not an observed flood — reporting propensity
-- varies with income and civic awareness, which is why analyses must
-- control for each location's baseline complaint rate.
CREATE TABLE complaints (
    complaint_id    BIGINT UNSIGNED     NOT NULL AUTO_INCREMENT,
    location_id     INT UNSIGNED        NOT NULL,
    failure_type_id TINYINT UNSIGNED    NULL,
    external_id     VARCHAR(80)         NULL COMMENT 'id in the source system, for dedup',
    reported_at     DATETIME            NOT NULL,
    resolved_at     DATETIME            NULL,
    category        VARCHAR(150)        NULL COMMENT 'raw category string from source',
    sub_category    VARCHAR(150)        NULL,
    status          ENUM('registered','in_progress','closed','reopened',
                         'long_term','not_relevant','unknown')
                    NOT NULL DEFAULT 'unknown',
    description     TEXT                NULL,
    source_id       SMALLINT UNSIGNED   NULL,
    run_id          BIGINT UNSIGNED     NULL,
    PRIMARY KEY (complaint_id),
    UNIQUE KEY uq_complaint_external (source_id, external_id),
    KEY idx_complaint_loc_time (location_id, reported_at),
    KEY idx_complaint_type_time (failure_type_id, reported_at),
    CONSTRAINT fk_complaint_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE,
    CONSTRAINT fk_complaint_type FOREIGN KEY (failure_type_id)
        REFERENCES failure_types (failure_type_id) ON DELETE SET NULL,
    CONSTRAINT fk_complaint_source FOREIGN KEY (source_id)
        REFERENCES data_sources (source_id) ON DELETE SET NULL,
    CONSTRAINT fk_complaint_run FOREIGN KEY (run_id)
        REFERENCES ingestion_runs (run_id) ON DELETE SET NULL
) ENGINE=InnoDB;


-- Confirmed failure events. Usually DERIVED from clustering complaints in
-- space and time — hence derived_from. occurred_at and reported_at are
-- separate because the lag between them is both a feature and a bias.
CREATE TABLE failures (
    failure_id      BIGINT UNSIGNED     NOT NULL AUTO_INCREMENT,
    failure_type_id TINYINT UNSIGNED    NOT NULL,
    location_id     INT UNSIGNED        NOT NULL,
    asset_id        INT UNSIGNED        NULL,
    occurred_at     DATETIME            NOT NULL,
    reported_at     DATETIME            NULL,
    severity_level  ENUM('low','medium','high','critical') NOT NULL DEFAULT 'medium',
    description     TEXT                NULL,
    derived_from    ENUM('manual','complaint_cluster','news','agency_report')
                    NOT NULL DEFAULT 'manual',
    complaint_count SMALLINT UNSIGNED   NULL COMMENT 'size of the cluster, if derived',
    source_id       SMALLINT UNSIGNED   NULL,
    created_at      TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (failure_id),
    KEY idx_failure_loc_time (location_id, occurred_at),
    KEY idx_failure_type_time (failure_type_id, occurred_at),
    KEY idx_failure_occurred (occurred_at),
    CONSTRAINT fk_failure_type FOREIGN KEY (failure_type_id)
        REFERENCES failure_types (failure_type_id) ON DELETE RESTRICT,
    CONSTRAINT fk_failure_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE,
    CONSTRAINT fk_failure_asset FOREIGN KEY (asset_id)
        REFERENCES infrastructure_assets (asset_id) ON DELETE SET NULL,
    CONSTRAINT fk_failure_source FOREIGN KEY (source_id)
        REFERENCES data_sources (source_id) ON DELETE SET NULL
) ENGINE=InnoDB;


CREATE TABLE complaint_failure_link (
    complaint_id    BIGINT UNSIGNED     NOT NULL,
    failure_id      BIGINT UNSIGNED     NOT NULL,
    PRIMARY KEY (complaint_id, failure_id),
    KEY idx_cfl_failure (failure_id),
    CONSTRAINT fk_cfl_complaint FOREIGN KEY (complaint_id)
        REFERENCES complaints (complaint_id) ON DELETE CASCADE,
    CONSTRAINT fk_cfl_failure FOREIGN KEY (failure_id)
        REFERENCES failures (failure_id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- The denominator of the relative flooding index.
--
--     rel(w,q) = events(w,q) / [ total_complaints(w,q) * city_share(q) ]
--
-- `complaints` holds only the waterlogging and solid-waste subset that rule 7
-- allows to be loaded, so the ward's complaint volume across EVERY category
-- cannot be recovered from it. Without this table the index is computable only
-- from a CSV sitting outside the database, which is how a dashboard ends up
-- showing a number nothing else can reproduce (profile SS27.1).
--
-- It is an aggregate of the source extract, not of `complaints`: re-running the
-- loader with a different category filter must not change these figures.
CREATE TABLE ward_period_totals (
    location_id     INT UNSIGNED        NOT NULL,
    period_type     ENUM('month','quarter','year') NOT NULL DEFAULT 'quarter',
    period_start    DATE                NOT NULL COMMENT 'first day of the period',
    total_complaints INT UNSIGNED       NOT NULL COMMENT 'all categories, not just hazards',
    run_id          BIGINT UNSIGNED     NULL,
    PRIMARY KEY (location_id, period_type, period_start),
    KEY idx_wpt_period (period_type, period_start),
    CONSTRAINT fk_wpt_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE,
    CONSTRAINT fk_wpt_run FOREIGN KEY (run_id)
        REFERENCES ingestion_runs (run_id) ON DELETE SET NULL
) ENGINE=InnoDB;


-- Operational hazard #2 (garbage). Real BBMP labels exist for this.
CREATE TABLE sanitation_data (
    sanitation_id   BIGINT UNSIGNED     NOT NULL AUTO_INCREMENT,
    location_id     INT UNSIGNED        NOT NULL,
    recorded_at     DATETIME            NOT NULL,
    garbage_volume_kg DECIMAL(10,2)     NULL,
    collection_status ENUM('collected','missed','partial','unknown')
                    NOT NULL DEFAULT 'unknown',
    source_id       SMALLINT UNSIGNED   NULL,
    PRIMARY KEY (sanitation_id),
    UNIQUE KEY uq_sanitation_loc_time (location_id, recorded_at),
    CONSTRAINT fk_sanitation_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- Schema-only in rev 2: kept for extensibility, no module built.
CREATE TABLE traffic_data (
    traffic_id      BIGINT UNSIGNED     NOT NULL AUTO_INCREMENT,
    location_id     INT UNSIGNED        NOT NULL,
    recorded_at     DATETIME            NOT NULL,
    vehicle_count   INT UNSIGNED        NULL,
    congestion_level ENUM('free','light','moderate','heavy','gridlock') NULL,
    average_speed_kmph DECIMAL(6,2)     NULL,
    source_id       SMALLINT UNSIGNED   NULL,
    PRIMARY KEY (traffic_id),
    UNIQUE KEY uq_traffic_loc_time (location_id, recorded_at),
    CONSTRAINT fk_traffic_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- =====================================================================
-- 4. MEMORY AND INTELLIGENCE
-- =====================================================================

-- The Failure Memory Index, recomputed as of a date.
-- CRITICAL: every value must be computed from data strictly EARLIER than
-- as_of_date, or the model leaks the future and every metric is invalid.
CREATE TABLE failure_memory (
    memory_id       BIGINT UNSIGNED     NOT NULL AUTO_INCREMENT,
    location_id     INT UNSIGNED        NOT NULL,
    failure_type_id TINYINT UNSIGNED    NOT NULL,
    as_of_date      DATE                NOT NULL,
    recurrence_count      SMALLINT UNSIGNED NULL,
    recurrence_rate       DECIMAL(7,4)  NULL COMMENT 'events per season',
    recurrence_percentile DECIMAL(6,5)  NULL COMMENT 'rank within city — this is what transfers',
    days_since_last       INT           NULL,
    severity_ema          DECIMAL(6,4)  NULL,
    rain_sensitivity_mm   DECIMAL(7,2)  NULL COMMENT 'rainfall at which THIS location has historically failed',
    neighbour_memory      DECIMAL(7,4)  NULL COMMENT 'same stats within 1 km',
    baseline_complaint_rate DECIMAL(9,4) NULL COMMENT 'reporting-bias control',
    PRIMARY KEY (memory_id),
    UNIQUE KEY uq_memory (location_id, failure_type_id, as_of_date),
    KEY idx_memory_asof (as_of_date),
    CONSTRAINT fk_memory_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE,
    CONSTRAINT fk_memory_type FOREIGN KEY (failure_type_id)
        REFERENCES failure_types (failure_type_id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- Human-readable rules, structured so they can be queried and ranked.
-- e.g. feature='rain_24h_mm', operator='>', threshold=60, confidence=0.72
CREATE TABLE detected_patterns (
    pattern_id      INT UNSIGNED        NOT NULL AUTO_INCREMENT,
    location_id     INT UNSIGNED        NULL COMMENT 'NULL = city-wide rule',
    failure_type_id TINYINT UNSIGNED    NOT NULL,
    feature         VARCHAR(80)         NOT NULL,
    operator        ENUM('>','>=','<','<=','=','between') NOT NULL,
    threshold_value DECIMAL(12,4)       NOT NULL,
    threshold_upper DECIMAL(12,4)       NULL COMMENT 'used when operator = between',
    season          VARCHAR(40)         NULL,
    support_count   INT UNSIGNED        NOT NULL,
    confidence      DECIMAL(6,5)        NOT NULL,
    lift            DECIMAL(8,4)        NULL,
    created_at      TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pattern_id),
    KEY idx_pattern_loc_type (location_id, failure_type_id),
    KEY idx_pattern_conf (confidence DESC),
    CONSTRAINT fk_pattern_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE,
    CONSTRAINT fk_pattern_type FOREIGN KEY (failure_type_id)
        REFERENCES failure_types (failure_type_id) ON DELETE CASCADE
) ENGINE=InnoDB;


CREATE TABLE models (
    model_id        INT UNSIGNED        NOT NULL AUTO_INCREMENT,
    name            VARCHAR(120)        NOT NULL,
    algorithm       ENUM('threshold_rule','logistic_regression','decision_tree',
                         'random_forest','gradient_boosting','other') NOT NULL,
    version         VARCHAR(30)         NOT NULL,
    city_id         SMALLINT UNSIGNED   NULL,
    failure_type_id TINYINT UNSIGNED    NULL,
    -- which ablation rung this is: M0 baseline .. M3 full memory model
    feature_set     ENUM('M0_threshold','M1_weather','M2_weather_geo','M3_full_memory')
                    NOT NULL,
    train_start     DATE                NULL,
    train_end       DATE                NULL,
    test_start      DATE                NULL,
    test_end        DATE                NULL,
    metrics         JSON                NULL COMMENT 'pr_auc, precision_at_20, brier, ece, base_rate',
    artifact_path   VARCHAR(400)        NULL,
    is_active       BOOLEAN             NOT NULL DEFAULT FALSE,
    trained_at      DATETIME            NOT NULL,
    PRIMARY KEY (model_id),
    UNIQUE KEY uq_model_name_version (name, version),
    KEY idx_model_active (is_active, city_id)
) ENGINE=InnoDB;


-- One row per (location, hazard, target date). actual_outcome is what
-- closes the loop — it is how you later prove the alerts were right.
CREATE TABLE risk_predictions (
    prediction_id   BIGINT UNSIGNED     NOT NULL AUTO_INCREMENT,
    location_id     INT UNSIGNED        NOT NULL,
    failure_type_id TINYINT UNSIGNED    NOT NULL,
    model_id        INT UNSIGNED        NOT NULL,
    predicted_for_date DATE             NOT NULL,
    generated_at    DATETIME            NOT NULL,
    risk_score      DECIMAL(7,6)        NOT NULL COMMENT 'calibrated probability 0..1',
    risk_level      ENUM('low','medium','high') NOT NULL,
    feature_snapshot JSON               NULL COMMENT 'exact inputs, for reproducibility',
    actual_outcome  ENUM('pending','failure','no_failure','unknown')
                    NOT NULL DEFAULT 'pending',
    outcome_recorded_at DATETIME        NULL,
    PRIMARY KEY (prediction_id),
    UNIQUE KEY uq_prediction (location_id, failure_type_id, predicted_for_date, model_id),
    KEY idx_pred_date (predicted_for_date, risk_score DESC),
    KEY idx_pred_outcome (actual_outcome, predicted_for_date),
    CONSTRAINT fk_pred_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE,
    CONSTRAINT fk_pred_type FOREIGN KEY (failure_type_id)
        REFERENCES failure_types (failure_type_id) ON DELETE CASCADE,
    CONSTRAINT fk_pred_model FOREIGN KEY (model_id)
        REFERENCES models (model_id) ON DELETE RESTRICT
) ENGINE=InnoDB;


-- The nightly ranked triage list, PERSISTED.
-- Without this table the ranking-dynamism proof is impossible: you cannot
-- measure how much the list reorders between events if you never kept it.
CREATE TABLE daily_rankings (
    ranking_id      BIGINT UNSIGNED     NOT NULL AUTO_INCREMENT,
    city_id         SMALLINT UNSIGNED   NOT NULL,
    failure_type_id TINYINT UNSIGNED    NOT NULL,
    ranking_date    DATE                NOT NULL,
    location_id     INT UNSIGNED        NOT NULL,
    rank_position   SMALLINT UNSIGNED   NOT NULL,
    score           DECIMAL(7,6)        NOT NULL,
    model_id        INT UNSIGNED        NOT NULL,
    in_top_k        BOOLEAN             NOT NULL DEFAULT FALSE COMMENT 'was it dispatched to?',
    generated_at    DATETIME            NOT NULL,
    PRIMARY KEY (ranking_id),
    UNIQUE KEY uq_ranking (city_id, failure_type_id, ranking_date, location_id, model_id),
    KEY idx_ranking_date_pos (ranking_date, rank_position),
    CONSTRAINT fk_rank_city FOREIGN KEY (city_id)
        REFERENCES cities (city_id) ON DELETE CASCADE,
    CONSTRAINT fk_rank_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE,
    CONSTRAINT fk_rank_type FOREIGN KEY (failure_type_id)
        REFERENCES failure_types (failure_type_id) ON DELETE CASCADE,
    CONSTRAINT fk_rank_model FOREIGN KEY (model_id)
        REFERENCES models (model_id) ON DELETE RESTRICT
) ENGINE=InnoDB;


-- Locations trending toward failure that are NOT yet on the official list.
-- status='confirmed' is set later if the site subsequently appears on the
-- municipality's register or shows sustained elevated complaints.
CREATE TABLE emerging_locations (
    emerging_id     INT UNSIGNED        NOT NULL AUTO_INCREMENT,
    location_id     INT UNSIGNED        NOT NULL,
    failure_type_id TINYINT UNSIGNED    NOT NULL,
    detected_at     DATETIME            NOT NULL,
    method          ENUM('mann_kendall','cusum','pettitt','other') NOT NULL,
    trend_statistic DECIMAL(10,5)       NULL,
    p_value         DECIMAL(8,7)        NULL,
    changepoint_date DATE               NULL,
    months_of_evidence SMALLINT UNSIGNED NULL,
    status          ENUM('candidate','confirmed','dismissed')
                    NOT NULL DEFAULT 'candidate',
    confirmed_at    DATETIME            NULL,
    notes           VARCHAR(500)        NULL,
    PRIMARY KEY (emerging_id),
    UNIQUE KEY uq_emerging (location_id, failure_type_id, detected_at),
    KEY idx_emerging_status (status, detected_at),
    CONSTRAINT fk_emerging_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE,
    CONSTRAINT fk_emerging_type FOREIGN KEY (failure_type_id)
        REFERENCES failure_types (failure_type_id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- =====================================================================
-- 5. INTERVENTIONS  ("did the fix work?")
-- =====================================================================

CREATE TABLE interventions (
    intervention_id INT UNSIGNED        NOT NULL AUTO_INCREMENT,
    location_id     INT UNSIGNED        NOT NULL,
    failure_type_id TINYINT UNSIGNED    NULL,
    intervention_type ENUM('desilting','drain_cleaning','drain_widening',
                           'pump_installation','road_raising','sewer_repair',
                           'other') NOT NULL,
    agency          VARCHAR(120)        NULL,
    start_date      DATE                NOT NULL,
    end_date        DATE                NULL,
    cost_inr        DECIMAL(14,2)       NULL,
    external_ref    VARCHAR(120)        NULL COMMENT 'work order number',
    source_id       SMALLINT UNSIGNED   NULL,
    PRIMARY KEY (intervention_id),
    KEY idx_intervention_loc_date (location_id, start_date),
    CONSTRAINT fk_intervention_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE,
    CONSTRAINT fk_intervention_source FOREIGN KEY (source_id)
        REFERENCES data_sources (source_id) ON DELETE SET NULL
) ENGINE=InnoDB;


-- Difference-in-differences: treated site before/after vs untreated sites
-- with similar history over the same period. Controls for the fact that a
-- dry year makes every intervention look effective.
CREATE TABLE intervention_effects (
    effect_id       INT UNSIGNED        NOT NULL AUTO_INCREMENT,
    intervention_id INT UNSIGNED        NOT NULL,
    evaluated_at    DATETIME            NOT NULL,
    window_months   SMALLINT UNSIGNED   NOT NULL,
    treated_pre_rate    DECIMAL(9,5)    NULL,
    treated_post_rate   DECIMAL(9,5)    NULL,
    control_pre_rate    DECIMAL(9,5)    NULL,
    control_post_rate   DECIMAL(9,5)    NULL,
    control_n           SMALLINT UNSIGNED NULL,
    did_estimate        DECIMAL(9,5)    NULL COMMENT 'negative = failures reduced',
    p_value             DECIMAL(8,7)    NULL,
    verdict         ENUM('effective','no_effect','worse','inconclusive')
                    NOT NULL DEFAULT 'inconclusive',
    PRIMARY KEY (effect_id),
    UNIQUE KEY uq_effect (intervention_id, evaluated_at, window_months),
    CONSTRAINT fk_effect_intervention FOREIGN KEY (intervention_id)
        REFERENCES interventions (intervention_id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- =====================================================================
-- 6. OPERATIONS  (alerts and actions)
-- =====================================================================

CREATE TABLE alerts (
    alert_id        BIGINT UNSIGNED     NOT NULL AUTO_INCREMENT,
    prediction_id   BIGINT UNSIGNED     NULL,
    emerging_id     INT UNSIGNED        NULL,
    city_id         SMALLINT UNSIGNED   NOT NULL,
    target_role     ENUM('admin','officer','all') NOT NULL DEFAULT 'officer',
    alert_type      ENUM('nightly_triage','emerging_hotspot','threshold_breach')
                    NOT NULL,
    severity        ENUM('info','warning','critical') NOT NULL DEFAULT 'warning',
    alert_message   TEXT                NOT NULL,
    alert_status    ENUM('queued','sent','failed','acknowledged')
                    NOT NULL DEFAULT 'queued',
    sent_at         DATETIME            NULL,
    created_at      TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (alert_id),
    KEY idx_alert_status (alert_status, created_at),
    KEY idx_alert_city (city_id, created_at),
    CONSTRAINT fk_alert_prediction FOREIGN KEY (prediction_id)
        REFERENCES risk_predictions (prediction_id) ON DELETE CASCADE,
    CONSTRAINT fk_alert_emerging FOREIGN KEY (emerging_id)
        REFERENCES emerging_locations (emerging_id) ON DELETE CASCADE,
    CONSTRAINT fk_alert_city FOREIGN KEY (city_id)
        REFERENCES cities (city_id) ON DELETE CASCADE
) ENGINE=InnoDB;


CREATE TABLE alert_recipients (
    alert_id        BIGINT UNSIGNED     NOT NULL,
    user_id         INT UNSIGNED        NOT NULL,
    delivered_at    DATETIME            NULL,
    read_at         DATETIME            NULL,
    PRIMARY KEY (alert_id, user_id),
    KEY idx_ar_user (user_id),
    CONSTRAINT fk_ar_alert FOREIGN KEY (alert_id)
        REFERENCES alerts (alert_id) ON DELETE CASCADE,
    CONSTRAINT fk_ar_user FOREIGN KEY (user_id)
        REFERENCES users (user_id) ON DELETE CASCADE
) ENGINE=InnoDB;


CREATE TABLE preventive_actions (
    action_id       BIGINT UNSIGNED     NOT NULL AUTO_INCREMENT,
    prediction_id   BIGINT UNSIGNED     NULL,
    location_id     INT UNSIGNED        NOT NULL,
    user_id         INT UNSIGNED        NULL,
    department      VARCHAR(120)        NULL,
    action_taken    TEXT                NULL,
    action_date     DATE                NOT NULL,
    status          ENUM('planned','in_progress','completed','cancelled')
                    NOT NULL DEFAULT 'planned',
    created_at      TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (action_id),
    KEY idx_action_loc_date (location_id, action_date),
    CONSTRAINT fk_action_prediction FOREIGN KEY (prediction_id)
        REFERENCES risk_predictions (prediction_id) ON DELETE SET NULL,
    CONSTRAINT fk_action_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE,
    CONSTRAINT fk_action_user FOREIGN KEY (user_id)
        REFERENCES users (user_id) ON DELETE SET NULL
) ENGINE=InnoDB;


-- =====================================================================
-- 7. DERIVED TABLES  (what the four dashboard screens read)
-- =====================================================================
-- These are computed, not ingested. Every one is reconciled against the
-- committed reference CSVs by tests/test_derived.py, because four
-- computations the paper already published are being reimplemented here
-- against a database instead of a dataframe, and a silent divergence between
-- the dashboard and the paper is the failure mode that matters.
--
-- Rebuild with `python -m app.ingestion.cli derive`. All four are idempotent.


-- Screen 1. The relative flooding index per ward-quarter - the quantity the
-- whole project turns on (profile SS23.1):
--
--     rel(w,q) = [events(w,q) + s] / [complaints(w,q) * city_share(q) + s]
--
-- rel = 1 means the ward sat exactly at the city norm that quarter. The city
-- share is stored beside every row so rel is recomputable from this table
-- alone, without a second pass over `complaints`.
--
-- city_share and rel_index are stored at full precision on purpose: rounding
-- the share to eight places moves rel by ~5e-7, which is enough to break the
-- exact reconciliation against the published panel.
CREATE TABLE ward_quarter_index (
    location_id     INT UNSIGNED        NOT NULL,
    period_type     ENUM('month','quarter','year') NOT NULL DEFAULT 'quarter',
    period_start    DATE                NOT NULL COMMENT 'first day of the period',
    event_days      INT UNSIGNED        NOT NULL COMMENT 'distinct ward-days carrying a strict waterlogging event',
    total_complaints INT UNSIGNED       NOT NULL COMMENT 'the denominator, from ward_period_totals: all categories',
    city_share      DECIMAL(20,18)      NOT NULL COMMENT 'citywide event-days over citywide complaints, this period',
    smoothing       DECIMAL(4,2)        NOT NULL DEFAULT 0.50 COMMENT 'added to numerator and denominator; 0.5 in the published panel',
    rel_index       DECIMAL(20,16)      NOT NULL COMMENT '1.00 is the city norm for that quarter',
    computed_at     DATETIME            NOT NULL,
    PRIMARY KEY (location_id, period_type, period_start),
    KEY idx_wqi_period (period_type, period_start),
    CONSTRAINT fk_wqi_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- Screen 2. The standing watchlist: the static "k historically worst" list,
-- frozen at as_of_date and never re-ranked. It is the baseline an officer
-- already has, and the project's measured result is that almost nothing beats
-- it (profile SS19).
--
-- The three metrics are columns rather than documentation because the screen
-- must show all three together. A bare precision@20 of 14% reads as failure;
-- against a 4.79% random floor and a 37.72% oracle ceiling it is 37% of what
-- is achievable. Showing the list without its context invites exactly the
-- misreading this project spent six sessions disproving.
--
-- They are NULL-able: a snapshot frozen at today's date has no held-out
-- window to measure against, and a made-up number is worse than a blank.
CREATE TABLE watchlist_snapshots (
    snapshot_id     INT UNSIGNED        NOT NULL AUTO_INCREMENT,
    city_id         SMALLINT UNSIGNED   NOT NULL,
    failure_type_id TINYINT UNSIGNED    NOT NULL,
    as_of_date      DATE                NOT NULL COMMENT 'freeze date: entries rank on events up to and including this day',
    k               SMALLINT UNSIGNED   NOT NULL DEFAULT 20 COMMENT 'crew capacity, and the k in precision@k',
    train_start     DATE                NOT NULL,
    test_start      DATE                NULL COMMENT 'NULL when the snapshot has not been scored',
    test_end        DATE                NULL,
    test_rain_days  SMALLINT UNSIGNED   NULL COMMENT 'held-out days at or above rain_threshold_mm',
    test_events     INT UNSIGNED        NULL COMMENT 'citywide event-days on those rain days',
    rain_threshold_mm DECIMAL(5,2)      NULL COMMENT 'city-mean daily rainfall that defines a rain day',
    weather_model   ENUM('era5','ecmwf_ifs','era5_land') NULL COMMENT 'which reanalysis defined a rain day',
    precision_at_k  DECIMAL(9,8)        NULL COMMENT 'what the frozen list achieved',
    oracle_at_k     DECIMAL(9,8)        NULL COMMENT 'the ceiling: most nights carry fewer than k events citywide',
    random_at_k     DECIMAL(9,8)        NULL COMMENT 'expected precision of k wards drawn at random',
    computed_at     DATETIME            NOT NULL,
    PRIMARY KEY (snapshot_id),
    UNIQUE KEY uq_watchlist_snapshot (city_id, failure_type_id, as_of_date, k),
    KEY idx_wls_as_of (city_id, as_of_date),
    CONSTRAINT fk_wls_city FOREIGN KEY (city_id)
        REFERENCES cities (city_id) ON DELETE CASCADE,
    CONSTRAINT fk_wls_type FOREIGN KEY (failure_type_id)
        REFERENCES failure_types (failure_type_id) ON DELETE CASCADE
) ENGINE=InnoDB;


CREATE TABLE watchlist_entries (
    snapshot_id     INT UNSIGNED        NOT NULL,
    rank_position   SMALLINT UNSIGNED   NOT NULL COMMENT '1 is worst; ties broken by area name so the order is stable',
    location_id     INT UNSIGNED        NOT NULL,
    prior_events    INT UNSIGNED        NOT NULL COMMENT 'event-days up to as_of_date. The entire ranking key.',
    test_events     INT UNSIGNED        NULL COMMENT 'event-days on the held-out rain days, for the per-ward column',
    PRIMARY KEY (snapshot_id, rank_position),
    UNIQUE KEY uq_watchlist_entry (snapshot_id, location_id),
    KEY idx_wle_location (location_id),
    CONSTRAINT fk_wle_snapshot FOREIGN KEY (snapshot_id)
        REFERENCES watchlist_snapshots (snapshot_id) ON DELETE CASCADE,
    CONSTRAINT fk_wle_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- Screen 3. The emerging watch: wards ranked by their first-half Theil-Sen
-- slope on rel_index, benchmarked to the city trend rather than to zero
-- (profile SS23.1 - testing against zero scored a ward as declining while it
-- was diverging upward, and manufactured a false negative).
--
-- The label is 'chronically_above_norm', not 'accelerating', and that is not a
-- wording preference. Flagged wards end the second half at mean rel 1.77
-- against 1.16 for all eligible wards (p = 0.0001), but they do NOT
-- significantly exceed their own first-half level (p = 0.23). The detector
-- finds wards that stay above the city norm. Profile SS25.1.
--
-- There is no external ground truth to confirm a flag against:
-- locations.first_listed_year is NULL for all 398 register points, so "which
-- locations did the city add this year" cannot be answered. The screen must
-- not imply otherwise.
CREATE TABLE emerging_watch (
    location_id     INT UNSIGNED        NOT NULL,
    as_of_date      DATE                NOT NULL COMMENT 'last day of the detection window',
    window_start    DATE                NOT NULL,
    rank_position   SMALLINT UNSIGNED   NOT NULL COMMENT 'by first-half slope, which is the flag rule',
    event_days      INT UNSIGNED        NOT NULL COMMENT 'over the whole window; eligibility is >= 15',
    half1_slope     DECIMAL(20,16)      NOT NULL COMMENT 'Theil-Sen on rel_index per quarter, first half',
    half1_p         DECIMAL(19,18)      NOT NULL COMMENT 'Mann-Kendall on the same series',
    half1_level     DECIMAL(20,16)      NOT NULL COMMENT 'mean rel_index over the first half',
    half2_level     DECIMAL(20,16)      NOT NULL,
    half2_slope     DECIMAL(20,16)      NOT NULL,
    level_delta     DECIMAL(21,16)      NOT NULL COMMENT 'half2_level minus half1_level',
    full_slope      DECIMAL(20,16)      NOT NULL COMMENT 'Theil-Sen over the whole window',
    full_p          DECIMAL(19,18)      NOT NULL,
    is_flagged      BOOLEAN             NOT NULL DEFAULT FALSE COMMENT 'inside the top-N cut this run used',
    on_register     BOOLEAN             NOT NULL DEFAULT FALSE COMMENT 'already on the BBMP flood register',
    label           VARCHAR(40)         NOT NULL DEFAULT 'chronically_above_norm' COMMENT 'what the detector was measured to find, not what it was hoped to find',
    computed_at     DATETIME            NOT NULL,
    PRIMARY KEY (location_id, as_of_date),
    KEY idx_ew_rank (as_of_date, rank_position),
    CONSTRAINT fk_ew_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- Screen 4. Allocation, NOT outcome.
--
-- The dose-response of the change in relative index on drainage spend is
-- RETRACTED (profile SS27.2): -0.0240 (p = 0.0138) over all 110 wards becomes
-- -0.0064 (p = 0.833) refitted on treated wards only, because log1p(spend)
-- placed 7 untreated wards at 0 against treated wards at 16-20 and the slope
-- was fitted through two clusters. Analysis is closed (SS28): drainage works
-- are distributed continuously and near-uniformly across all 198 wards and
-- have been since 2013, so no observational evaluation of their effect is
-- identifiable from these records.
--
-- delta_index is stored because the screen plots it and the allocation finding
-- needs a "need" axis. It is NOT an effect estimate and no endpoint returns it
-- as one.
--
-- What survives, and what this table is for: spend tracks ward AREA
-- (Spearman +0.474), not relative flooding need (+0.082, p = 0.39), and the
-- correlation with absolute complaint counts (+0.274) collapses to -0.050
-- (p = 0.60) once area is controlled.
CREATE TABLE ward_allocation (
    location_id     INT UNSIGNED        NOT NULL,
    window_start    DATE                NOT NULL COMMENT 'first work completion date counted',
    window_end      DATE                NOT NULL,
    drainage_works  SMALLINT UNSIGNED   NOT NULL COMMENT 'work orders classified as drainage completing in the window',
    drainage_spend  DECIMAL(16,2)       NOT NULL COMMENT 'INR, nett of deductions',
    ward_area_sqkm  DECIMAL(8,2)        NULL COMMENT 'what spend actually tracks',
    event_days_pre  INT UNSIGNED        NOT NULL,
    event_days_post INT UNSIGNED        NOT NULL,
    event_days_total INT UNSIGNED       NOT NULL COMMENT 'over the whole index window: the absolute-volume axis of the targeting check',
    pre_index       DECIMAL(20,16)      NOT NULL COMMENT 'mean rel_index over the pre quarters',
    post_index      DECIMAL(20,16)      NOT NULL,
    delta_index     DECIMAL(21,16)      NOT NULL COMMENT 'post minus pre. Descriptive. NOT an effect of spend.',
    is_treated      BOOLEAN             NOT NULL COMMENT 'any drainage work in the window. 103 of 110; not a usable control split.',
    computed_at     DATETIME            NOT NULL,
    PRIMARY KEY (location_id, window_start, window_end),
    KEY idx_wa_spend (drainage_spend),
    CONSTRAINT fk_wa_location FOREIGN KEY (location_id)
        REFERENCES locations (location_id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- =====================================================================
-- 8. SEED DATA
-- =====================================================================

INSERT INTO cities
    (name, state, centroid_lat, centroid_lng, role, monsoon_start_month, monsoon_end_month)
VALUES
    ('Bengaluru', 'Karnataka',   12.971600, 77.594600, 'primary', 4, 11),
    ('Delhi',     'Delhi',       28.613900, 77.209000, 'demo',    6,  9);

INSERT INTO failure_types (code, name, description, scope) VALUES
    ('WATERLOG',  'Waterlogging / Flooding',
     'Standing water on roads or in low-lying areas after rainfall.', 'modelled'),
    ('GARBAGE',   'Garbage Overflow',
     'Uncollected or overflowing solid waste.', 'operational'),
    ('TRAFFIC',   'Traffic Congestion',
     'Abnormal congestion. Schema retained for extensibility.', 'schema_only'),
    ('WATER_SHORT','Water Shortage',
     'Interruption or shortfall in water supply.', 'schema_only'),
    ('INFRA',     'Infrastructure Failure',
     'Road, drain or structural failure.', 'schema_only');

INSERT INTO data_sources (name, url, licence, description) VALUES
    ('BBMP Grievances (OpenCity)',
     'https://data.opencity.in/dataset/bbmp-grievances-data',
     'Public Domain',
     'Ward-level citizen grievances, 2020-2025, six annual CSV files.'),
    ('BBMP Flood-Prone Locations (OpenCity)',
     'https://data.opencity.in/dataset/flooding-locations-in-bengaluru-urban',
     'Public Domain',
     'BBMP flood-vulnerable areas and low-lying locations. The triage candidate list.'),
    ('BBMP Work Orders by Ward (OpenCity)',
     'https://data.opencity.in/dataset/bbmp-work-orders-by-ward-2013-2022',
     'Public Domain',
     'Ward-level works 2013-2022. Source for intervention records.'),
    ('Open-Meteo Historical Weather API',
     'https://archive-api.open-meteo.com/v1/archive',
     'CC-BY 4.0 (non-commercial free tier)',
     'ERA5 reanalysis, hourly, 1940-present. No API key required.'),
    ('Delhi PWD / Traffic Police waterlogging points',
     NULL,
     'Public record',
     'Annual list of waterlogging-prone points. Demo city candidate list.'),
    ('OpenStreetMap',
     'https://www.openstreetmap.org',
     'ODbL',
     'Road network, drains, ward boundaries.');


-- =====================================================================
-- 9. CONVENIENCE VIEWS
-- =====================================================================

-- Alert accuracy over time — the answer to "does your system work?"
CREATE OR REPLACE VIEW v_prediction_outcomes AS
SELECT
    m.name              AS model_name,
    m.feature_set,
    p.predicted_for_date,
    p.risk_level,
    COUNT(*)                                                    AS n_predictions,
    SUM(p.actual_outcome = 'failure')                           AS n_failures,
    ROUND(SUM(p.actual_outcome = 'failure') / NULLIF(COUNT(*),0), 4) AS hit_rate
FROM risk_predictions p
JOIN models m ON m.model_id = p.model_id
WHERE p.actual_outcome IN ('failure','no_failure')
GROUP BY m.name, m.feature_set, p.predicted_for_date, p.risk_level;


-- Precision@K per event — the headline triage metric.
CREATE OR REPLACE VIEW v_precision_at_k AS
SELECT
    r.ranking_date,
    r.city_id,
    r.model_id,
    COUNT(*)                                        AS k,
    SUM(p.actual_outcome = 'failure')               AS hits,
    ROUND(SUM(p.actual_outcome = 'failure') / NULLIF(COUNT(*),0), 4) AS precision_at_k
FROM daily_rankings r
LEFT JOIN risk_predictions p
       ON p.location_id        = r.location_id
      AND p.failure_type_id    = r.failure_type_id
      AND p.predicted_for_date = r.ranking_date
      AND p.model_id           = r.model_id
WHERE r.in_top_k = TRUE
GROUP BY r.ranking_date, r.city_id, r.model_id;


-- Known hotspots that have never actually been observed to fail —
-- useful sanity check on both the register and your label coverage.
CREATE OR REPLACE VIEW v_unverified_hotspots AS
SELECT l.location_id, c.name AS city, l.area_name, l.ward_no, l.first_listed_year
FROM locations l
JOIN cities c ON c.city_id = l.city_id
LEFT JOIN failures f ON f.location_id = l.location_id
WHERE l.is_known_hotspot = TRUE
GROUP BY l.location_id, c.name, l.area_name, l.ward_no, l.first_listed_year
HAVING COUNT(f.failure_id) = 0;

-- =====================================================================
-- END OF SCHEMA
-- 31 tables, 3 views. Runs clean on MySQL 8.0.16+.
-- =====================================================================
