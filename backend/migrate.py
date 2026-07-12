"""One-off migration: brings an existing database up to date with the
current models.py without dropping any data.

Run this once with:
    python migrate.py

Safe to re-run — every statement is idempotent (IF NOT EXISTS / catches
duplicate-column errors).
"""
import os
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

from app import app
from extensions import db

STATEMENTS = [
    # maintenance_requests grew technician_name / notes / resolved_at /
    # updated_at after some databases were first created from an older
    # version of the model.
    'ALTER TABLE maintenance_requests ADD COLUMN IF NOT EXISTS technician_name VARCHAR(150)',
    'ALTER TABLE maintenance_requests ADD COLUMN IF NOT EXISTS notes TEXT',
    'ALTER TABLE maintenance_requests ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP',
    'ALTER TABLE maintenance_requests ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT now()',
]


def run():
    with app.app_context():
        with db.engine.begin() as conn:
            for stmt in STATEMENTS:
                print(f"-> {stmt}")
                conn.execute(text(stmt))

        # Creates any tables that don't exist yet at all (e.g. audit_cycles,
        # audit_items, notifications) — never touches existing tables/columns.
        db.create_all()

        print("Migration complete.")


if __name__ == "__main__":
    run()
