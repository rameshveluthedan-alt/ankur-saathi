"""
Which children to photograph when a group is too large to do everyone.

Method: SYSTEMATIC sampling on the group's sorted roll numbers.
  * interval k = group size / sample size
  * a start point in [0, k) picks the first child, then every k-th child after that
  * the start moves a little every day, in golden-ratio steps, so the sample is spread evenly over the whole roll list,
    differs from day to day, and gives every child a turn over a few days
  * deterministic: the same group on the same day always gets the same sample, so the plan, the Review screen and the
    teacher's records agree

What a sample is and is not: it gives a ROUGH picture of the group (enough to decide to re-teach or move on when the
picture is clear), but a child's own level change needs that child's own evidence on several days. margin_points() puts
a rough number on the first, under an assumed spread of children's accuracy; it is a guide, not a guarantee.
"""

import math
import zlib

GOLDEN = 0.6180339887498949
EVERYONE_UP_TO = 8            # a group this small is simply done in full
MIN_SAMPLE = 6
SAMPLE_FRACTION = 0.4
ASSUMED_SD = 0.30             # how far apart children's accuracies typically are (assumed, not measured)


def default_sample_size(group_size: int) -> int:
    """Everyone in a small group; otherwise 40% of the group, never fewer than 6."""
    if group_size <= EVERYONE_UP_TO:
        return group_size
    return min(group_size, max(MIN_SAMPLE, math.ceil(group_size * SAMPLE_FRACTION)))


def _salt(level: str, competency_id: str) -> int:
    """So that the three groups of one class do not all start at the same point of their lists."""
    return zlib.crc32(f"{level}:{competency_id}".encode("utf-8")) % 1000


def systematic_sample(rolls, n: int, day: int, salt: int = 0) -> list:
    """n roll numbers spread evenly over the sorted list, starting at a point that moves with `day`."""
    rolls = sorted({int(r) for r in rolls})
    total = len(rolls)
    if n >= total:
        return rolls
    if n <= 0:
        return []
    k = total / n
    start = (((day + salt) * GOLDEN) % 1.0) * k            # in [0, k)
    return [rolls[int(start + i * k)] for i in range(n)]    # k > 1, so the positions are distinct and below `total`


def replace_absent(rolls, sample, absent) -> list:
    """
    An absent sampled child is replaced by the nearest child on the roll list who is not already in the sample and is
    not absent, which keeps the sample spread out. If no one is left to swap in, the sample is simply one shorter.
    """
    rolls = sorted({int(r) for r in rolls})
    absent = {int(a) for a in absent or []}
    out = [r for r in sample if r not in absent]
    pool = [r for r in rolls if r not in set(sample) and r not in absent]
    for gone in sorted(r for r in sample if r in absent):
        if not pool:
            break
        pos = rolls.index(gone)
        best = min(pool, key=lambda r: (abs(rolls.index(r) - pos), r))
        out.append(best)
        pool.remove(best)
    return sorted(out)


def margin_points(n: int, group_size: int, sd: float = ASSUMED_SD) -> int:
    """Roughly how many percentage points the group's average accuracy could be off by (95%), for a sample of n children."""
    if n >= group_size or n <= 0 or group_size <= 1:
        return 0
    fpc = math.sqrt((group_size - n) / (group_size - 1))
    return int(round(1.96 * sd / math.sqrt(n) * fpc * 100))


def sample_for_group(rolls, plan_date, level: str, competency_id: str, size: int = None, absent=None) -> dict:
    """The suggested children for one group on one day."""
    rolls = sorted({int(r) for r in rolls})
    total = len(rolls)
    n = default_sample_size(total) if size is None else max(0, min(int(size), total))
    chosen = systematic_sample(rolls, n, plan_date.toordinal(), _salt(level, competency_id))
    if absent:
        chosen = replace_absent(rolls, chosen, absent)
    return {"mode": "all" if n >= total else "sample", "size": len(chosen), "group_size": total, "rolls": chosen,
            "margin_points": margin_points(len(chosen), total)}
