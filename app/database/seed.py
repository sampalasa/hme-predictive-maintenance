"""Populates SQLite from the HME_Downtime dataset.

Idempotent: if EquipmentReading rows already exist, seeding is skipped so
re-running `python -m app.database.seed` never duplicates data.

Also seeds the four business roles (Admin, Ingenieur, Technicien, Manager),
one demo user per role, and synthetic maintenance records (derived from the
dataset's failure flags) so the Phase 3 dashboard has real KPIs to display.
"""

import random
from datetime import timedelta

from app import create_app
from app.models import Equipment, EquipmentReading, MaintenanceRecord, Role, User, db
from app.repositories.equipment_repository import EquipmentRepository
from app.services.auth_service import AuthService
from app.services.data.data_cleaning_service import DataCleaningService
from app.services.data.data_loader_service import DataLoaderService
from app.utils.constants import ALL_ROLES
from app.utils.logger import get_logger

logger = get_logger(__name__)

# username -> (role, password, full_name, email)
DEMO_USERS = {
    "admin": ("Admin", "Admin@123", "Administrateur Système", "admin@hme-system.local"),
    "ingenieur": ("Ingenieur", "Ingenieur@123", "Ingénieur Fiabilité", "ingenieur@hme-system.local"),
    "technicien": ("Technicien", "Technicien@123", "Technicien Maintenance", "technicien@hme-system.local"),
    "manager": ("Manager", "Manager@123", "Manager Opérations", "manager@hme-system.local"),
}

_TECHNICIANS = ["J. Kabongo", "P. Mwamba", "S. Ilunga", "T. Mukendi"]


def seed_roles() -> None:
    existing = {r.name for r in db.session.query(Role).all()}
    for role_name in ALL_ROLES:
        if role_name not in existing:
            db.session.add(Role(name=role_name))
    db.session.commit()
    logger.info("Roles ensured: %s", ALL_ROLES)


def seed_demo_users() -> None:
    if db.session.query(User).count() > 0:
        logger.info("Users table already populated, skipping demo user seed.")
        return

    roles_by_name = {r.name: r for r in db.session.query(Role).all()}

    for username, (role_name, password, full_name, email) in DEMO_USERS.items():
        db.session.add(
            User(
                username=username,
                email=email,
                password_hash=AuthService.hash_password(password),
                full_name=full_name,
                role_id=roles_by_name[role_name].id,
            )
        )
    db.session.commit()
    logger.info("Seeded %d demo user(s): %s", len(DEMO_USERS), list(DEMO_USERS))


def seed_equipment_data() -> None:
    if db.session.query(EquipmentReading).count() > 0:
        logger.info("EquipmentReading table already populated, skipping dataset seed.")
        return

    df = DataLoaderService().load()
    df = DataCleaningService().clean(df)

    equipment_repo = EquipmentRepository()
    equipment_cache: dict[str, Equipment] = {}

    readings: list[EquipmentReading] = []
    for row in df.itertuples(index=False):
        if row.EquipmentID not in equipment_cache:
            equipment_cache[row.EquipmentID] = equipment_repo.get_or_create(
                equipment_code=row.EquipmentID, equipment_type=row.EquipmentType
            )
        equipment = equipment_cache[row.EquipmentID]

        readings.append(
            EquipmentReading(
                equipment_id=equipment.id,
                timestamp=row.Timestamp,
                operating_hours=int(row.OperatingHours),
                engine_temp=float(row.EngineTemp),
                hydraulic_pressure=float(row.HydraulicPressure),
                vibration=float(row.Vibration),
                failure_mode=row.FailureMode,
                failure_within_7_days=int(row.FailureWithin7Days),
            )
        )

    db.session.add_all(readings)
    db.session.commit()

    logger.info(
        "Seeded %d equipment(s) and %d reading(s) from dataset",
        len(equipment_cache),
        len(readings),
    )


def seed_maintenance_records() -> None:
    """Derive maintenance history from the dataset's failure-flagged readings.

    The raw dataset has no maintenance log, so this generates one plausible
    corrective intervention a few days after each reading flagged
    ``FailureWithin7Days=1``, giving the Phase 3 dashboard real MTTR/cost
    data instead of an all-zero KPI.
    """

    if db.session.query(MaintenanceRecord).count() > 0:
        logger.info("MaintenanceRecord table already populated, skipping.")
        return

    rng = random.Random(42)
    flagged_readings = (
        db.session.query(EquipmentReading).filter_by(failure_within_7_days=1).all()
    )

    records = [
        MaintenanceRecord(
            equipment_id=reading.equipment_id,
            maintenance_type="Corrective",
            description=f"Intervention suite à alerte {reading.failure_mode}",
            performed_by=rng.choice(_TECHNICIANS),
            downtime_hours=round(rng.uniform(2.0, 48.0), 1),
            cost=round(rng.uniform(150.0, 5000.0), 2),
            status="Completed",
            performed_at=reading.timestamp + timedelta(days=rng.randint(1, 6)),
        )
        for reading in flagged_readings
    ]

    db.session.add_all(records)
    db.session.commit()
    logger.info("Seeded %d synthetic maintenance record(s)", len(records))


def run() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_roles()
        seed_equipment_data()
        seed_demo_users()
        seed_maintenance_records()


if __name__ == "__main__":
    run()
