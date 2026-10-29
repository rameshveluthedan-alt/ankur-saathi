// The phone's Back button inside one screen: the Review's steps, a dialog (navigation D). An extra entry in the browser's history carries a marker
// next to React Router's own fields (usr, key and idx are copied), so the router sees the same location and the screen itself answers the Back press.
export const historyState = () => (typeof window !== 'undefined' && window.history.state) || {};
export const pushMarks = (marks) => window.history.pushState({ ...historyState(), ...marks }, '');
export const replaceMarks = (marks) => window.history.replaceState({ ...historyState(), ...marks }, '');

// "← वापस" (navigation F): back to the screen the teacher came from, if it was in the app (React Router counts its entries in idx); else to the Plan screen
export const backOrHome = (navigate, home = '/') => (historyState().idx > 0 ? navigate(-1) : navigate(home));
