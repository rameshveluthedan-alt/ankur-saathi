"""
Ankur Saathi — Progress Service
Dashboard data, B/P/P summary, level change recommendations, MLO export.
"""

import json
import csv
import io
from datetime import date

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'prompts'))
from vision_analysis import check_level_changes


async def get_bpp_summary(db, teacher_id: str) -> list[dict]:
    """Get B/P/P distribution per domain for the Progress screen header."""
    rows = await db.fetch("""
        SELECT clp.domain_id, clp.bpp_level, COUNT(*) as count
        FROM child_lakshya_positions clp
        JOIN children c ON clp.child_id = c.id
        WHERE c.teacher_id = $1 AND c.is_active = TRUE
        GROUP BY clp.domain_id, clp.bpp_level
        ORDER BY clp.domain_id, clp.bpp_level
    """, teacher_id)
    
    # Pivot into per-domain summaries
    domains = {}
    for r in rows:
        d = r['domain_id']
        if d not in domains:
            domains[d] = {"domain_id": d, "beginner_count": 0, "progressor_count": 0, "proficient_count": 0}
        domains[d][f"{r['bpp_level']}_count"] = r['count']
    
    return list(domains.values())


async def get_children_progress(db, teacher_id: str) -> list[dict]:
    """Get per-child progress for the full Progress screen table."""
    rows = await db.fetch("""
        SELECT 
            c.roll_number, c.enrolled_grade,
            num.bpp_level as num_bpp, num.current_competency_id as num_comp,
            num_c.name_hi as num_comp_hi,
            lit.bpp_level as lit_bpp, lit.current_competency_id as lit_comp,
            lit_c.name_hi as lit_comp_hi
        FROM children c
        LEFT JOIN child_lakshya_positions num 
            ON num.child_id = c.id AND num.domain_id = 'numeracy'
        LEFT JOIN competencies num_c ON num_c.id = num.current_competency_id
        LEFT JOIN child_lakshya_positions lit 
            ON lit.child_id = c.id AND lit.domain_id = 'r1_literacy'
        LEFT JOIN competencies lit_c ON lit_c.id = lit.current_competency_id
        WHERE c.teacher_id = $1 AND c.is_active = TRUE
        ORDER BY c.roll_number
    """, teacher_id)
    
    return [
        {
            "roll_number": r['roll_number'],
            "enrolled_grade": r['enrolled_grade'],
            "numeracy_bpp": r['num_bpp'],
            "numeracy_competency_id": r['num_comp'],
            "numeracy_competency_name_hi": r['num_comp_hi'],
            "literacy_bpp": r['lit_bpp'],
            "literacy_competency_id": r['lit_comp'],
            "literacy_competency_name_hi": r['lit_comp_hi'],
        }
        for r in rows
    ]


async def get_level_change_recommendations(db, teacher_id: str) -> dict:
    """Get level change recommendations for both domains."""
    numeracy_recs = await check_level_changes(db, teacher_id, 'numeracy')
    literacy_recs = await check_level_changes(db, teacher_id, 'r1_literacy')
    return {
        "numeracy": numeracy_recs,
        "r1_literacy": literacy_recs,
    }


async def apply_level_change(db, teacher_id: str, child_id: str, domain_id: str, new_bpp: str):
    """Apply a teacher-approved level change."""
    current = await db.fetchrow("""
        SELECT current_competency_id, bpp_level 
        FROM child_lakshya_positions
        WHERE child_id = $1 AND domain_id = $2
    """, child_id, domain_id)
    
    if not current:
        return {"status": "error", "message": "Position not found"}
    
    await db.execute("""
        UPDATE child_lakshya_positions SET
            previous_competency_id = current_competency_id,
            previous_bpp_level = bpp_level,
            bpp_level = $3,
            source = 'daily',
            level_changed_at = NOW(),
            updated_at = NOW()
        WHERE child_id = $1 AND domain_id = $2
    """, child_id, domain_id, new_bpp)
    
    return {
        "status": "applied",
        "child_id": child_id,
        "domain_id": domain_id,
        "from": current['bpp_level'],
        "to": new_bpp,
    }


async def export_mlo_report_csv(db, teacher_id: str) -> str:
    """Generate CSV export for MLO (Block/District officer) reporting."""
    children = await get_children_progress(db, teacher_id)
    
    teacher = await db.fetchrow("""
        SELECT s.school_code, s.block_name, s.district_name
        FROM teachers t JOIN schools s ON t.school_id = s.id
        WHERE t.id = $1
    """, teacher_id)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'School Code', 'Block', 'District',
        'Roll No', 'Enrolled Grade',
        'Numeracy Level', 'Numeracy Competency',
        'Literacy Level', 'Literacy Competency',
    ])
    
    for c in children:
        writer.writerow([
            teacher['school_code'] if teacher else '',
            teacher['block_name'] if teacher else '',
            teacher['district_name'] if teacher else '',
            c['roll_number'], c['enrolled_grade'],
            c['numeracy_bpp'] or '', c['numeracy_competency_id'] or '',
            c['literacy_bpp'] or '', c['literacy_competency_id'] or '',
        ])
    
    return output.getvalue()
