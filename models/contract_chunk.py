from datetime import datetime

from pgvector.sqlalchemy import Vector

from models import db


class ContractChunk(db.Model):
    __tablename__ = "contract_chunks"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # Contract this chunk belongs to
    contract_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "contracts.id",
            ondelete="CASCADE"
        ),
        nullable=False
    )

    # Position of the chunk within the contract
    chunk_index = db.Column(
        db.Integer,
        nullable=False
    )

    # Extracted contract text
    content = db.Column(
        db.Text,
        nullable=False
    )

    # Gemini embedding
    # gemini-embedding-2 with output_dimensionality=768
    embedding = db.Column(
        Vector(768),
        nullable=False
    )

    # Timestamp
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
