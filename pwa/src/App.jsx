import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import PlanScreen from './screens/PlanScreen';
import YojanaScreen from './screens/YojanaScreen';
import ReviewScreen from './screens/ReviewScreen';
import ProgressScreen from './screens/ProgressScreen';
import LoginScreen from './screens/LoginScreen';

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
  ];

  return (
    <nav className="bottom-nav">
      {tabs.map(t => (
        <button key={t.id} className={`nav-item ${path === t.id ? 'active' : ''}`}
          onClick={() => navigate(t.id)}>
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
  if (!teacher) return <LoginScreen />;
  return (
    <>
      <Routes>
        <Route path="/" element={<PlanScreen />} />
        <Route path="/yojana" element={<YojanaScreen />} />
        <Route path="/review" element={<ReviewScreen />} />
        <Route path="/progress" element={<ProgressScreen />} />
      </Routes>
      <BottomNav />
    </>
  );
}

export default function App() {
  const [teacher, setTeacher] = useState(() => {
    try { return JSON.parse(localStorage.getItem('ankur_teacher')); } catch { return null; }
  });
  const [currentPlan, setCurrentPlan] = useState(null);
  const [selectedDomain, setSelectedDomain] = useState('numeracy');

  useEffect(() => {
    if (teacher) localStorage.setItem('ankur_teacher', JSON.stringify(teacher));
    else localStorage.removeItem('ankur_teacher');
  }, [teacher]);

  return (
    <AuthContext.Provider value={{ teacher, setTeacher, currentPlan, setCurrentPlan, selectedDomain, setSelectedDomain }}>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </AuthContext.Provider>
  );
}
