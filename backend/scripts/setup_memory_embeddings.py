import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from database.db import db
from models.user_memory import UserMemory
from services.embedding_service import (
    MEMORY_EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    embed_memory,
)

load_dotenv()

TABLE = "user_memories"
COLUMN = "embedding"


def bootstrap_extension():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("[schema] ERROR: DATABASE_URL is not set")
        return False

    engine = create_engine(database_url)

    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    engine.dispose()
    print("[schema] pgvector extension present")
    return True


def ensure_schema():
    existing_dim = db.session.execute(
        text(
            """
            SELECT a.atttypmod
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            WHERE c.relname = :table AND a.attname = :column AND a.attnum > 0
            """
        ),
        {"table": TABLE, "column": COLUMN},
    ).scalar()

    if existing_dim is None:
        db.session.execute(
            text(
                f"ALTER TABLE {TABLE} "
                f"ADD COLUMN IF NOT EXISTS {COLUMN} vector({EMBEDDING_DIMENSION})"
            )
        )
        db.session.commit()
        print(f"[schema] added {TABLE}.{COLUMN} vector({EMBEDDING_DIMENSION})")
    elif existing_dim != EMBEDDING_DIMENSION:
        print(
            f"[schema] ERROR: {TABLE}.{COLUMN} is vector({existing_dim}) but "
            f"MEMORY_EMBEDDING_MODEL={MEMORY_EMBEDDING_MODEL} needs "
            f"vector({EMBEDDING_DIMENSION}).\n"
            f"          Drop the column and re-run to switch models "
            f"(all embeddings will be regenerated):\n"
            f"          ALTER TABLE {TABLE} DROP COLUMN {COLUMN};"
        )
        return False
    else:
        print(f"[schema] {TABLE}.{COLUMN} already vector({EMBEDDING_DIMENSION})")

    db.session.execute(
        text(
            f"CREATE INDEX IF NOT EXISTS ix_{TABLE}_user_id "
            f"ON {TABLE} (user_id)"
        )
    )
    db.session.commit()
    print(f"[schema] user_id index present")
    return True


def ensure_hnsw_index():
    db.session.execute(
        text(
            f"CREATE INDEX IF NOT EXISTS ix_{TABLE}_{COLUMN}_hnsw "
            f"ON {TABLE} USING hnsw ({COLUMN} vector_cosine_ops)"
        )
    )
    db.session.commit()
    print("[schema] hnsw cosine index present")


def backfill():
    pending = (
        UserMemory.query
        .filter(UserMemory.embedding.is_(None))
        .order_by(UserMemory.id)
        .all()
    )

    if not pending:
        print("[backfill] nothing to do  every memory already has an embedding")
        return

    print(f"[backfill] {len(pending)} memor{'y' if len(pending) == 1 else 'ies'} "
          f"without an embedding (model={MEMORY_EMBEDDING_MODEL})")

    done = 0
    failed = 0

    for memory in pending:
        vector = embed_memory(
            memory.memory_type, memory.memory_key, memory.memory_value
        )

        if vector is None:
            failed += 1
            print(f"  [skip] id={memory.id} {memory.memory_type}/{memory.memory_key} "
                  f"-- embedding unavailable, left NULL for a later run")
            continue

        db.session.query(UserMemory).filter_by(id=memory.id).update(
            {"embedding": vector}, synchronize_session=False
        )
        done += 1
        print(f"  [ok]   id={memory.id} {memory.memory_type}/{memory.memory_key}")

    db.session.commit()
    print(f"[backfill] embedded {done}, still missing {failed}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema-only", action="store_true")
    parser.add_argument("--backfill-only", action="store_true")
    parser.add_argument("--hnsw", action="store_true",
                        help="also create an HNSW cosine index (large datasets)")
    args = parser.parse_args()

    if not bootstrap_extension():
        sys.exit(1)

    from app import app

    with app.app_context():
        if not args.backfill_only:
            if not ensure_schema():
                sys.exit(1)
            if args.hnsw:
                ensure_hnsw_index()

        if not args.schema_only:
            backfill()


if __name__ == "__main__":
    main()
