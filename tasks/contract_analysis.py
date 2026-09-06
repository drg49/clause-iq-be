import time

from app import app
from models import db
from models.contract import Contract


def analyze_contract(contract_id):
    """
    Background task for analyzing a contract.

    This is currently a placeholder. The actual PDF extraction,
    RAG, and Gemini analysis will be added later.
    """

    with app.app_context():

        try:
            # Find the contract
            contract = db.session.get(Contract, contract_id)

            if not contract:
                return

            # The worker has now started processing the contract
            contract.status = "ANALYZING"
            db.session.commit()

            # Simulate a long-running analysis
            time.sleep(10)

            # Mark the contract as analyzed
            contract.status = "ANALYZED"
            db.session.commit()

        except Exception:
            db.session.rollback()

            # Mark the contract as failed
            try:
                contract = db.session.get(
                    Contract,
                    contract_id
                )

                if contract:
                    contract.status = "FAILED"
                    db.session.commit()

            except Exception:
                db.session.rollback()

        finally:
            db.session.remove()
