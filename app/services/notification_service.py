"""Creates and manages in-app notifications (critical risk alerts, etc.)."""

from typing import Any

from app.models import Notification, db


class NotificationService:
    """Business logic for creating and querying notifications."""

    CRITICAL_RISK_LEVELS = ("Critical", "High")

    def notify_critical_predictions(self, predictions: list[dict[str, Any]]) -> int:
        """Create one notification per critical/high-risk equipment. Returns count created."""

        critical = [p for p in predictions if p["risk_level"] in self.CRITICAL_RISK_LEVELS]

        for pred in critical:
            db.session.add(
                Notification(
                    title=f"Risque {pred['risk_level']} — {pred['equipment_code']}",
                    message=(
                        f"L'équipement {pred['equipment_code']} ({pred['equipment_type']}) présente "
                        f"une probabilité de panne de {pred['probability'] * 100:.1f}% "
                        "dans les 7 prochains jours."
                    ),
                    level="danger" if pred["risk_level"] == "Critical" else "warning",
                )
            )
        db.session.commit()
        return len(critical)

    def get_recent(self, limit: int = 10) -> list[Notification]:
        return (
            db.session.query(Notification).order_by(Notification.created_at.desc()).limit(limit).all()
        )

    def count_unread(self) -> int:
        return db.session.query(Notification).filter_by(is_read=False).count()

    def mark_all_read(self) -> None:
        db.session.query(Notification).filter_by(is_read=False).update({Notification.is_read: True})
        db.session.commit()

    def mark_read(self, notification_id: int) -> None:
        notification = db.session.get(Notification, notification_id)
        if notification is not None:
            notification.is_read = True
            db.session.commit()
