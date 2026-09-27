import os

from google import genai
from google.genai import types

from models.contract_chunk import ContractChunk

gemini_client = genai.Client(
  api_key=os.getenv("GEMINI_API_KEY")
)

EMBEDDING_DIMENSION = 768

def generate_query_embedding(query):
    """
    Generate an embedding for a search query.

    The resulting vector must have the same dimensionality
    as the embeddings stored in contract_chunks.
    """

    result = gemini_client.models.embed_content(
        model="gemini-embedding-2",
        contents=[
            types.Content(
                parts=[
                    types.Part.from_text(
                        text=query
                    )
                ]
            )
        ],
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIMENSION
        )
    )

    if not result.embeddings:
        raise ValueError(
            "Gemini returned no embedding for the query"
        )

    return result.embeddings[0].values


def retrieve_relevant_chunks(
    contract_id,
    query,
    top_k=5
):
    """
    Retrieve the most relevant chunks for a contract.

    Results are always restricted to the specified contract_id
    before vector similarity ranking is performed.
    """

    query_embedding = generate_query_embedding(
        query
    )

    chunks = (
        ContractChunk.query
        .filter(
            ContractChunk.contract_id == contract_id
        )
        .order_by(
            ContractChunk.embedding.cosine_distance(
                query_embedding
            )
        )
        .limit(top_k)
        .all()
    )

    return chunks
