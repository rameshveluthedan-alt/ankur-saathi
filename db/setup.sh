#!/bin/bash
# ============================================================================
# Ankur Saathi — Database Setup Script
# Creates the database, runs schema, and loads all seed data in correct order.
#
# Usage:
#   ./setup.sh                              # Uses default local postgres
#   ./setup.sh postgresql://user:pass@host/db  # Uses custom connection
# ============================================================================

set -e

DB_URL="${1:-postgresql://postgres@localhost/ankur_saathi}"
# Plain shell string handling (no `grep -P`, which macOS does not have): BASE_URL is the URL without its ?query, DB_NAME its last part
BASE_URL="${DB_URL%%\?*}"
QUERY_PART="${DB_URL#"$BASE_URL"}"
DB_NAME="${BASE_URL##*/}"
# The same connection, to the maintenance database "postgres": that is where a new database is created from
ADMIN_URL="${BASE_URL%/*}/postgres${QUERY_PART}"

echo "============================================"
echo "Ankur Saathi — Database Setup"
echo "============================================"
echo "Database: $DB_NAME"
echo ""

# Get the directory this script lives in
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create database if it doesn't exist
echo "[1/8] Creating database..."
if psql "$DB_URL" -tAc "SELECT 1" >/dev/null 2>&1; then
  echo "  Database $DB_NAME exists, continuing."
else
  # created through the SAME connection you gave (a bare `createdb` would use your operating-system user, which is usually not a database role)
  psql "$ADMIN_URL" -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$DB_NAME\"" || {
    echo "  ERROR: could not create the database $DB_NAME with the connection you gave (wrong password? may this user create databases?)."
    echo "  Create it yourself (for example: createdb -U <user> $DB_NAME), then run this script again."
    exit 1
  }
fi

# Enable extensions
echo "[2/8] Enabling extensions..."
psql "$DB_URL" -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" >/dev/null || \
  echo "  WARNING: could not enable uuid-ossp (it needs a database superuser); the schema below may fail."
psql "$DB_URL" -c "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null 2>&1 || \
  echo "  pgvector is not available: that is fine. Everything works except the optional semantic retrieval switch."

# Run schema
echo "[3/8] Creating L1 schema..."
psql "$DB_URL" -f "$SCRIPT_DIR/schema/01_l1_schema.sql"

echo "[4/8] Creating L2 schema..."
# If pgvector isn't available, replace vector(1024) with text (semantic retrieval then stays off)
if psql "$DB_URL" -c "SELECT '[1,2,3]'::vector" 2>/dev/null; then
  psql "$DB_URL" -f "$SCRIPT_DIR/schema/02_l2_schema.sql"
else
  sed 's/vector(1024)/text/g' "$SCRIPT_DIR/schema/02_l2_schema.sql" | \
    sed '/ivfflat/d' | psql "$DB_URL"
fi

psql "$DB_URL" -f "$SCRIPT_DIR/schema/03_content_provenance.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/schema/04_nipun_alignment.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/schema/05_coverage.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/schema/06_review_analyses.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/schema/07_register.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/schema/08_child_names.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/schema/09_auth.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/schema/10_ai_usage.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/schema/11_skill_bridges.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/schema/12_embeddings_1024.sql"      # the skill embeddings column + the vector size (a no-op without pgvector)

# Seed data — order matters (foreign key dependencies)
echo "[5/8] Seeding numeracy competency tree..."
psql "$DB_URL" -f "$SCRIPT_DIR/seeds/numeracy/01_competencies.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/seeds/numeracy/02_prerequisites.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/seeds/numeracy/03_misconceptions.sql"

echo "[6/8] Seeding literacy competency tree..."
psql "$DB_URL" -f "$SCRIPT_DIR/seeds/literacy/01_competencies.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/seeds/literacy/02_prerequisites.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/seeds/literacy/03_misconceptions.sql"

echo "[7/8] Seeding curriculum plan + L2 content..."
psql "$DB_URL" -f "$SCRIPT_DIR/seeds/curriculum/00_header.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/seeds/curriculum/01_numeracy.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/seeds/curriculum/02_literacy.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/seeds/content/01_anchors_tlm.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/seeds/content/02_interventions.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/seeds/content/03_passages.sql"

# Anchors added or edited through scripts/import_anchors.py (written by scripts/export_anchors.py)
if [ -f "$SCRIPT_DIR/seeds/content/04_imported_anchors.sql" ]; then
  psql "$DB_URL" -f "$SCRIPT_DIR/seeds/content/04_imported_anchors.sql"
fi

# Proposed alignment of each skill to NIPUN Bharat Annexure I (written by scripts/nipun_alignment.py sql)
if [ -f "$SCRIPT_DIR/seeds/content/05_nipun_alignment.sql" ]; then
  psql "$DB_URL" -f "$SCRIPT_DIR/seeds/content/05_nipun_alignment.sql"
fi

# Coverage labels per skill (written by scripts/build_coverage.py)
if [ -f "$SCRIPT_DIR/seeds/content/06_coverage.sql" ]; then
  psql "$DB_URL" -f "$SCRIPT_DIR/seeds/content/06_coverage.sql"
fi

echo "[8/8] Seeding test classroom..."
psql "$DB_URL" -f "$SCRIPT_DIR/seeds/classroom/01_profile.sql"
psql "$DB_URL" -f "$SCRIPT_DIR/seeds/classroom/02_child_names.sql"

echo ""
echo "============================================"
echo "Setup complete. Summary:"
echo "============================================"
psql "$DB_URL" -c "
SELECT 'L1: Competencies' as item, count(*) FROM competencies
UNION ALL SELECT 'L1: Prerequisites', count(*) FROM competency_prerequisites
UNION ALL SELECT 'L1: Learning Outcomes', count(*) FROM learning_outcomes
UNION ALL SELECT 'L1: Misconceptions', count(*) FROM misconceptions
UNION ALL SELECT 'L1: Curriculum Weeks', count(*) FROM curriculum_weeks
UNION ALL SELECT 'L2: Anchor Activities', count(*) FROM anchor_activities
UNION ALL SELECT 'L2: Reading Passages', count(*) FROM reading_passages
UNION ALL SELECT 'L2: Interventions', count(*) FROM intervention_templates
UNION ALL SELECT 'L2: TLM References', count(*) FROM tlm_references
UNION ALL SELECT 'Classroom: Children', count(*) FROM children
UNION ALL SELECT 'Classroom: Positions', count(*) FROM child_lakshya_positions
UNION ALL SELECT 'Classroom: Groups', count(*) FROM teaching_groups
ORDER BY 1;
"
echo ""
echo "Next steps:"
echo "  1. (optional) Semantic retrieval: 'python scripts/load_embeddings.py' loads db/seeds/content/embeddings.json (needs pgvector; see docs/SEMANTIC_RETRIEVAL.md)"
echo "  2. Start the FastAPI backend: 'uvicorn app.main:app --reload' from backend/"
