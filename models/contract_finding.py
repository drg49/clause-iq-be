from datetime import datetime

from models import db

class ContractFinding(db.Model):
    __tablename__ = "contract_findings"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # Contract this finding belongs to
    contract_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "contracts.id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    # Finding classification
    type = db.Column(
        db.Enum(
            "RISK",
            "MISSING_PROTECTION",
            "NEGOTIATION_OPPORTUNITY",
            name="contract_finding_type"
        ),
        nullable=False
    )

    # Finding severity
    severity = db.Column(
        db.Enum(
            "HIGH",
            "MEDIUM",
            "LOW",
            name="contract_finding_severity"
        ),
        nullable=True
    )

    # Finding information
    title = db.Column(
        db.String(255),
        nullable=False
    )

    explanation = db.Column(
        db.Text,
        nullable=False
    )

    recommendation = db.Column(
        db.Text,
        nullable=False
    )

    # Timestamp
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
