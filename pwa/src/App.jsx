import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import PlanScreen from './screens/PlanScreen';
import YojanaScreen from './screens/YojanaScreen';
import ReviewScreen from './screens/ReviewScreen';
import ProgressScreen from './screens/ProgressScreen';
import LoginScreen from './screens/LoginScreen';

// ── Auth Context ──
export const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

function BottomNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const path = location.pathname;

  const tabs = [
    { id: '/', icon: '🎯', label: 'योजना', labelEn: 'Plan' },
    { id: '/yojana', icon: '📋', label: 'दैनिक योजना', labelEn: 'Yojana' },
    { id: '/review', icon: '📷', label: 'समीक्षा', labelEn: 'Review' },
    { id: '/progress', icon: '📊', label: 'प्रगति', labelEn: 'Progress' },
  ];

  return (
    <nav className="bottom-nav">
      {tabs.map(t => (
        <button
          key={t.id}
          className={`nav-item ${path === t.id ? 'active' : ''}`}
          onClick={() => navigate(t.id)}
        >
          <span className="nav-icon">{t.icon}</span>
          {t.label}
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
