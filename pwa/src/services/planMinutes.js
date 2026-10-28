// How long a plan is, for the plan screen's time chip and the printed plan's header. PURE (no React, no network).
// 1. The plan records it (session_minutes, set by the server on every new plan: the time the teacher chose, or the length a recorded sample plan was made for).
//    The AI's own rotation_schedule.total_minutes is never read: it is a hint the model wrote, not a fact the system recorded.
// 2. A plan made before that (no session_minutes): its blocks' minutes added up. Within 5 minutes of 45, 60 or 90 that is the preset ("87" was obviously a 90-minute
//    plan, and the chip should not look broken); further off, the exact sum.

export const PRESETS = [45, 60, 90];
const NEAR = 5;

/** { minutes, recorded } for the plan reply (the shape /plan/generate and GET /plan/... return), or null when nothing can be said */
export function planMinutes(reply) {
  const plan = (reply && reply.plan) || {};
  const recorded = Number(plan.session_minutes);
  if (Number.isFinite(recorded) && recorded > 0) return { minutes: recorded, recorded: true };
  const blocks = (plan.rotation_schedule && plan.rotation_schedule.blocks) || [];
  const sum = blocks.reduce((a, b) => a + (Number(b && b.duration_minutes) || 0), 0);
  if (!(sum > 0)) return null;
  const preset = PRESETS.find((p) => Math.abs(sum - p) <= NEAR);
  return { minutes: preset ?? sum, recorded: false };
}
