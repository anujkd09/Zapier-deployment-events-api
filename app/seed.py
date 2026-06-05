"""Seed the database with mock deployment data.

Run with:  ``python -m app.seed``

Generates a deterministic (fixed-seed) set of deployments spread across several
services, all statuses, and a range of timestamps/durations — so the API has
realistic data to serve immediately. Re-running it resets the table.
"""

import random
from datetime import datetime, timedelta, timezone

from app.data.base import Base
from app.data.session import SessionLocal, engine
from app.models.deployment_model import Deployment, DeploymentStatus

SERVICES = [
    "billing-api",
    "auth-service",
    "web-frontend",
    "notifications-worker",
    "search-api",
    "payments-gateway",
]

# Weighted so most deploys succeed, with a realistic minority of failures,
# in-flight, and rollbacks — gives filtering and (later) metrics something to chew on.
STATUS_WEIGHTS = {
    DeploymentStatus.SUCCESS: 68,
    DeploymentStatus.FAILED: 18,
    DeploymentStatus.IN_PROGRESS: 6,
    DeploymentStatus.ROLLED_BACK: 8,
}

EVENT_COUNT = 30
RANDOM_SEED = 42


def build_deployments(
    count: int = EVENT_COUNT, seed: int = RANDOM_SEED
) -> list[Deployment]:
    """Build a reproducible list of mock deployments."""
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    statuses = list(STATUS_WEIGHTS)
    weights = list(STATUS_WEIGHTS.values())

    deployments: list[Deployment] = []
    for i in range(1, count + 1):
        status = rng.choices(statuses, weights=weights, k=1)[0]

        # Most deploys are quick; failures/rollbacks skew slower; a few are very slow.
        base = rng.randint(45, 300)
        if status in (DeploymentStatus.FAILED, DeploymentStatus.ROLLED_BACK):
            base += rng.randint(60, 400)
        if rng.random() < 0.1:  # occasional outlier
            base += rng.randint(300, 900)
        duration = base if status != DeploymentStatus.IN_PROGRESS else rng.randint(5, 120)

        # Spread across the last ~30 days at varied times of day.
        timestamp = now - timedelta(
            days=rng.randint(0, 29),
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
        )

        deployments.append(
            Deployment(
                id=f"deploy_{i:03d}",
                service=rng.choice(SERVICES),
                status=status,
                duration=duration,
                timestamp=timestamp,
                commit_sha=f"{rng.randrange(16**7):07x}",
            )
        )
    return deployments


def main() -> None:
    """Reset the deployments table and insert fresh mock data."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        deployments = build_deployments()
        db.add_all(deployments)
        db.commit()
        print(
            f"Seeded {len(deployments)} deployments "
            f"across {len(SERVICES)} services and {len(STATUS_WEIGHTS)} statuses."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
