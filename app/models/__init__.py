"""All ORM models. Importing this package registers every table on Base."""
from app.models.geography import (  # noqa: F401
    City, DataSource, FailureType, InfrastructureAsset, IngestionRun, Location,
    WeatherCell,
)
from app.models.user import User  # noqa: F401
from app.models.observation import (  # noqa: F401
    Complaint, ComplaintFailureLink, Failure, SanitationData, TrafficData,
    WeatherDaily, WeatherObservation,
)
from app.models.intelligence import (  # noqa: F401
    DailyRanking, DetectedPattern, EmergingLocation, FailureMemory, MLModel,
    RiskPrediction,
)
from app.models.operations import (  # noqa: F401
    Alert, AlertRecipient, Intervention, InterventionEffect, PreventiveAction,
)

__all__ = [
    "City", "WeatherCell", "DataSource", "IngestionRun", "FailureType",
    "Location", "InfrastructureAsset", "User", "WeatherObservation",
    "WeatherDaily", "Complaint", "Failure", "ComplaintFailureLink",
    "SanitationData", "TrafficData", "FailureMemory", "DetectedPattern",
    "MLModel", "RiskPrediction", "DailyRanking", "EmergingLocation",
    "Intervention", "InterventionEffect", "Alert", "AlertRecipient",
    "PreventiveAction",
]
