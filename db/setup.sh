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
DB_NAME=$(echo "$DB_URL" | grep -oP '[^/]+$' | cut -d'?' -f1)

echo "============================================"
echo "Ankur Saathi — Database Setup"
echo "============================================"
echo "Database: $DB_NAME"
echo ""

# Get the directory this script lives in
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create database if it doesn't exist
echo "[1/8] Creating database..."
psql "$DB_URL" -c "SELECT 1" 2>/dev/null || \
  createdb "$DB_NAME" 2>/dev/null || \
  echo "  Database already exists, continuing."

# Enable extensions
echo "[2/8] Enabling extensions..."
psql "$DB_URL" -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" 2>/dev/null
psql "$DB_URL" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || \
  echo "  pgvector not available — L2 semantic search will use keyword fallback."

# Run schema
echo "[3/8] Creating L1 schema..."
psql "$DB_URL" -f "$SCRIPT_DIR/schema/01_l1_schema.sql"

echo "[4/8] Creating L2 schema..."
# If pgvector isn't available, replace vector(1536) with text
if psql "$DB_URL" -c "SELECT '[1,2,3]'::vector" 2>/dev/null; then
  psql "$DB_URL" -f "$SCRIPT_DIR/schema/02_l2_schema.sql"
else
  sed 's/vector(1536)/text/g' "$SCRIPT_DIR/schema/02_l2_schema.sql" | \
    sed '/ivfflat/d' | psql "$DB_URL"
fi

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

echo "[8/8] Seeding test classroom..."
psql "$DB_URL" -f "$SCRIPT_DIR/seeds/classroom/01_profile.sql"

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
echo "  1. Run 'python scripts/populate_embeddings.py' to populate L2 vector embeddings"
echo "  2. Start the FastAPI backend: 'uvicorn app:app --reload'"
