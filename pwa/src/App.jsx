import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import PlanScreen from './screens/PlanScreen';
import YojanaScreen from './screens/YojanaScreen';
import ReviewScreen from './screens/ReviewScreen';
import ProgressScreen from './screens/ProgressScreen';
import LoginScreen from './screens/LoginScreen';
import OfflineBanner from './components/OfflineBanner';
import { probe } from './services/network';
import { TAB_RESELECT_EVENT, tabTap } from './services/tabs';
import RegisterScreen from './screens/RegisterScreen';
import AccountScreen from './screens/AccountScreen';
import ChangePinScreen from './screens/ChangePinScreen';
import ConsentGate from './screens/ConsentGate';
import { getNames, getToken, setToken } from './services/api';

export const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

function BottomNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const path = location.pathname;

  const tabs = [
    { id: '/', icon: '🎯', hi: 'योजना', en: 'Plan' },
    { id: '/yojana', icon: '📋', hi: 'दैनिक योजना', en: 'Yojana' },
    { id: '/review', icon: '📷', hi: 'समीक्षा', en: 'Review' },
    { id: '/progress', icon: '📊', hi: 'प्रगति', en: 'Progress' },
    { id: '/account', icon: '👤', hi: 'प्रोफ़ाइल', en: 'Profile' },        // on every screen: log out, change password, and the leader's reset
  ];

  return (
    <nav className="bottom-nav">
      {tabs.map(t => (
        <button key={t.id} className={`nav-item ${path === t.id ? 'active' : ''}`} data-testid={`nav-${t.id.replace('/', '') || 'plan'}`}
          onClick={() => {
            if (tabTap(path, t.id) === 'reselect') {            // the screen we are on: scroll it to the top, and tell it (the Plan screen goes back to choosing a skill)
              window.scrollTo({ top: 0, behavior: 'smooth' });
              window.dispatchEvent(new CustomEvent(TAB_RESELECT_EVENT, { detail: t.id }));
            } else navigate(t.id);
          }}>
          <span className="nav-icon">{t.icon}</span>
          <span style={{fontSize:'0.7rem'}}>{t.hi}</span>
          <span style={{fontSize:'0.5rem',opacity:0.6}}>{t.en}</span>
        </button>
      ))}
    </nav>
  );
}

function AppShell() {
  const { teacher } = useAuth();
  if (!teacher || !getToken()) return <><OfflineBanner /><LoginScreen /></>;
  if (teacher.must_change_pin) return <ChangePinScreen forced />;       // a first sign-in or a reset by the school leader: choose a new password first
  if (teacher.consent_needed) return <ConsentGate />;                   // the school leader confirms the consent statement, once, before anything else
  return (
    <>
      <div style={{ position: 'sticky', top: 0, zIndex: 30 }}>
        <OfflineBanner />
        {teacher.is_demo && (
          <div data-testid="demo-banner" style={{ background: '#FFF4D6', color: '#6B4A00', fontSize: '0.7rem', padding: '4px 10px', textAlign: 'center' }}>
            डेमो अकाउंट: सिर्फ़ काल्पनिक डेटा, असली बच्चों के नाम न डालें। (Demo account: fictional data only. Do not enter real children's names.)
          </div>
        )}
      </div>
      <Routes>
        <Route path="/" element={<PlanScreen />} />
        <Route path="/yojana" element={<YojanaScreen />} />
        <Route path="/review" element={<ReviewScreen />} />
        <Route path="/progress" element={<ProgressScreen />} />
        <Route path="/register" element={<RegisterScreen />} />
        <Route path="/account" element={<AccountScreen />} />
      </Routes>
      <BottomNav />
    </>
  );
}

export default function App() {
  const [teacher, setTeacher] = useState(() => {
    // a stored teacher without a sign-in token is a leftover from before sign-in existed: do not treat it as signed in
    try { return getToken() ? JSON.parse(localStorage.getItem('ankur_teacher')) : null; } catch { return null; }
  });
  const [currentPlan, setCurrentPlan] = useState(null);
  useEffect(() => { probe(); }, []);            // on opening: can the server be reached? (a service worker can open the app with no network at all)
  const [selectedDomain, setSelectedDomain] = useState('numeracy');
  const [names, setNames] = useState({});        // {class number: name}: the teacher's own screens only, never sent to the AI
  const refreshNames = () => { if (teacher && teacher.teacher_id && getToken()) getNames(teacher.teacher_id).then(setNames).catch(() => setNames({})); };
  useEffect(() => { if (teacher && teacher.teacher_id && getToken()) refreshNames(); else setNames({}); }, [teacher && teacher.teacher_id]);

  const logout = () => { setToken(null); setTeacher(null); setCurrentPlan(null); setNames({}); };
  useEffect(() => {      // the session ended (expired, or the password was changed elsewhere), or a reset by the school leader made a new password necessary
    const ended = () => { setToken(null); setTeacher(null); };
    const mustChange = () => setTeacher(t => (t ? { ...t, must_change_pin: true } : t));
    window.addEventListener('ankur-auth-ended', ended);
    window.addEventListener('ankur-pin-change', mustChange);
    return () => { window.removeEventListener('ankur-auth-ended', ended); window.removeEventListener('ankur-pin-change', mustChange); };
  }, []);

  useEffect(() => {
    if (teacher) localStorage.setItem('ankur_teacher', JSON.stringify(teacher));
    else localStorage.removeItem('ankur_teacher');
  }, [teacher]);

  return (
    <AuthContext.Provider value={{ teacher, setTeacher, currentPlan, setCurrentPlan, selectedDomain, setSelectedDomain, names, refreshNames, logout }}>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </AuthContext.Provider>
  );
}
