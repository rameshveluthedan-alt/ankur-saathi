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

// The bottom tabs, named for what the teacher does there (29 Oct, reviewed by Vaishnavi): two tabs both called "योजना" were hard to tell apart, and
// "प्रगति" (progress) sat too close to "प्रगतिशील" (the Progressors). The screens' titles and "कैसे काम करता है?" use the same names.
export const TABS = [
  { id: '/', icon: '🎯', hi: 'योजना बनाएँ', en: 'Make plan' },
  { id: '/yojana', icon: '📋', hi: 'आज की योजना', en: "Today's plan" },
  { id: '/review', icon: '☑️', hi: 'समीक्षा', en: 'Review' },          // checking what the children can do, by any of the three ways (not only photos: 📸 marks the photo way inside)
  { id: '/progress', icon: '📊', hi: 'कक्षा प्रगति', en: 'Class progress' },
  { id: '/account', icon: '👤', hi: 'प्रोफ़ाइल', en: 'Profile' },        // on every screen: log out, change password, and the leader's reset
];

// Which tab is lit: the screen's own, and for a screen opened from one (the class register, from "योजना बनाएँ") that one, so the teacher still sees where she is
const OPENED_FROM = { '/register': '/' };
export const activeTab = (path) => OPENED_FROM[path] || path;
