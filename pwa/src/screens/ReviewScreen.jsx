import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../App';
import { recordDecisions, recordObserved, recordORF, analysePhotos, getSavedAnalyses, getReviewCoverage, getReviewChannels } from '../services/api';
import { compressImage } from '../utils/imageCompress';
import { useOnline } from '../components/OfflineBanner';
import { GROUP_LABELS, GROUP_ORDER } from '../tiers';
import Bi from '../components/Bi';
import { bi } from '../services/language';
import { notify } from '../services/notify';
import { localToday } from '../services/today';

// an English translation on the same line, after its Hindi (hidden by the "Hindi only" setting)
const En = ({ children }) => <span className="en en-inline" lang="en">{children}</span>;

export default function ReviewScreen() {
  const { teacher, currentPlan, selectedDomain, names } = useAuth();
  const [step, setStep] = useState(1);
  const [decisions, setDecisions] = useState({});
  const [channel, setChannel] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [sheetLevel, setSheetLevel] = useState('progressor');   // which group's worksheet the photos are of
  const [loading, setLoading] = useState(false);
  const online = useOnline();            // sending photos for analysis needs the internet (they go to the AI); the chosen photos stay on the screen
  const [observedItems, setObservedItems] = useState([]);
  const [orfEntry, setOrfEntry] = useState({ roll_number: '', cwpm: '', error_count: '', passage_id: 'RP-004' });
  const fileInput = useRef(null);

  const today = localToday();
  const groups = currentPlan?.groups || [];
  const [savedAnalyses, setSavedAnalyses] = useState([]);
  const [coverage, setCoverage] = useState(null);       // who in this group is done today, and who is left
  const [dupNotice, setDupNotice] = useState('');       // the same photo picked twice
  const [sampleMode, setSampleMode] = useState('sample');   // a large group: photograph the suggested sample, or everyone
  const [absent, setAbsent] = useState([]);                 // sampled children who are away today
  const [channelsInfo, setChannelsInfo] = useState(null);    // which way of capturing evidence each group's skill needs today
  const [showAllChannels, setShowAllChannels] = useState(false);
  const LEVEL_HI = { beginner: 'शुरुआती', progressor: 'प्रगतिशील', proficient: 'दक्ष' };
  const refreshSaved = () => {
    if (!teacher?.teacher_id || !selectedDomain) return;
    getSavedAnalyses(teacher.teacher_id, today, selectedDomain).then(setSavedAnalyses).catch(() => setSavedAnalyses([]));
  };
  useEffect(refreshSaved, [teacher?.teacher_id, selectedDomain, today]);
  useEffect(() => {
    if (!teacher?.teacher_id || !selectedDomain) return;
    getReviewChannels(teacher.teacher_id, today, selectedDomain).then(setChannelsInfo).catch(() => setChannelsInfo(null));
  }, [teacher?.teacher_id, selectedDomain, today]);
  const ALL_CHANNELS = ['observed', 'photo', 'orf'];
  const relevantChannels = channelsInfo && channelsInfo.has_plan && Object.keys(channelsInfo.channels).length ? Object.keys(channelsInfo.channels) : ALL_CHANNELS;
  const visibleChannels = showAllChannels ? ALL_CHANNELS : relevantChannels;
  const levelsFor = (ch) => (channelsInfo && channelsInfo.has_plan && channelsInfo.channels[ch]) || ['beginner', 'progressor', 'proficient'];
  const activeChannel = channel === 'observed' ? 'observed' : channel === 'orf' ? 'orf' : 'photo';
  const levelInfo = (ch) => (channelsInfo?.levels || []).find(l => l.channel === ch && l.level === sheetLevel);
  const observedLevel = levelInfo('observed');
  const orfLevel = levelInfo('orf');
  useEffect(() => {      // a single relevant channel needs no choosing
    if (step === 2 && !channel && !showAllChannels && relevantChannels.length === 1) setChannel(relevantChannels[0]);
  }, [step, channelsInfo]);
  useEffect(() => {      // keep the selected group one that uses this channel
    if (!channel) return;
    const allowed = levelsFor(activeChannel);
    if (!allowed.includes(sheetLevel)) setSheetLevel(allowed[0]);
  }, [channel, channelsInfo]);
  const refreshCoverage = () => {
    if (!teacher?.teacher_id || !selectedDomain) return;
    getReviewCoverage(teacher.teacher_id, today, selectedDomain, sheetLevel, { absent, channel: activeChannel }).then(setCoverage).catch(() => setCoverage(null));
  };
  useEffect(() => { setAbsent([]); }, [sheetLevel]);
  useEffect(refreshCoverage, [teacher?.teacher_id, selectedDomain, today, sheetLevel, savedAnalyses.length, absent.join(','), activeChannel]);
  const openSaved = (a) => { setAnalysisResult(a.result); setSheetLevel(a.worksheet_level); setStep(3); };

  const handleDecision = (groupLabel, decision) => {
    setDecisions(d => ({ ...d, [groupLabel]: d[groupLabel] === decision ? null : decision }));
  };

  const submitDecisions = async () => {
    setLoading(true);
    try {
      await recordDecisions(teacher.teacher_id, today, selectedDomain, decisions);
      setStep(2);
    } catch (e) { notify(bi('समस्या', 'Error') + ': ' + e.message, 'error'); }
    setLoading(false);
  };

  // A fingerprint of the photo's bytes, so the very same file is never added twice
  const fileKey = async (file) => {
    try {
      if (window.crypto && window.crypto.subtle) {
        const h = await window.crypto.subtle.digest('SHA-256', await file.arrayBuffer());
        return Array.from(new Uint8Array(h)).map(b => b.toString(16).padStart(2, '0')).join('');
      }
    } catch (err) { /* fall through */ }
    return `${file.name}:${file.size}:${file.lastModified}`;
  };

  const handlePhotoCapture = async (e) => {
    const files = Array.from(e.target.files);
    e.target.value = '';
    const seen = new Set(photos.map(p => p.__key).filter(Boolean));
    const fresh = [];
    let duplicates = 0;
    for (const f of files) {
      const key = await fileKey(f);
      if (seen.has(key)) { duplicates += 1; continue; }
      seen.add(key);
      const small = await compressImage(f);          // 5-10 MB phone photos become a few hundred KB
      small.__key = key;
      fresh.push(small);
    }
    setDupNotice(duplicates ? bi('यह फ़ोटो पहले ही जोड़ी जा चुकी है', 'This photo was already added') : '');
    setPhotos(prev => [...prev, ...fresh].slice(0, 6));
  };

  const submitPhotos = async (opts = {}) => {
    if (!photos.length || !currentPlan) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('teacher_id', teacher.teacher_id);
      fd.append('session_date', today);
      fd.append('domain_id', selectedDomain);
      fd.append('competency_id', currentPlan.selected_competency_id);
      fd.append('worksheet_level', sheetLevel);
      fd.append('teacher_pre_judgment', decisions[sheetLevel] || '');
      fd.append('on_duplicate', 'skip');                       // a child already analysed today keeps the earlier result
      if (opts.replaceRolls && opts.replaceRolls.length) fd.append('replace_rolls', opts.replaceRolls.join(','));
      photos.forEach(p => fd.append('photos', p));
      const result = await analysePhotos(teacher.teacher_id, fd);
      setAnalysisResult(result);
      setStep(3);
      refreshSaved();
      refreshCoverage();
    } catch (e) { notify(bi('विश्लेषण में समस्या', 'Analysis error') + ': ' + e.message, 'error'); }
    setLoading(false);
  };

  const addObservedItem = (rollNumber, competencyId, status) => {
    setObservedItems(prev => [...prev.filter(i => !(i.roll_number === rollNumber && i.competency_id === competencyId)),
      { roll_number: parseInt(rollNumber), competency_id: competencyId, status }
    ]);
  };

  const submitObserved = async () => {
    if (!observedItems.length) return;
    setLoading(true);
    try {
      await recordObserved(teacher.teacher_id, today, observedItems);
      notify(`✅ ${observedItems.length} ` + bi('अवलोकन दर्ज हुए', 'observations recorded'), 'success');
      setObservedItems([]);
      refreshCoverage();
    } catch (e) { notify(bi('समस्या', 'Error') + ': ' + e.message, 'error'); }
    setLoading(false);
  };

  const submitORF = async () => {
    if (!orfEntry.roll_number || !orfEntry.cwpm) return;
    setLoading(true);
    try {
      const result = await recordORF(teacher.teacher_id, {
        session_date: today, roll_number: parseInt(orfEntry.roll_number),
        passage_id: orfEntry.passage_id, cwpm: parseInt(orfEntry.cwpm),
        error_count: parseInt(orfEntry.error_count || 0),
      });
      notify(`✅ ${bi('रोल', 'Roll')} ${orfEntry.roll_number}: ${orfEntry.cwpm} ${bi('सही शब्द/मिनट', 'CWPM')} → ${result.classification}`, 'success');
      setOrfEntry({ roll_number: '', cwpm: '', error_count: '', passage_id: 'RP-004' });
      refreshCoverage();
    } catch (e) { notify(bi('समस्या', 'Error') + ': ' + e.message, 'error'); }
    setLoading(false);
  };

  return (
    <div className="screen">
      <div className="screen-header">
        <h1>📷 <Bi hi="समीक्षा" en="Review" inline /></h1>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
          चरण<span className="en en-inline" lang="en">Step</span> {step}/3
        </span>
      </div>

      {/* An analysis already done today can always be reopened, even after pressing Back or reloading */}
      {step !== 3 && savedAnalyses.length > 0 && (
        <div className="card" style={{ background: '#EAF6EE', borderColor: '#BFE3CC' }} data-testid="saved-analyses">
          <div style={{ fontWeight: 600, fontSize: '0.875rem', marginBottom: 6 }}>🔍 आज का विश्लेषण उपलब्ध है<span className="en en-inline" lang="en">Today's analysis, tap to open</span></div>
          {savedAnalyses.map(a => (
            <button key={a.id} type="button" className="btn btn-secondary" onClick={() => openSaved(a)}
              style={{ width: '100%', display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: '0.8125rem' }}>
              <span>{LEVEL_HI[a.worksheet_level] || a.worksheet_level} · {a.result.children_analysed} बच्चे · {Math.round((a.result.group_accuracy || 0) * 100)}%</span>
              <span style={{ color: 'var(--text-secondary)' }}>{new Date(a.created_at).toLocaleTimeString('hi-IN', { hour: '2-digit', minute: '2-digit' })} देखें →</span>
            </button>
          ))}
        </div>
      )}

      {/* STEP 1: Decisions */}
      {step === 1 && (
        <>
          <h2 style={{ marginBottom: 4 }}>आज हर समूह कैसा रहा?</h2>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: 16 }}>
            AI विश्लेषण से पहले अपना आकलन दर्ज करें।
            <span className="en" lang="en">How did each group do today? Record your judgment before AI analysis.</span>
          </p>

          {groups.map(g => (
            <div key={g.label} className={`card tier-card tier-${g.label}`}>
              <div className="card-header">
                <div>
                  <span className={`badge badge-${g.label}`}>{GROUP_LABELS[g.label]?.hi}</span>
                  <span className="en en-inline" lang="en">{GROUP_LABELS[g.label]?.en}</span>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{g.count} बच्चे</span>
              </div>
              <div className="decision-row">
                <button className={`decision-btn advance ${decisions[g.label] === 'advance' ? 'selected' : ''}`}
                  onClick={() => handleDecision(g.label, 'advance')}>
                  <Bi hi="▲ आगे बढ़ें" en="Advance" />
                </button>
                <button className={`decision-btn reteach ${decisions[g.label] === 'reteach' ? 'selected' : ''}`}
                  onClick={() => handleDecision(g.label, 'reteach')}>
                  <Bi hi="🔄 दोहराएँ" en="Re-teach" />
                </button>
                <button className={`decision-btn ${decisions[g.label] === 'not_sure' ? 'selected' : ''}`}
                  onClick={() => handleDecision(g.label, 'not_sure')}>
                  <Bi hi="❓ पक्का नहीं" en="Not sure" />
                </button>
              </div>
            </div>
          ))}

          <button className="btn btn-primary" onClick={submitDecisions} disabled={loading} style={{ marginTop: 8, flexDirection: 'column', gap: 0 }}>
            {loading ? <Bi hi="दर्ज हो रहा..." en="Recording" /> : <Bi hi="दर्ज करें → साक्ष्य कैप्चर" en="Record → Capture Evidence" />}
          </button>
        </>
      )}

      {/* STEP 2: Evidence capture */}
      {step === 2 && (
        <>
          <h2 style={{ marginBottom: 12 }}><Bi hi="साक्ष्य कैप्चर करें" en="Capture Evidence" /></h2>

          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            {[
              { id: 'observed', icon: '✓', hi: 'अवलोकन', en: 'Observed' },
              { id: 'photo', icon: '📸', hi: 'फ़ोटो', en: 'Photo' },
              { id: 'orf', icon: '⏱️', hi: 'पठन प्रवाह', en: 'Reading aloud' },
            ].filter(ch => visibleChannels.includes(ch.id)).map(ch => (
              <button key={ch.id} className={`domain-tab ${channel === ch.id ? 'active' : ''}`} data-testid={`channel-${ch.id}`}
                onClick={() => setChannel(ch.id)}>
                {ch.icon} <Bi hi={ch.hi} en={ch.en} />
                {channelsInfo?.has_plan && channelsInfo.channels[ch.id] && <div style={{ fontSize: '0.55rem', fontWeight: 400 }}>{channelsInfo.channels[ch.id].map(l => LEVEL_HI[l]).join(', ')}</div>}
              </button>
            ))}
          </div>
          {channelsInfo?.has_plan && relevantChannels.length < 3 && (
            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', margin: '-8px 0 12px' }} data-testid="channel-hint">
              आज के कौशल के लिए यही तरीका चाहिए<span className="en en-inline" lang="en">Today's skills need this way</span> ·{' '}
              <button type="button" onClick={() => setShowAllChannels(v => !v)} style={{ background: 'none', border: 'none', color: 'var(--green-dark)', textDecoration: 'underline', fontSize: '0.75rem', padding: '0 4px', minHeight: 44, fontFamily: 'inherit' }}>
                {showAllChannels ? <Bi hi="सिर्फ़ ज़रूरी दिखाएँ" en="Show only needed" inline /> : <Bi hi="दूसरे तरीके" en="Other ways" inline />}
              </button>
            </div>
          )}

          {/* Observed: the group's children as a checklist (the skill is filled in from today's plan) */}
          {channel === 'observed' && observedLevel && (() => {
            const sample = coverage?.sample;
            const big = coverage && coverage.group_rolls.length > 8 && sample;
            const useSample = big && sampleMode === 'sample';
            const rolls = coverage ? (useSample ? sample.rolls : coverage.group_rolls) : observedLevel.rolls;
            const saved = new Set(coverage?.analysed_rolls || []);
            const statusOf = (r) => (observedItems.find(i => i.roll_number === r && i.competency_id === observedLevel.competency_id) || {}).status;
            const tap = (r, s) => statusOf(r) === s
              ? setObservedItems(prev => prev.filter(i => !(i.roll_number === r && i.competency_id === observedLevel.competency_id)))
              : addObservedItem(r, observedLevel.competency_id, s);
            const btn = (on, color) => ({ minWidth: 52, minHeight: 44, padding: '5px 4px', borderRadius: 8, border: `1px solid ${color}`, fontSize: '0.75rem', fontWeight: 600, background: on ? color : 'white', color: on ? 'white' : color });
            const mode = (on) => ({ flex: 1, minHeight: 40, padding: '5px 4px', borderRadius: 8, border: '1px solid var(--border)', fontSize: '0.75rem', fontWeight: 600, background: on ? 'var(--green-dark)' : 'var(--surface)', color: on ? 'white' : 'var(--text)' });
            return (
              <div className="card" data-testid="observed-list">
                <h3 style={{ marginBottom: 4 }}>✓ <Bi hi="शिक्षक अवलोकन" en="Teacher Observation" inline /></h3>
                {levelsFor('observed').length > 1 && (
                  <div style={{ display: 'flex', gap: 6, margin: '6px 0' }}>
                    {levelsFor('observed').map(l => <button key={l} type="button" className={`tier-option tier-${l} ${sheetLevel === l ? 'selected' : ''}`} onClick={() => setSheetLevel(l)}>{GROUP_LABELS[l].mark} {LEVEL_HI[l]}</button>)}
                  </div>
                )}
                <p style={{ fontSize: '0.8125rem', margin: '4px 0 8px' }}>कौशल<span className="en en-inline" lang="en">Skill</span>: <b>{observedLevel.competency_id}</b> · {observedLevel.name_hi}</p>
                {big && (
                  <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                    <button type="button" data-testid="obs-mode-sample" style={mode(useSample)} onClick={() => setSampleMode('sample')}>नमूना<En>Sample</En> {sample.size}/{sample.group_size}</button>
                    <button type="button" style={mode(!useSample)} onClick={() => setSampleMode('all')}>सभी<En>Everyone</En> {coverage.group_rolls.length}</button>
                  </div>
                )}
                {rolls.map(r => (
                  <div key={r} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                    <b style={{ width: 78, fontSize: '0.8125rem' }}>रोल {r}{names && names[r] && <div style={{ fontSize: '0.7rem', fontWeight: 500 }} data-testid={`name-${r}`}>{names[r]}</div>}{coverage?.labels?.[r] && <div style={{ fontSize: '0.55rem', fontWeight: 400, color: 'var(--text-secondary)' }}>{coverage.labels[r]}</div>}</b>
                    <button type="button" data-testid={`obs-${r}-achieved`} style={btn(statusOf(r) === 'achieved', 'var(--proficient-ink)')} onClick={() => tap(r, 'achieved')}>A</button>
                    <button type="button" data-testid={`obs-${r}-partially_achieved`} style={btn(statusOf(r) === 'partially_achieved', 'var(--progressor-ink)')} onClick={() => tap(r, 'partially_achieved')}>PA</button>
                    <button type="button" data-testid={`obs-${r}-not_achieved`} style={btn(statusOf(r) === 'not_achieved', 'var(--beginner-ink)')} onClick={() => tap(r, 'not_achieved')}>NA</button>
                    {saved.has(r) && <span style={{ fontSize: '0.7rem', color: 'var(--proficient)' }} title="आज दर्ज हो चुका">✓</span>}
                    {useSample && !saved.has(r) && <button type="button" data-testid={`obs-absent-${r}`} style={{ marginLeft: 'auto', minHeight: 44, padding: '0 6px', background: 'none', border: 'none', fontSize: '0.75rem', color: 'var(--text-secondary)', textDecoration: 'underline', fontFamily: 'inherit' }}
                      onClick={() => setAbsent(prev => [...prev, r])}>अनुपस्थित</button>}
                  </div>
                ))}
                {useSample && <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 6 }} data-testid="sample-note-obs">नमूना मोटी तस्वीर देता है (लगभग ±{sample.margin_points} अंक)।<span className="en" lang="en">A sample gives a rough picture of the group.</span></p>}
                <button className="btn btn-primary" onClick={submitObserved} disabled={loading || !observedItems.length} style={{ marginTop: 8 }} data-testid="obs-submit">
                  {loading ? 'दर्ज हो रहा...' : <>✓ {observedItems.length} अवलोकन जमा करें<En>Submit</En></>}
                </button>
              </div>
            );
          })()}
          {/* Observed: the manual form, used only when today's plan is not available */}
          {channel === 'observed' && !observedLevel && (
            <div className="card">
              <h3 style={{ marginBottom: 4 }}>✓ <Bi hi="शिक्षक अवलोकन" en="Teacher Observation" inline /></h3>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
                <Bi hi="हर बच्चे के लिए A / PA / NA दबाएँ" en="Tap A / PA / NA for each child" />
              </p>
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <input type="number" inputMode="numeric" placeholder="रोल नं." aria-label="रोल नंबर (Roll number)" min="1"
                  style={{ flex: 1, padding: 8, borderRadius: 6, border: '1px solid var(--border)', fontFamily: 'inherit' }} id="obs-roll" />
                <input type="text" placeholder="कौशल कोड (N1.2.4)" aria-label="कौशल कोड (Skill code)"
                  style={{ flex: 1, padding: 8, borderRadius: 6, border: '1px solid var(--border)', fontFamily: 'inherit' }} id="obs-comp" />
              </div>
              <div className="decision-row">
                {[['achieved', <Bi hi="✓ A प्राप्त" en="Achieved" />], ['partially_achieved', <Bi hi="~ PA आंशिक" en="Partial" />], ['not_achieved', <Bi hi="✗ NA प्राप्त नहीं" en="Not Achieved" />]].map(([s, label]) => (
                  <button key={s} className="decision-btn" onClick={() => {
                    const roll = document.getElementById('obs-roll').value;
                    const comp = document.getElementById('obs-comp').value;
                    if (roll && comp) addObservedItem(roll, comp, s);
                  }}>{label}</button>
                ))}
              </div>
              {observedItems.length > 0 && (
                <div style={{ marginTop: 8, fontSize: '0.8125rem' }}>
                  <strong>{observedItems.length} दर्ज<En>recorded</En>:</strong>{' '}
                  {observedItems.map(i => `R${i.roll_number}:${i.status[0].toUpperCase()}`).join(', ')}
                </div>
              )}
              <button className="btn btn-primary" onClick={submitObserved} disabled={loading || !observedItems.length} style={{ marginTop: 8 }}>
                {loading ? 'दर्ज हो रहा...' : <>✓ {observedItems.length} अवलोकन जमा करें<En>Submit</En></>}
              </button>
            </div>
          )}

          {/* Photo */}
          {channel === 'photo' && (
            <div className="card">
              <h3 style={{ marginBottom: 4 }}>📸 <Bi hi="वर्कशीट फ़ोटो" en="Worksheet Photos" inline /></h3>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '4px 0' }}>किस समूह की वर्कशीट?<span className="en en-inline" lang="en">Which group's sheet?</span></div>
              <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                {GROUP_ORDER.filter((id) => levelsFor('photo').includes(id)).map((id) => (
                  <button key={id} type="button" onClick={() => setSheetLevel(id)} className={`tier-option tier-${id} ${sheetLevel === id ? 'selected' : ''}`}>
                    {GROUP_LABELS[id].mark} <Bi hi={GROUP_LABELS[id].hi} en={GROUP_LABELS[id].en} />
                  </button>
                ))}
              </div>
              {coverage && coverage.group_rolls && coverage.group_rolls.length > 0 && (() => {
                const sample = coverage.sample;
                const big = coverage.group_rolls.length > 8 && sample;
                const useSample = big && sampleMode === 'sample';
                const done = useSample ? sample.done : coverage.analysed_rolls;
                const left = useSample ? sample.left : coverage.pending_rolls;
                const total = useSample ? sample.size : coverage.group_rolls.length;
                const toggleAbsent = (r) => setAbsent(prev => prev.includes(r) ? prev.filter(x => x !== r) : [...prev, r]);
                const mode = (on) => ({ flex: 1, minHeight: 40, padding: '5px 4px', borderRadius: 8, border: '1px solid var(--border)', fontSize: '0.7rem', fontWeight: 600,
                                        background: on ? 'var(--green-dark)' : 'var(--surface)', color: on ? 'white' : 'var(--text)' });
                return (
                  <div data-testid="coverage" style={{ fontSize: '0.75rem', background: '#F3F8F4', border: '1px solid #D5E6DA', borderRadius: 8, padding: '6px 10px', marginBottom: 8 }}>
                    {big && (
                      <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                        <button type="button" data-testid="mode-sample" style={mode(useSample)} onClick={() => setSampleMode('sample')}>नमूना<En>Sample</En> {sample.size}/{sample.group_size}</button>
                        <button type="button" data-testid="mode-all" style={mode(!useSample)} onClick={() => setSampleMode('all')}>सभी<En>Everyone</En> {coverage.group_rolls.length}</button>
                      </div>
                    )}
                    <div><b>✓ हो चुके<En>Done</En>: {done.length}/{total}</b>{done.length > 0 && ` · रोल ${done.join(', ')}`}</div>
                    <div style={{ marginTop: 2 }}>
                      ⏳ {useSample ? <>इन बच्चों की फ़ोटो लें<En>Photograph these</En></> : <>बाकी<En>Left</En></>}:{' '}
                      {left.length === 0 ? <>कोई नहीं<En>none</En></> : useSample
                        ? left.map(r => <button key={r} type="button" data-testid={`chip-${r}`} title={[names && names[r], coverage.labels?.[r]].filter(Boolean).join(' · ')} className="chip" onClick={() => toggleAbsent(r)}>{r}{coverage.labels?.[r] ? <span style={{ fontSize: '0.55rem', color: 'var(--text-secondary)' }}> {coverage.labels[r]}</span> : null}</button>)
                        : left.join(', ')}
                    </div>
                    {useSample && left.length > 0 && <div style={{ color: 'var(--text-secondary)' }}><Bi hi="कोई बच्चा अनुपस्थित है? उसके रोल पर दबाएँ, उसकी जगह दूसरा बच्चा सुझाया जाएगा।" en="Absent? Tap the roll and another child is suggested." /></div>}
                    {useSample && sample.absent.length > 0 && (
                      <div style={{ marginTop: 4 }}>अनुपस्थित<En>Absent</En>: {sample.absent.map(r => <button key={r} type="button" data-testid={`absent-${r}`} className="chip" onClick={() => toggleAbsent(r)}>{r} ✕</button>)}</div>
                    )}
                    {useSample && (
                      <div data-testid="sample-note" style={{ color: 'var(--text-secondary)', marginTop: 4 }}>
                        नमूना समूह की मोटी तस्वीर देता है (औसत लगभग ±{sample.margin_points} अंक तक अलग हो सकता है)। स्तर सिर्फ़ आकलन से बदलते हैं, दैनिक नमूने से नहीं।
                        <span className="en" lang="en">A sample gives a rough picture of the group (the average could be off by about ±{sample.margin_points} points). Levels change only through an assessment, never from daily results.</span>
                      </div>
                    )}
                    {!useSample && done.length > 0 && <div style={{ color: 'var(--text-secondary)', marginTop: 2 }}><Bi hi="जो हो चुके हैं उनकी दोबारा फ़ोटो न लें।" en="No need to photograph the done ones again." /></div>}
                  </div>
                );
              })()}
              <div className="capture-area" onClick={() => fileInput.current?.click()}>
                <div className="capture-icon">📷</div>
                <p>वर्कशीट की फ़ोटो लें या चुनें (अधिकतम 6)</p>
                <p className="en" lang="en" style={{ fontSize: '0.75rem' }}>Tap to capture or select (max 6)</p>
                <input ref={fileInput} type="file" accept="image/*" capture="environment"
                  multiple onChange={handlePhotoCapture} style={{ display: 'none' }} />
              </div>
              {dupNotice && <div style={{ fontSize: '0.75rem', color: '#8A5A00', background: '#FFF4D6', borderRadius: 8, padding: '4px 10px', marginTop: 6 }} data-testid="dup-notice">⚠ {dupNotice}</div>}
              <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: 6 }} data-testid="photo-name-hint">
