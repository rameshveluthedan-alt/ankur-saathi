// LAB PHONE TEST ONLY. Until the server sends each teach block's `signal` (the three core questions / the writing prompt), this fills one in so the plan screen's
// signal panel can be tried on a phone. Used by api.js only when the app is built or served with VITE_MOCK_SIGNAL=1; a normal build never loads this file.
// A block that already has a `signal` (the real server's, even `shape: null`) is never touched, so once the server work lands the mock does nothing.
// The contract is the server's exactly: { shape, signal_curated, maths_questions: { core, extra_count } | writing_prompt: { prompt } }.

// The same three sums for whatever maths skill: they are placeholders for the layout, not content
const MATHS_CORE = {
  beginner: ['4 + 3 = ?', '6 + 2 = ?', '5 + 4 = ?'],
  progressor: ['23 + 15 = ?', '36 + 29 = ?', '48 + 37 = ?'],
  proficient: ['245 + 132 = ?', '368 + 257 = ?', '409 + 196 = ?'],
};
const WRITING_PROMPT = 'अपने परिवार के बारे में तीन वाक्य लिखो';

// Which addresses carry a plan: the new plan (POST /plan/generate) and a stored one (GET /plan/{teacher}/{date}/{subject})
export const isPlanPath = (path) => /^\/plan\/generate(\?|$)/.test(path) || /^\/plan\/[^/]+\/\d{4}-\d{2}-\d{2}\/[^/?]+$/.test(path);

function mockSignal(domain, group) {
  if (domain === 'numeracy') return MATHS_CORE[group] ? { shape: 'maths_questions', signal_curated: true, maths_questions: { core: MATHS_CORE[group], extra_count: 2 } } : null;
  // literacy: the Beginners get a writing prompt and the other groups no panel, so the phone test sees both the writing shape and the empty one
  return group === 'beginner' ? { shape: 'writing_prompt', signal_curated: false, writing_prompt: { prompt: WRITING_PROMPT } } : { shape: null, signal_curated: false };
}

/** The plan reply with a mock `signal` on every teach block that has none. Returns a new object; the reply itself is not changed. */
export function withMockSignal(reply) {
  const blocks = reply && reply.plan && reply.plan.rotation_schedule && reply.plan.rotation_schedule.blocks;
  if (!Array.isArray(blocks)) return reply;
  const domain = reply.domain_id;
  const next = blocks.map((b) => (b && b.type === 'teach' && !('signal' in b) ? { ...b, signal: mockSignal(domain, b.teach_group) } : b));
  return { ...reply, mock_signal: true, plan: { ...reply.plan, rotation_schedule: { ...reply.plan.rotation_schedule, blocks: next } } };
}
