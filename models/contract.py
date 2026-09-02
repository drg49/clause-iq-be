from datetime import datetime

from models import db


class Contract(db.Model):
    __tablename__ = "contracts"

    id = db.Column(db.Integer, primary_key=True)

    # Owner
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    # Contract information
    name = db.Column(
        db.String(255),
        nullable=False
    )

    # S3
    s3_key = db.Column(
        db.String(500),
        nullable=False
    )

    # Timestamp
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
