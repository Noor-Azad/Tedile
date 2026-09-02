from datetime import datetime, timezone

from app.extensions import db


class Review(db.Model):
    """A rating left by either party for a completed booking."""

    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("providers.id"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    reviewer_role = db.Column(db.String(40), nullable=True)

    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint("booking_id", "reviewer_id", name="uq_review_booking_reviewer"),)

    def to_dict(self):
        return {
            "id": self.id,
            "provider_id": self.provider_id,
            "customer_id": self.customer_id,
            "rating": self.rating,
            "comment": self.comment,
        }
