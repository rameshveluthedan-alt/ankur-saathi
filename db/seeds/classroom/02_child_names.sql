-- ============================================================================
-- Names for the demo classroom: FICTIONAL, for the demo only.
-- Never put a real child's name in this repository. A real school's names are entered by the teacher in her own
-- app (the class register upload), stored in child_names, and shown only to her.
-- Needs db/schema/08_child_names.sql. Safe to run again.
-- ============================================================================
INSERT INTO child_names (child_id, name)
SELECT c.id, n.name
FROM children c
JOIN (VALUES
  (1, 'आरव'), (2, 'अनन्या'), (3, 'विहान'), (4, 'सान्वी'), (5, 'अर्जुन'), (6, 'इशिता'), (7, 'कबीर'), (8, 'मीरा'), (9, 'रेयांश'), (10, 'तारा'),
  (11, 'दिव्यांश'), (12, 'नेहा'), (13, 'अयान'), (14, 'काव्या'), (15, 'रुद्र'), (16, 'पीहू'), (17, 'यश'), (18, 'सिया'), (19, 'वेदांत'), (20, 'रिया'),
  (21, 'आदित्य'), (22, 'परी'), (23, 'ध्रुव'), (24, 'जिया'), (25, 'कृष'), (26, 'अवनि'), (27, 'लक्ष्य'), (28, 'मायरा'), (29, 'शौर्य'), (30, 'नव्या')
) AS n(roll, name) ON n.roll = c.roll_number
WHERE c.teacher_id = '10000001-aaaa-bbbb-cccc-000000000001'
ON CONFLICT (child_id) DO NOTHING;
