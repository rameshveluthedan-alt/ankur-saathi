// What a tap on a bottom tab does. PURE (no React), so the rule can be tested on its own.
//
// Found on the click-through: tapping the "योजना / Plan" tab while on the Plan screen did NOTHING (navigating to the screen you are on is a no-op), just when a teacher
// who has chosen a skill wants to go back to choosing another.

export const TAB_RESELECT_EVENT = 'ankur-tab-reselect';

/**
 * 'navigate' to the tab's screen, or 'reselect' when it is the screen we are already on: the screen then goes back to its start
 * (the Plan screen: back to choosing a skill; every screen: scrolled to the top).
 */
export function tabTap(currentPath, tabId) {
  return currentPath === tabId ? 'reselect' : 'navigate';
}
