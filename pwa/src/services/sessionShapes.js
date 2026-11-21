// What each session length looks like, for the one line under "Today's time" on the Plan screen (21 Nov 2026). PURE (no React).
// The numbers are the server's own layout (prompts/session_shape.py: session_shape); backend/tests/test_session_shape.py reads THIS file and
// checks that every number here equals the server's, so the screen can never promise a different session from the plan it gets.
// The order of the blocks here is by length; which group gets which block depends on the day (the plan itself shows each group's minutes).
export const SESSION_SHAPES = {
  45: { anchor: 5, blocks: [16, 14, 7], extras: 1 },
  60: { anchor: 10, blocks: [18, 13, 13], extras: 2 },
  90: { anchor: 10, blocks: [30, 22, 22], extras: 3 },
};

/** { hi, en } for the chosen length, or null for a length with no shape here. */
export function sessionSummary(minutes) {
  const s = SESSION_SHAPES[minutes];
  if (!s) return null;
  const [a, b, c] = s.blocks;
  return {
    hi: `एंकर ${s.anchor} मिनट · समूहों को ${a}, ${b} और ${c} मिनट · वर्कशीट: 3 मुख्य + ${s.extras} अतिरिक्त सवाल`,
    en: `Anchor ${s.anchor} min · groups get ${a}, ${b} and ${c} min · worksheet: 3 core + ${s.extras} extra`,
  };
}
