from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.common import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health(response: Response, db: Session = Depends(get_db)) -> HealthOut:
    """Liveness + database reachability.

    Returns 503 when the database is unreachable, not 200. Platform health
    checks (Render, Aiven, a load balancer) read the STATUS CODE, not the
    body — a 200 with "database": "unreachable" reads as healthy while the
    service is entirely broken, and the platform keeps routing traffic to it.
    """
    try:
        db.execute(text("SELECT 1"))
        database, healthy = "reachable", True
    except Exception:
        database, healthy = "unreachable", False

    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthOut(
        status="ok" if healthy else "degraded",
        database=database,
        environment=settings.environment,
    )
