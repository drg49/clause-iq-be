from models import db

class FindingChunk(db.Model):
    __tablename__ = "finding_chunks"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # Finding
    finding_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "contract_findings.id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    # Supporting contract chunk
    chunk_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "contract_chunks.id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    # Order in which evidence should be presented
    evidence_order = db.Column(
        db.Integer,
        nullable=False
    )
