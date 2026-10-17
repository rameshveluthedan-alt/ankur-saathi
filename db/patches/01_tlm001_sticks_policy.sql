-- ============================================================================
-- Patch: TLM-001 (bundling sticks) policy
-- Replaces the old "each child needs 9 bundles + 9 loose sticks" entry with the policy
-- decided after reviewing the research: teacher demo kit for every group, pair kits for
-- Beginners only, drawn tens-and-ones for the other groups.
-- db/seeds/content/01_anchors_tlm.sql already carries this text, so a fresh database
-- built by setup.sh needs no patch. Run it ONCE on an existing database:
--   psql -U postgres -d ankur_saathi -f db/patches/01_tlm001_sticks_policy.sql
-- ============================================================================
UPDATE tlm_references SET
  description_en = 'Sets of 10 sticks bundled with rubber bands for place value. Single sticks as ones, bundles as tens. Mainly the teacher''s demonstration; children handle sticks only in the Beginner group, in pairs.',
  diy_instructions = 'Collect thin sticks or straws and bundle groups of 10 with rubber bands BEFORE class; children never bundle during the lesson. Teacher demo kit: 9 bundles + 9 loose sticks (99 sticks). Beginner pair kit: 4 bundles + 9 loose sticks (49 sticks) for each pair, kept in a bag or box. Rule a Tens | Ones frame on a sheet or the notebook cover. Count the sticks back in at the end. Other groups draw tens as lines and ones as dots instead of using sticks.'
WHERE id = 'TLM-001';
