"""Python mirrors of the SQL ENUMs. Keep these in sync with ufms_schema.sql."""
import enum


class CityRole(str, enum.Enum):
    PRIMARY = "primary"   # full pipeline, labels available, metrics reported
    DEMO = "demo"         # method applied, no ground truth


class FailureScope(str, enum.Enum):
    MODELLED = "modelled"
    OPERATIONAL = "operational"
    SCHEMA_ONLY = "schema_only"


class GeomLevel(str, enum.Enum):
    WARD = "ward"
    POINT = "point"
    GRID = "grid"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OFFICER = "officer"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DerivedFrom(str, enum.Enum):
    MANUAL = "manual"
    COMPLAINT_CLUSTER = "complaint_cluster"
    NEWS = "news"
    AGENCY_REPORT = "agency_report"


class ComplaintStatus(str, enum.Enum):
    REGISTERED = "registered"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    REOPENED = "reopened"
    LONG_TERM = "long_term"
    NOT_RELEVANT = "not_relevant"
    UNKNOWN = "unknown"


class AssetType(str, enum.Enum):
    DRAIN = "drain"
    CULVERT = "culvert"
    PUMP = "pump"
    UNDERPASS = "underpass"
    SEWER_LINE = "sewer_line"
    CATCH_BASIN = "catch_basin"
    ROAD = "road"
    OTHER = "other"


class AssetStatus(str, enum.Enum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class CollectionStatus(str, enum.Enum):
    COLLECTED = "collected"
    MISSED = "missed"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class CongestionLevel(str, enum.Enum):
    FREE = "free"
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    GRIDLOCK = "gridlock"


class IngestionStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class Algorithm(str, enum.Enum):
    THRESHOLD_RULE = "threshold_rule"
    LOGISTIC_REGRESSION = "logistic_regression"
    DECISION_TREE = "decision_tree"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    OTHER = "other"


class FeatureSet(str, enum.Enum):
    """The ablation ladder. M3 is the system under test."""
    M0_THRESHOLD = "M0_threshold"
    M1_WEATHER = "M1_weather"
    M2_WEATHER_GEO = "M2_weather_geo"
    M3_FULL_MEMORY = "M3_full_memory"


class PredictionOutcome(str, enum.Enum):
    PENDING = "pending"
    FAILURE = "failure"
    NO_FAILURE = "no_failure"
    UNKNOWN = "unknown"


class EmergingMethod(str, enum.Enum):
    MANN_KENDALL = "mann_kendall"
    CUSUM = "cusum"
    PETTITT = "pettitt"
    OTHER = "other"


class EmergingStatus(str, enum.Enum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"


class InterventionType(str, enum.Enum):
    DESILTING = "desilting"
    DRAIN_CLEANING = "drain_cleaning"
    DRAIN_WIDENING = "drain_widening"
    PUMP_INSTALLATION = "pump_installation"
    ROAD_RAISING = "road_raising"
    SEWER_REPAIR = "sewer_repair"
    OTHER = "other"


class EffectVerdict(str, enum.Enum):
    EFFECTIVE = "effective"
    NO_EFFECT = "no_effect"
    WORSE = "worse"
    INCONCLUSIVE = "inconclusive"


class AlertType(str, enum.Enum):
    NIGHTLY_TRIAGE = "nightly_triage"
    EMERGING_HOTSPOT = "emerging_hotspot"
    THRESHOLD_BREACH = "threshold_breach"


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    ACKNOWLEDGED = "acknowledged"


class TargetRole(str, enum.Enum):
    ADMIN = "admin"
    OFFICER = "officer"
    ALL = "all"


class ActionStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PatternOperator(str, enum.Enum):
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "="
    BETWEEN = "between"
