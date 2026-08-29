import os
import logging
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

MEMORY_EMBEDDING_MODEL = os.getenv(
    "MEMORY_EMBEDDING_MODEL", "text-embedding-3-small"
)

EMBEDDING_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}

EMBEDDING_DIMENSION = EMBEDDING_DIMENSIONS.get(MEMORY_EMBEDDING_MODEL)

if EMBEDDING_DIMENSION is None:
    logger.warning(
        "Unknown MEMORY_EMBEDDING_MODEL %r falling back to the "
        "text-embedding-3-small dimension (1536). Add the model to "
        "EMBEDDING_DIMENSIONS and re-run scripts/setup_memory_embeddings.py "
        "if that is wrong.",
        MEMORY_EMBEDDING_MODEL,
    )
    EMBEDDING_DIMENSION = 1536

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def memory_embedding_text(memory_type, memory_key, memory_value):
    parts = [
        f"{(memory_type or '').replace('_', ' ')}",
        f"{(memory_key or '').replace('_', ' ').replace(':', ': ')}",
        f"{memory_value or ''}",
    ]
    return " | ".join(p.strip() for p in parts if p and p.strip())


def embed_text(text):
    if not text or not text.strip():
        return None

    try:
        response = client.embeddings.create(
            model=MEMORY_EMBEDDING_MODEL,
            input=text.strip(),
        )
        return response.data[0].embedding
    except Exception as exc:
        logger.warning(
            "Memory embedding failed (model=%s): %s: %s",
            MEMORY_EMBEDDING_MODEL,
            type(exc).__name__,
            exc,
        )
        return None


def embed_memory(memory_type, memory_key, memory_value):
    return embed_text(memory_embedding_text(memory_type, memory_key, memory_value))