<Bi hi="फ़ोटो में बच्चे का नाम न आने दें। नाम AI को कभी नहीं भेजे जाते, पर फ़ोटो में लिखा नाम चला जाएगा।" en="Keep names out of the photo: names are never sent to the AI, but a name written on the page would be." />
              </p>
              {photos.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {photos.map((p, i) => (
                      <div key={i} style={{ width: 60, height: 60, borderRadius: 8, background: 'var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem' }}>📄 {i + 1}</div>
                    ))}
                  </div>
                  {!online && <div data-testid="photos-offline" style={{ fontSize: '0.75rem', color: '#26405A', background: '#E8EEF4', borderRadius: 8, padding: '6px 10px', marginTop: 8 }}><Bi hi="फ़ोटो भेजने के लिए इंटरनेट चाहिए; चुनी हुई फ़ोटो यहीं रहेंगी।" en="Sending photos needs the internet; the photos you chose stay here." /></div>}
          <button className="btn btn-primary" onClick={() => submitPhotos()} disabled={loading || !online} style={{ marginTop: 8 }}>
                    {loading ? (
                      <><div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> <Bi hi="विश्लेषण हो रहा..." en="Analysing" inline /></>
                    ) : <>🔍 {photos.length} फ़ोटो का विश्लेषण करें<span className="en en-inline" lang="en">Analyse</span></>}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ORF */}
          {channel === 'orf' && (
            <div className="card">
              <h3 style={{ marginBottom: 4 }}>⏱️ <Bi hi="पठन प्रवाह" en="Reading Fluency / ORF" inline /></h3>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
                <Bi hi="एक बच्चे को एक मिनट पढ़ते सुनें, फिर सही शब्द और गलतियाँ दर्ज करें। कोई आवाज़ रिकॉर्ड नहीं होती।" en="Listen to one child read for a minute, then enter the correct words and the errors. No audio is recorded." />
              </p>
              {orfLevel && (
                <div style={{ marginBottom: 8, fontSize: '0.75rem' }} data-testid="orf-chips">
                  <div style={{ marginBottom: 4 }}>कौशल<span className="en en-inline" lang="en">Skill</span>: <b>{orfLevel.competency_id}</b> · {orfLevel.name_hi}</div>
                  {levelsFor('orf').length > 1 && (
                    <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                      {levelsFor('orf').map(l => <button key={l} type="button" className={`tier-option tier-${l} ${sheetLevel === l ? 'selected' : ''}`} onClick={() => setSheetLevel(l)}>{GROUP_LABELS[l].mark} {LEVEL_HI[l]}</button>)}
                    </div>
                  )}
                  {(coverage ? (coverage.sample.mode === 'sample' && sampleMode === 'sample' ? coverage.sample.rolls : coverage.group_rolls) : orfLevel.rolls).map(r => {
                    const done = (coverage?.analysed_rolls || []).includes(r);
                    return <button key={r} type="button" className="chip" data-testid={`orf-chip-${r}`} onClick={() => setOrfEntry(o => ({ ...o, roll_number: String(r) }))}
                      style={{ background: String(orfEntry.roll_number) === String(r) ? 'var(--green-dark)' : done ? '#E4F4EA' : 'white', color: String(orfEntry.roll_number) === String(r) ? 'white' : 'inherit' }}>{r}{done ? ' ✓' : ''}</button>;
                  })}
                </div>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <input type="number" inputMode="numeric" placeholder="रोल नं." aria-label="रोल नंबर (Roll number)" value={orfEntry.roll_number}
                  onChange={e => setOrfEntry(o => ({ ...o, roll_number: e.target.value }))}
                  style={{ padding: 10, borderRadius: 8, border: '1px solid var(--border)', fontSize: '1rem', fontFamily: 'inherit' }} />
                <input type="number" inputMode="numeric" placeholder={bi('सही शब्द/मिनट', 'CWPM')} aria-label="सही शब्द प्रति मिनट (Correct Words Per Minute)" value={orfEntry.cwpm}
                  onChange={e => setOrfEntry(o => ({ ...o, cwpm: e.target.value }))}
                  style={{ padding: 10, borderRadius: 8, border: '1px solid var(--border)', fontSize: '1rem', fontFamily: 'inherit' }} />
                <input type="number" inputMode="numeric" placeholder={bi('गलतियाँ', 'Errors')} aria-label="गलतियाँ (Errors)" value={orfEntry.error_count}
                  onChange={e => setOrfEntry(o => ({ ...o, error_count: e.target.value }))}
                  style={{ padding: 10, borderRadius: 8, border: '1px solid var(--border)', fontSize: '1rem', fontFamily: 'inherit' }} />
              </div>
              <button className="btn btn-primary" onClick={submitORF}
                disabled={loading || !orfEntry.roll_number || !orfEntry.cwpm} style={{ marginTop: 10 }}>
                {loading ? 'दर्ज हो रहा...' : <>⏱️ पठन दर्ज करें<En>Save reading score</En></>}
              </button>
            </div>
          )}

          {!channel && (
            <div className="empty-state">
              <p><Bi hi="ऊपर से साक्ष्य का तरीका चुनें" en="Select evidence channel above" /></p>
            </div>
          )}

          <button className="btn btn-secondary" onClick={() => setStep(3)} style={{ marginTop: 12 }}>
            <Bi hi="विश्लेषण देखें" en="View Analysis" inline /> →
          </button>
        </>
      )}

      {/* STEP 3: AI Analysis */}
      {step === 3 && (
        <>
          <h2 style={{ marginBottom: 12 }}>🔍 <Bi hi="AI विश्लेषण" en="AI Analysis" inline /></h2>

          {analysisResult ? (
            <>
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span><Bi hi="विश्लेषित बच्चे" en="Children analysed" /></span>
                  <strong>{analysisResult.children_analysed}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span><Bi hi="समूह शुद्धता" en="Group accuracy" /></span>
                  <strong>{Math.round(analysisResult.group_accuracy * 100)}%</strong>
                </div>
                {analysisResult.copy_errors_excluded > 0 && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 8 }}>
                    ✏️ {analysisResult.copy_errors_excluded} सवाल गिने नहीं गए: बच्चों ने उन्हें अलग उतारा<En>problems not scored: copied differently</En>
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span><Bi hi="AI सुझाव" en="AI recommendation" /></span>
                  <strong style={{ color: analysisResult.ai_recommendation === 'advance' ? 'var(--proficient-ink)' : 'var(--reteach)', textAlign: 'right' }}>
                    {analysisResult.ai_recommendation === 'advance' ? <Bi hi="▲ आगे बढ़ें" en="Advance" /> : <Bi hi="🔄 दोहराएँ" en="Re-teach" />}
                  </strong>
                </div>
              </div>

              {analysisResult.skipped_duplicates?.length > 0 && (
                <div className="card" style={{ borderLeft: '4px solid #D9A400', background: '#FFF8E1' }} data-testid="dup-skipped">
                  <h3 style={{ marginBottom: 4 }}>⚠️ <Bi hi="पहले से विश्लेषित" en="Already analysed today" inline /></h3>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 6 }}><Bi hi="इनका पहले का परिणाम रखा गया" en="the earlier result was kept" inline /></p>
                  {analysisResult.skipped_duplicates.map(d => (
                    <div key={d.roll_number} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', fontSize: '0.8125rem' }}>
                      <span>रोल {d.roll_number} ·{d.earlier_accuracy == null ? '—' : Math.round(d.earlier_accuracy * 100) + '%'} · {new Date(d.earlier_at).toLocaleTimeString('hi-IN', { hour: '2-digit', minute: '2-digit' })}</span>
                      {photos.length > 0 && <button type="button" className="btn btn-secondary btn-small" style={{ fontSize: '0.8125rem' }} disabled={loading || !online}
                        onClick={() => submitPhotos({ replaceRolls: [d.roll_number] })}>नई फ़ोटो से बदलें<En>Replace</En></button>}
                    </div>
                  ))}
                </div>
              )}
              {(analysisResult.duplicates_in_batch?.length > 0 || analysisResult.unknown_rolls?.length > 0 || analysisResult.outside_group_rolls?.length > 0 ||
                analysisResult.unreadable_sheets > 0 || analysisResult.not_assessed?.length > 0) && (
                <div className="card" style={{ background: '#FFF8E1', fontSize: '0.8125rem' }} data-testid="roll-notices">
                  {analysisResult.duplicates_in_batch?.length > 0 && <div>🔁 एक ही बच्चे की दो फ़ोटो, साफ़ वाली इस्तेमाल हुई<En>Two photos of the same child, the clearer one was used</En>: रोल {analysisResult.duplicates_in_batch.join(', ')}</div>}
                  {analysisResult.unknown_rolls?.length > 0 && <div>❓ ये रोल नंबर इस कक्षा में नहीं हैं, गिने नहीं गए<En>Not in this class, not counted</En>: {analysisResult.unknown_rolls.join(', ')}</div>}
                  {analysisResult.outside_group_rolls?.length > 0 && <div>↔️ दूसरे समूह की शीट<En>A sheet from another group</En>: रोल {analysisResult.outside_group_rolls.join(', ')}</div>}
                  {analysisResult.unreadable_sheets > 0 && <div>🔍 {analysisResult.unreadable_sheets} शीट का रोल नंबर पढ़ा नहीं गया, दोबारा फ़ोटो लें<En>Roll number unreadable, please retake</En></div>}
                  {analysisResult.not_assessed?.length > 0 && <div>📝 कुछ आँका नहीं जा सका<En>Nothing could be scored</En>: रोल {analysisResult.not_assessed.join(', ')}</div>}
                </div>
              )}

              {analysisResult.discrepancy && (
                <div className="card" style={{ borderLeft: '4px solid var(--beginner)', background: 'var(--beginner-bg)' }}>
                  <h3 style={{ color: 'var(--beginner-ink)', marginBottom: 4 }}>⚠️ <Bi hi="विसंगति" en="Discrepancy" inline /></h3>
                  <p style={{ fontSize: '0.875rem' }}>{analysisResult.discrepancy.reason}</p>
                </div>
              )}

              {analysisResult.misconceptions_detected?.length > 0 && (
                <div className="card">
                  <h3 style={{ marginBottom: 8 }}><Bi hi="पाई गई गलतियाँ" en="Misconceptions Detected" inline /></h3>
                  {analysisResult.misconceptions_detected.map(m => (
                    <div key={m.id} style={{ padding: '6px 0', borderBottom: '1px solid var(--border)', fontSize: '0.875rem' }}>
                      <strong>{m.id}</strong> — {m.total_occurrences} बार<En>occurrences</En>
                    </div>
                  ))}
                </div>
              )}

              {analysisResult.per_child?.map(c => (
                <div key={c.roll_number} className="card" style={{ padding: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <strong>रोल {c.roll_number}</strong>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      {/* the result of THIS check, in words: one day on a sample says nothing about mastery of the skill */}
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }} data-testid="today-result">
                        आज की जाँच में: {c.status === 'achieved' ? 'प्राप्त' : c.status === 'partially_achieved' ? 'आंशिक' : c.status === 'not_assessed' ? 'आँका नहीं गया' : 'प्राप्त नहीं'}
                      </span>
                      {/* a neutral badge with a symbol: a tier colour here would make "NA" look like the Beginner group */}
                      <span className="badge badge-result">
                        {c.status === 'achieved' ? '✓ A' : c.status === 'partially_achieved' ? '~ PA' : c.status === 'not_assessed' ? '—' : '✗ NA'}
                      </span>
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {c.accuracy == null
                      ? <>आँका नहीं गया<En>Not assessed</En></>
                      : <>शुद्धता<En>Accuracy</En>: {Math.round(c.accuracy * 100)}%{c.assessed_problems ? <> · {c.assessed_problems} सवालों में से<En>of {c.assessed_problems}</En></> : null}</>}
                    {c.misconceptions?.length > 0 && <> · गलती<En>Error</En>: {c.misconceptions.join(', ')}</>}
                  </div>
                  {c.copy_errors?.length > 0 && (
                    <div style={{ fontSize: '0.75rem', color: '#8A5A00', marginTop: 4 }} data-testid="copy-errors">
                      ✏️ अलग उतारा, गिना नहीं गया<En>Copied differently, not scored</En>:{' '}
                      {c.copy_errors.map(e => `#${e.problem}${e.written ? ` लिखा ${e.written}` : ''} → ${e.answer}${e.correct_for_written === true ? ' ✓ (उस सवाल के लिए सही)' : e.correct_for_written === false ? ' ✗' : ''}`).join(' · ')}
                    </div>
                  )}
                  {c.needs_check?.length > 0 && (
                    <div style={{ fontSize: '0.75rem', color: '#555', marginTop: 4 }} data-testid="needs-check">
                      👀 नोटबुक में जाँचें<En>Check in the notebook</En>: सवाल {c.needs_check.join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <p>फ़ोटो विश्लेषण के बाद परिणाम यहाँ दिखेंगे</p>
              <p className="en" lang="en" style={{ fontSize: '0.8rem', marginTop: 4 }}>Results will appear after photo analysis</p>
            </div>
          )}

          <button className="btn btn-secondary" onClick={() => { setStep(1); setDecisions({}); setPhotos([]); setAnalysisResult(null); setChannel(null); }}
            style={{ marginTop: 16, marginBottom: 80 }}>
            ← <Bi hi="नई समीक्षा शुरू करें" en="Start new review" inline />
          </button>
        </>
      )}
    </div>
  );
}
