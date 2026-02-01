import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment")
    exit(1)

engine = create_engine(DATABASE_URL)

migration_sql = """
CREATE TABLE IF NOT EXISTS weekly_checkins (
    id SERIAL PRIMARY KEY,
    client_protocol_id INTEGER NOT NULL REFERENCES client_protocols(id) ON DELETE CASCADE,
    week_number INTEGER NOT NULL,
    primary_symptom_rating INTEGER NOT NULL CHECK (primary_symptom_rating BETWEEN 1 AND 10),
    energy_level INTEGER NOT NULL CHECK (energy_level BETWEEN 1 AND 10),
    sleep_quality INTEGER NOT NULL CHECK (sleep_quality BETWEEN 1 AND 10),
    notes TEXT,
    what_helped TEXT,
    what_struggled TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(client_protocol_id, week_number, DATE(submitted_at))
);

CREATE TABLE IF NOT EXISTS protocol_outcomes (
    id SERIAL PRIMARY KEY,
    client_protocol_id INTEGER NOT NULL REFERENCES client_protocols(id) ON DELETE CASCADE,
    protocol_id INTEGER NOT NULL REFERENCES protocols(id),
    overall_effectiveness INTEGER CHECK (overall_effectiveness BETWEEN 1 AND 5),
    symptoms_improved BOOLEAN,
    would_recommend BOOLEAN,
    what_improved_most TEXT,
    what_was_hardest TEXT,
    suggestions TEXT,
    practitioner_effectiveness INTEGER CHECK (practitioner_effectiveness BETWEEN 1 AND 5),
    completed_by VARCHAR(50) DEFAULT 'client',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(client_protocol_id)
);

CREATE INDEX IF NOT EXISTS idx_weekly_checkins_protocol ON weekly_checkins(client_protocol_id);
CREATE INDEX IF NOT EXISTS idx_weekly_checkins_week ON weekly_checkins(week_number);
CREATE INDEX IF NOT EXISTS idx_weekly_checkins_date ON weekly_checkins(submitted_at);
CREATE INDEX IF NOT EXISTS idx_protocol_outcomes_protocol ON protocol_outcomes(protocol_id);
CREATE INDEX IF NOT EXISTS idx_protocol_outcomes_effectiveness ON protocol_outcomes(overall_effectiveness);
"""

try:
    with engine.connect() as conn:
        conn.execute(text(migration_sql))
        conn.commit()

    # Verify
    with engine.connect() as conn:
        wc = conn.execute(text("SELECT COUNT(*) FROM weekly_checkins")).scalar()
        po = conn.execute(text("SELECT COUNT(*) FROM protocol_outcomes")).scalar()

    print("✅ Migration complete!")
    print(f"   weekly_checkins: {wc} rows")
    print(f"   protocol_outcomes: {po} rows")

except Exception as e:
    print(f"❌ Migration failed: {e}")
