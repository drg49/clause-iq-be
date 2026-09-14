import os
import time
from io import BytesIO

import boto3
from pypdf import PdfReader

from models import db
from models.contract import Contract


S3_BUCKET = "drg-clauses"

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)


def analyze_contract(contract_id):
    """
    Background task for analyzing a contract.

    A user can only have one contract actively analyzed at a time.
    Contracts that are waiting for their turn remain PENDING.

    Current step:
    1. Wait for the user's other analysis to finish.
    2. Mark the contract as ANALYZING.
    3. Download the PDF from S3.
    4. Extract text from the PDF.
    5. Confirm the text was extracted successfully.

    Chunking, embeddings, RAG, Gemini analysis,
    and result storage will be added later.
    """

    from app import app

    with app.app_context():

        contract = None

        try:
            # Find the contract
            contract = db.session.get(
                Contract,
                contract_id
            )

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

            # Download the PDF from S3
            s3_response = s3.get_object(
                Bucket=S3_BUCKET,
                Key=contract.s3_key
            )

            pdf_bytes = s3_response["Body"].read()

            # Confirm that the PDF was downloaded
            if not pdf_bytes:
                raise ValueError(
                    "Downloaded PDF is empty"
                )

            print(
                f"Downloaded {contract.name} "
                f"from S3 ({len(pdf_bytes)} bytes)"
            )

            # Create a PDF reader from the downloaded bytes
            pdf = PdfReader(
                BytesIO(pdf_bytes)
            )

            # Extract text from every page
            extracted_text = ""

            for page in pdf.pages:
                page_text = page.extract_text()

                if page_text:
                    extracted_text += page_text + "\n"

            # Confirm that text was extracted
            if not extracted_text.strip():
                raise ValueError(
                    "No text could be extracted from the PDF"
                )

            print(
                f"Extracted {len(extracted_text)} characters "
                f"from {contract.name}"
            )

            # Print a small preview so we can verify the extraction
            print(
                "\n--- Extracted Text Preview ---\n"
                f"{extracted_text[:500]}"
                "\n--- End Preview ---\n"
            )

            # Temporary status update.
            # This will eventually happen only after
            # the complete analysis pipeline succeeds.
            contract.status = "ANALYZED"
            db.session.commit()

        except Exception as e:
            db.session.rollback()

            print(
                f"Contract analysis failed for "
                f"contract {contract_id}: {e}"
            )

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
