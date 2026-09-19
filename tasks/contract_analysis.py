import os
import time
from io import BytesIO

import boto3
from google import genai
from google.genai import types
from langchain_text_splitters import RecursiveCharacterTextSplitter
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


# Gemini client used to generate embeddings.
gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# Text splitter used to divide contract text into
# smaller pieces for the RAG pipeline.
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
    separators=[
        "\n\n",
        "\n",
        ". ",
        " ",
        ""
    ]
)


# Gemini Embedding 2 has an 8,192-token input limit.
#
# We use a conservative character limit when grouping chunks
# into a single embedding request. This keeps the combined
# request comfortably below the model's token limit without
# requiring a tokenizer just to determine batch boundaries.
EMBEDDING_BATCH_CHARACTER_LIMIT = 24000


def generate_embeddings(chunks, contract_name):
    """
    Generate one embedding per contract chunk.

    Multiple chunks are sent in a single embed_content request
    using separate Content objects. Gemini Embedding 2 returns
    one embedding for each Content object.

    Chunks are divided into smaller batches so the combined
    request stays within Gemini's input limits.
    """

    embeddings = []

    current_batch = []
    current_batch_characters = 0

    for chunk in chunks:

        chunk_length = len(chunk)

        # If adding this chunk would exceed the batch size,
        # process the current batch before starting a new one.
        if (
            current_batch
            and current_batch_characters + chunk_length
            > EMBEDDING_BATCH_CHARACTER_LIMIT
        ):
            batch_embeddings = _embed_batch(
                current_batch,
                contract_name
            )

            embeddings.extend(
                batch_embeddings
            )

            current_batch = []
            current_batch_characters = 0

        current_batch.append(chunk)
        current_batch_characters += chunk_length

    # Process the final batch.
    if current_batch:

        batch_embeddings = _embed_batch(
            current_batch,
            contract_name
        )

        embeddings.extend(
            batch_embeddings
        )

    return embeddings


def _embed_batch(chunks, contract_name):
    """
    Generate separate embeddings for a single batch of chunks.
    """

    contents = []

    for chunk in chunks:

        document_text = (
            f"title: {contract_name} | "
            f"text: {chunk}"
        )

        contents.append(
            types.Content(
                parts=[
                    types.Part.from_text(
                        text=document_text
                    )
                ]
            )
        )

    result = gemini_client.models.embed_content(
        model="gemini-embedding-2",
        contents=contents,
        config=types.EmbedContentConfig(
            output_dimensionality=768
        )
    )

    if not result.embeddings:
        raise ValueError(
            "Gemini returned no embeddings"
        )

    if len(result.embeddings) != len(chunks):
        raise ValueError(
            "Number of embeddings returned by Gemini "
            "does not match the number of chunks"
        )

    return [
        embedding.values
        for embedding in result.embeddings
    ]


def analyze_contract(contract_id):
    """
    Background task for analyzing a contract.

    A user can only have one contract actively analyzed at a time.
    Contracts that are waiting for their turn remain PENDING.

    Current pipeline:
    1. Wait for the user's other analysis to finish.
    2. Mark the contract as ANALYZING.
    3. Download the PDF from S3.
    4. Extract text from the PDF.
    5. Split the text into overlapping chunks.
    6. Generate embeddings for the chunks.

    Vector storage, retrieval, Gemini analysis,
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

            # --------------------------------------------------
            # STEP 1: Download PDF from S3
            # --------------------------------------------------

            s3_response = s3.get_object(
                Bucket=S3_BUCKET,
                Key=contract.s3_key
            )

            pdf_bytes = s3_response["Body"].read()

            if not pdf_bytes:
                raise ValueError(
                    "Downloaded PDF is empty"
                )

            print(
                f"Downloaded {contract.name} "
                f"from S3 ({len(pdf_bytes)} bytes)"
            )

            # --------------------------------------------------
            # STEP 2: Extract text from PDF
            # --------------------------------------------------

            pdf = PdfReader(
                BytesIO(pdf_bytes)
            )

            extracted_text = ""

            for page in pdf.pages:

                page_text = page.extract_text()

                if page_text:
                    extracted_text += page_text + "\n"

            if not extracted_text.strip():
                raise ValueError(
                    "No text could be extracted from the PDF"
                )

            print(
                f"Extracted {len(extracted_text)} characters "
                f"from {contract.name}"
            )

            # --------------------------------------------------
            # STEP 3: Split text into chunks
            # --------------------------------------------------

            chunks = text_splitter.split_text(
                extracted_text
            )

            if not chunks:
                raise ValueError(
                    "No chunks were created from the extracted text"
                )

            print(
                f"Created {len(chunks)} chunks "
                f"from {contract.name}"
            )

            # --------------------------------------------------
            # STEP 4: Generate embeddings
            # --------------------------------------------------

            embeddings = generate_embeddings(
                chunks,
                contract.name
            )

            if len(embeddings) != len(chunks):
                raise ValueError(
                    "Number of embeddings does not match "
                    "the number of chunks"
                )

            print(
                f"Successfully generated "
                f"{len(embeddings)} embeddings"
            )

            # Print information about the first embedding
            print(
                f"First embedding dimensions: "
                f"{len(embeddings[0])}"
            )

            print(
                f"First embedding preview: "
                f"{embeddings[0][:5]}"
            )

            # Temporary status update.
            # We will eventually mark the contract as ANALYZED
            # only after the complete pipeline succeeds.
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