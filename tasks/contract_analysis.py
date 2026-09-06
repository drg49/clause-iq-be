import time

from models import db
from models.contract import Contract


def analyze_contract(contract_id):
    """
    Background task for analyzing a contract.

    A user can only have one contract actively analyzed at a time.
    Contracts that are waiting for their turn remain PENDING.

    This is currently a placeholder. The actual PDF extraction,
    RAG, and Gemini analysis will be added later.
    """

    from app import app

    with app.app_context():

        try:
            # Find the contract
            contract = db.session.get(Contract, contract_id)

            if not contract:
                return

            # Remember which user owns this contract
            user_id = contract.user_id

            # Wait until this user's other analysis has finished
            while True:

                active_analysis = Contract.query.filter(
                    Contract.user_id == user_id,
                    Contract.status == "ANALYZING",
                    Contract.id != contract.id
                ).first()

                if not active_analysis:
                    break

                # Another contract belonging to this user is
                # currently being analyzed.
                time.sleep(1)

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
