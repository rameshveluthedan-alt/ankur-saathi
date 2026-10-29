import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../App';
import { recordDecisions, recordObserved, recordORF, analysePhotos, getSavedAnalyses, getReviewCoverage, getReviewChannels, getCachedPlan } from '../services/api';
import { placeKey, loadPlace, savePlace } from '../services/reviewPlace';
import { compressImage } from '../utils/imageCompress';
import { useOnline } from '../components/OfflineBanner';
import { GROUP_LABELS, GROUP_ORDER } from '../tiers';
import Bi from '../components/Bi';
import { bi } from '../services/language';
import { notify } from '../services/notify';
import { friendlyError } from '../services/errors';
import { localToday } from '../services/today';
import { useNavigate } from 'react-router-dom';
import { ObservedSaved, ReadingSaved, SaveError } from '../components/ReviewConfirm';
import { DECISION_TEXT } from '../components/ProgressToday';
import { CHANNELS, channelOf, PRACTICE_ONLY, hasWorksheet } from '../services/reviewWays';
import SkillLine from '../components/SkillLine';
import FluencyLine from '../components/FluencyLine';
import { RESULT_MARK } from '../components/ProgressToday';
import { isFluencySkill } from '../services/pace';
import Hint from '../components/Hint';

// an English translation on the same line, after its Hindi (hidden by the "Hindi only" setting)
const SAVE_FAILED = { hi: 'सहेजा नहीं जा सका', en: 'Could not save' };
const OBS_CODE = { achieved: 'A', partially_achieved: 'PA', not_achieved: 'NA' };

const En = ({ children }) => <span className="en en-inline" lang="en">{children}</span>;

// Each step's heading says where the teacher is: "1/3 · आज हर समूह कैसा रहा?", "2/3 · बच्चों का काम देखें", "3/3 · अंतिम निर्णय". One set of words: the heading is the step
// (there is no separate step marker). The ways between steps are buttons where her thumb is.
export function StepTitle({ n, hi, en, icon }) {
  return (
    <h2 data-testid="review-title" data-step={n} style={{ marginBottom: 4 }}>
      <span className="step-count">{n}/3</span> {icon ? `${icon} ` : ''}<Bi hi={hi} en={en} inline />
    </h2>
  );
}

export default function ReviewScreen() {
  const { teacher, currentPlan, setCurrentPlan, selectedDomain, names } = useAuth();
  // The review in three steps: 1 the teacher's FIRST judgment per group (before the evidence, so it is not anchored by the AI's reading), 2 the children's
  // work (observation, reading aloud or worksheet photos; a photo analysis opens inside this step), 3 the FINAL decision per group, with her first judgment and
  // today's evidence in front of her. The final decision is what tomorrow's plan suggests from (the first judgment is kept too).
  // Where the teacher was (services/reviewPlace.js): leaving for Progress or another tab and coming back lands in the same place.
  const place = placeKey(teacher.teacher_id, localToday(), selectedDomain);
  const [restored] = useState(() => loadPlace(place));
  const [step, setStep] = useState(() => (restored && restored.step) || 1);
  const [analysisOpen, setAnalysisOpen] = useState(false);       // step 2: a photo analysis on screen instead of the ways of checking
  const [planInfo, setPlanInfo] = useState(null);                 // the server's plan reply: first judgments, final decisions, today's evidence per group
  const [finals, setFinals] = useState({});                       // step 3: the final decision chosen per group
  const [finalDone, setFinalDone] = useState(false);              // step 3: the final decisions were recorded
  const [decisions, setDecisions] = useState(() => (restored && restored.decisions) || {});
  const [channel, setChannel] = useState(() => (restored && restored.channel) || null);
  const [photos, setPhotos] = useState([]);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [sheetLevel, setSheetLevel] = useState(() => (restored && restored.sheetLevel) || 'progressor');   // which group's worksheet the photos are of
  const goStep = (n) => setStep(n);
  const touched = useRef(false);                     // the teacher has changed a decision on this screen: the server's copy never overwrites it
  const [loading, setLoading] = useState(false);
  const online = useOnline();            // sending photos for analysis needs the internet (they go to the AI); the chosen photos stay on the screen
  const [observedItems, setObservedItems] = useState([]);
  const [orfEntry, setOrfEntry] = useState({ roll_number: '', cwpm: '', error_count: '' });
  const fileInput = useRef(null);
  const navigate = useNavigate();
  // what the last save recorded, shown above the list (Observed) or the form (Reading aloud); a failed save shows its error in place instead
  const [observedSaved, setObservedSaved] = useState(null);     // { level, items }
  const [observedError, setObservedError] = useState('');
  const [orfSaved, setOrfSaved] = useState(null);               // { level, result }: the server's answer
  const [orfError, setOrfError] = useState('');

  const today = localToday();
  // today's plan in this subject: the one in memory if it is that, else loaded here (after the app is reopened, the plan is not in memory)
  const isToday = (p) => !!p && p.domain_id === selectedDomain && p.plan_date === today;
  const plan = isToday(currentPlan) ? currentPlan : null;
  const [planStatus, setPlanStatus] = useState(plan ? 'ready' : 'loading');     // 'ready' | 'loading' | 'none' (no plan today) | 'error'
  useEffect(() => {
    let cancelled = false;
    getCachedPlan(teacher.teacher_id, today, selectedDomain).then((reply) => {
      if (cancelled) return;
      if (!isToday(currentPlan)) setCurrentPlan(reply);
      setPlanStatus('ready');
      setPlanInfo(reply);
      // what was already recorded today: the first judgments (older records have only "decisions") and the final decisions.
      // Every group decided finally: the review opens at step 3; every group judged first: at step 2 (unless the teacher's own place says otherwise)
      const first = { ...(reply.decisions || {}), ...(reply.first_judgments || {}) };
      const fin = reply.final_decisions || {};
      const needed = (reply.groups || []).filter((g) => g.count > 0);
      const all = (d) => needed.length > 0 && needed.every((g) => d[g.label]);
      setFinals((prev) => ({ ...fin, ...prev }));
      if (all(fin)) setFinalDone(true);
      if (touched.current) return;
      if (!restored && all(fin)) { setDecisions(first); goStep(3); }
      else if (!restored && all(first)) { setDecisions(first); goStep(2); }
      else setDecisions((prev) => ({ ...first, ...prev }));
    }).catch((e) => { if (!cancelled) setPlanStatus(isToday(currentPlan) ? 'ready' : (e && e.status === 404 ? 'none' : 'error')); });
    return () => { cancelled = true; };
  }, [teacher.teacher_id, selectedDomain]);
  useEffect(() => { savePlace(place, { step, decisions, channel, sheetLevel }); }, [place, step, decisions, channel, sheetLevel]);
  const groups = plan?.groups || [];
  // step 1 is complete when every group with children has a decision: until then "record" is off, and the screen says which groups are left
  const undecided = groups.filter((g) => g.count > 0 && !decisions[g.label]);
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
  const openSaved = (a) => { setAnalysisResult(a.result); setSheetLevel(a.worksheet_level); goStep(2); setAnalysisOpen(true); };
  // step 3: today's evidence fetched again (the children's work may have changed it), and each group's choice starts on her final decision if one
  // was recorded, else on her first judgment
  const enterFinal = async () => {
    setAnalysisOpen(false); goStep(3);
    try {
      const reply = await getCachedPlan(teacher.teacher_id, today, selectedDomain);
      setPlanInfo(reply);
      setFinals((prev) => { const out = { ...prev }; groups.forEach((g) => { if (!out[g.label]) out[g.label] = (reply.final_decisions || {})[g.label] || decisions[g.label] || null; }); return out; });
    } catch { setFinals((prev) => { const out = { ...prev }; groups.forEach((g) => { if (!out[g.label]) out[g.label] = decisions[g.label] || null; }); return out; }); }
  };

  // to Progress from a save's pointer: Progress shows "← समीक्षा पर लौटें", and the review is where it was (reviewPlace)
  const toProgress = () => navigate('/progress', { state: { from: 'review' } });

  const handleDecision = (groupLabel, decision) => {
    touched.current = true;
    setDecisions(d => ({ ...d, [groupLabel]: d[groupLabel] === decision ? null : decision }));
  };

  const submitDecisions = async () => {
    setLoading(true);
    try {
      await recordDecisions(teacher.teacher_id, today, selectedDomain, decisions, 'first');
      goStep(2);
    } catch (e) { notify(friendlyError(e, { hi: 'निर्णय दर्ज नहीं हो सके', en: 'The decisions could not be recorded' }), 'error'); }
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
    if (!photos.length || !plan) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('teacher_id', teacher.teacher_id);
      fd.append('session_date', today);
      fd.append('domain_id', selectedDomain);
      fd.append('competency_id', plan.selected_competency_id);
      fd.append('worksheet_level', sheetLevel);
      fd.append('teacher_pre_judgment', decisions[sheetLevel] || '');
      fd.append('on_duplicate', 'skip');                       // a child already analysed today keeps the earlier result
      if (opts.replaceRolls && opts.replaceRolls.length) fd.append('replace_rolls', opts.replaceRolls.join(','));
      photos.forEach(p => fd.append('photos', p));
      const result = await analysePhotos(teacher.teacher_id, fd);
      setAnalysisResult(result);
      setAnalysisOpen(true);
      refreshSaved();
      refreshCoverage();
    } catch (e) { notify(friendlyError(e, { hi: 'फ़ोटो का विश्लेषण नहीं हो सका', en: 'The photos could not be analysed' }, { 400: { hi: 'फ़ोटो पढ़ी नहीं जा सकी। वर्कशीट की साफ़ फ़ोटो चुनें।', en: "The photo couldn't be read. Choose a clear photo of the worksheet." } }), 'error'); }
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
      const res = await recordObserved(teacher.teacher_id, today, observedItems);
      setObservedSaved({ level: sheetLevel, items: observedItems, result: res }); setObservedError('');    // exactly the children of this save, and what the server did with each
      setObservedItems([]);
      refreshCoverage();
    } catch (e) { setObservedSaved(null); setObservedError(friendlyError(e, SAVE_FAILED)); }
    setLoading(false);
  };

  const submitORF = async () => {
    if (!orfEntry.roll_number || !orfEntry.cwpm) return;
    setLoading(true);
    try {
      const result = await recordORF(teacher.teacher_id, {
        session_date: today, roll_number: parseInt(orfEntry.roll_number),
        passage_id: (orfLevel && orfLevel.passage && orfLevel.passage.id) || null,       // the text the screen showed; none when it showed none (never a made-up id)
        cwpm: parseInt(orfEntry.cwpm),
        error_count: parseInt(orfEntry.error_count || 0),
        competency_id: orfLevel?.competency_id,        // the skill on today's plan (before, the server always read the score against L2.5.1)
      });
      setOrfSaved({ level: sheetLevel, skill: orfLevel?.competency_id, result,                 // the server's own result, never worked out here,
                    entry: { cwpm: parseInt(orfEntry.cwpm), errors: parseInt(orfEntry.error_count || 0) } });   // and the two numbers the teacher entered
      setOrfError('');
      setOrfEntry({ roll_number: '', cwpm: '', error_count: '' });
      refreshCoverage();
    } catch (e) { setOrfSaved(null); setOrfError(friendlyError(e, SAVE_FAILED, { 404: { hi: 'यह रोल नंबर इस कक्षा में नहीं है।', en: "This roll number isn't in this class." } })); }
    setLoading(false);
  };

  return (
    <div className="screen">
      <div className="screen-header">
        <h1>☑️ <Bi hi="समीक्षा" en="Review" inline /></h1>
      </div>

      {/* no plan for today in this subject (or it could not be loaded): say so, and the way to make one */}
      {!plan && (planStatus === 'loading' ? (
        <div className="loading" data-testid="review-loading"><div className="spinner" /><span><Bi hi="आज की योजना खोली जा रही है…" en="Opening today's plan" inline /></span></div>
      ) : (
        <div className="card" data-testid="review-no-plan" style={{ textAlign: 'center' }}>
          {planStatus === 'none'
            ? <Bi hi="आज इस विषय की योजना नहीं बनी है। पहले योजना बनाएँ; पढ़ाने के बाद यहाँ समीक्षा करें।" en="No plan for this subject today. Make a plan first; review here after teaching." />
            : <Bi hi="आज की योजना खुल नहीं सकी। इंटरनेट जाँचकर फिर कोशिश करें।" en="Today's plan could not be opened. Check the internet and try again." />}
          <button type="button" className="btn btn-primary" data-testid="review-make-plan" onClick={() => navigate('/')} style={{ marginTop: 10, flexDirection: 'column', gap: 0 }}>
            <Bi hi="योजना बनाएँ →" en="Make a plan" />
          </button>
        </div>
      ))}

      {plan && (<>

      {/* An analysis already done today can always be reopened, even after pressing Back or reloading */}
      {step !== 3 && !analysisOpen && savedAnalyses.length > 0 && (
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
          <StepTitle n={1} hi="आज हर समूह कैसा रहा?" en="How did each group do today?" />
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: 16 }} data-testid="first-intro">
            बच्चों का काम देखने से पहले, आपका <b data-testid="first-term">पहला अनुमान</b>। अंतिम निर्णय तीसरे चरण में, आज की जाँच देखकर।
            <span className="en" lang="en">Your <b>first judgment</b>, before looking at the children's work. The final decision comes in step 3, with today's evidence.</span>
          </p>
          {/* what each choice does to the next plan, one tap away */}
          <Hint testid="hint-decisions">
            <Bi hi="⬆ आगे बढ़ें: अगली योजना में अगला कौशल। 🔄 दोहराएँ या ❓ पक्का नहीं: अगली योजना में वही कौशल, दोबारा समझाकर। यह पहला अनुमान है; अंतिम निर्णय तीसरे चरण में, आज की जाँच देखकर।"
              en="Advance: the next plan moves to the next skill. Re-teach or Not sure: the next plan keeps the same skill and teaches it again. This is a first judgment; the final decision comes in step 3, with today's evidence." />
          </Hint>

          {groups.map(g => (
            <div key={g.label} className={`card tier-card tier-${g.label}`}>
              <div className="card-header">
                <div>
                  <span className={`badge badge-${g.label}`}>{GROUP_LABELS[g.label]?.hi}</span>
                  <span className="en en-inline" lang="en">{GROUP_LABELS[g.label]?.en}</span>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{g.count} बच्चे</span>
              </div>
              <SkillLine level={g.label} skillId={g.target_competency_id} name={g.target_competency_name_hi} withGroup={false} testid={`skill-1-${g.label}`} />
              <div className="decision-row">
                <button className={`decision-btn advance ${decisions[g.label] === 'advance' ? 'selected' : ''}`}
                  onClick={() => handleDecision(g.label, 'advance')}>
                  <Bi hi="⬆ आगे बढ़ें" en="Advance" />
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

          {undecided.length > 0 && (
            <p data-testid="decisions-left" style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '8px 0 0' }}>
              <Bi hi={`हर समूह के लिए एक विकल्प चुनें (बाकी: ${undecided.map((g) => `${GROUP_LABELS[g.label]?.mark || ''} ${GROUP_LABELS[g.label]?.hi || g.label}`.trim()).join(', ')})`}
                en={`Choose an option for each group (left: ${undecided.map((g) => GROUP_LABELS[g.label]?.en || g.label).join(', ')})`} />
            </p>
          )}
          <button className="btn btn-primary" data-testid="record-decisions" onClick={submitDecisions} disabled={loading || undecided.length > 0} style={{ marginTop: 8, flexDirection: 'column', gap: 0 }}>
            {loading ? <Bi hi="दर्ज हो रहा..." en="Recording" /> : <Bi hi="दर्ज करें → बच्चों का काम देखें" en="Record → Look at the children's work" />}
          </button>
        </>
      )}

      {/* STEP 2: Evidence capture */}
      {step === 2 && !analysisOpen && (
        <>
          <button type="button" className="btn btn-secondary btn-small" data-testid="back-to-decisions" onClick={() => setStep(1)} style={{ marginBottom: 8 }}>
            ← <span className="step-count">1/3</span> <Bi hi="पहला अनुमान बदलें" en="Change the first judgment" inline />
          </button>
          <StepTitle n={2} hi="बच्चों का काम देखें" en="Look at the children's work" />
          <div style={{ marginBottom: 8 }} />

          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            {CHANNELS.filter(ch => visibleChannels.includes(ch.id)).map(ch => (
              <button key={ch.id} className={`domain-tab ${channel === ch.id ? 'active' : ''}`} data-testid={`channel-${ch.id}`}
                onClick={() => setChannel(ch.id)}>
                {ch.icon} <Bi hi={ch.hi} en={ch.en} />
                {channelsInfo?.has_plan && channelsInfo.channels[ch.id] && <div style={{ fontSize: '0.55rem', fontWeight: 400 }}>{channelsInfo.channels[ch.id].map(l => LEVEL_HI[l]).join(', ')}</div>}
              </button>
            ))}
          </div>
          {/* who does what, for the way chosen (the photo way is read by the AI) */}
          {CHANNELS.find((ch) => ch.id === channel) && (
            <p data-testid="channel-who" style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '-8px 0 12px' }}>
              <Bi hi={CHANNELS.find((ch) => ch.id === channel).who.hi} en={CHANNELS.find((ch) => ch.id === channel).who.en} />
            </p>
          )}
          {channelOf(channel) && (
            <details className="fold" data-testid={`how-${channel}`} style={{ margin: '-6px 0 12px' }}>
              <summary><span><Bi hi="कैसे करें?" en="How to do it" inline /></span></summary>
              {channel === 'observed' && observedLevel && hasWorksheet(plan, observedLevel.level) && (
                <p data-testid="worksheet-practice" style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#8A5A00', margin: '2px 0 4px' }}><Bi hi={PRACTICE_ONLY.hi} en={PRACTICE_ONLY.en} inline /></p>
              )}
              <ol data-testid="how-steps" style={{ margin: '2px 0 4px', paddingLeft: 20, fontSize: '0.8125rem' }}>
                {channelOf(channel).how.map((st, i) => <li key={i} style={{ marginBottom: 2 }}><Bi hi={st.hi} en={st.en} inline /></li>)}
              </ol>
            </details>
          )}
          {/* today's skills need only some of the three ways: why, which groups, and the other ways if the teacher wants them */}
          {channelsInfo?.has_plan && relevantChannels.length < 3 && (
            <Hint testid="hint-why-way" label={<Bi hi="यही तरीका क्यों?" en="Why this way?" inline />}>
              {CHANNELS.filter((ch) => relevantChannels.includes(ch.id)).map((ch) => (
                <div key={ch.id} data-testid={`why-${ch.id}`} style={{ marginBottom: 6 }}>
                  <b>{ch.icon} {ch.hi}</b>: <Bi hi={ch.why.hi} en={ch.why.en} inline />
                  <div style={{ fontSize: '0.75rem' }}>
                    <Bi hi="आज" en="Today" inline />: {(channelsInfo.levels || []).filter((l) => l.channel === ch.id).map((l) => `${GROUP_LABELS[l.level]?.mark || ''} ${LEVEL_HI[l.level] || l.level} ${l.competency_id}`).join(' · ')}
                  </div>
                </div>
              ))}
              <button type="button" data-testid="channel-toggle" onClick={() => setShowAllChannels(v => !v)}
                style={{ background: 'none', border: 'none', color: 'var(--green-dark)', textDecoration: 'underline', fontSize: '0.8125rem', padding: '4px 0', minHeight: 36, cursor: 'pointer', fontFamily: 'inherit' }}>
                {showAllChannels ? <Bi hi="सिर्फ़ ज़रूरी तरीके दिखाएँ" en="Show only the ways needed" inline /> : <Bi hi="दूसरे तरीके भी दिखाएँ" en="Show the other ways too" inline />}
              </button>
            </Hint>
          )}

          {/* Observed: the group's children as a checklist (the skill is filled in from today's plan) */}
          {channel === 'observed' && observedLevel && (() => {
            const sample = coverage?.sample;
            const big = coverage && coverage.group_rolls.length > 8 && sample;
            const useSample = big && sampleMode === 'sample';
            const rolls = coverage ? (useSample ? sample.rolls : coverage.group_rolls) : observedLevel.rolls;
            const saved = new Set(coverage?.analysed_rolls || []);
            // a tap not yet submitted, and what is already recorded today for the child (from the server: right after a save, after coming back, on another phone)
            const statusOf = (r) => (observedItems.find(i => i.roll_number === r && i.competency_id === observedLevel.competency_id) || {}).status;
            const recordedOf = (r) => ((coverage?.recorded || {})[String(r)] || {}).status;
            const shown = (r) => statusOf(r) || recordedOf(r);
            const unTap = (r) => setObservedItems(prev => prev.filter(i => !(i.roll_number === r && i.competency_id === observedLevel.competency_id)));
            // tapping the recorded choice again (or the pending one) is no change: nothing to submit for that child
            const tap = (r, s) => (statusOf(r) === s || recordedOf(r) === s ? unTap(r) : addObservedItem(r, observedLevel.competency_id, s));
            const btn = (on, color, changing) => ({ minWidth: 52, minHeight: 44, padding: '5px 4px', borderRadius: 8, border: `1px solid ${color}`, fontSize: '0.75rem', fontWeight: 600, background: on ? color : 'white', color: on ? 'white' : color,
                                                    outline: changing ? '3px dashed #C9A227' : 'none', outlineOffset: 1 });
            const isChange = (r) => !!(statusOf(r) && recordedOf(r));
            const newCount = observedItems.filter(i => !recordedOf(i.roll_number)).length;
            const changeCount = observedItems.length - newCount;
            const mode = (on) => ({ flex: 1, minHeight: 40, padding: '5px 4px', borderRadius: 8, border: '1px solid var(--border)', fontSize: '0.75rem', fontWeight: 600, background: on ? 'var(--green-dark)' : 'var(--surface)', color: on ? 'white' : 'var(--text)' });
            return (
              <div className="card" data-testid="observed-list">
                {levelsFor('observed').length > 1 && (
                  <div style={{ display: 'flex', gap: 6, margin: '6px 0' }}>
                    {levelsFor('observed').map(l => <button key={l} type="button" className={`tier-option tier-${l} ${sheetLevel === l ? 'selected' : ''}`} onClick={() => setSheetLevel(l)}>{GROUP_LABELS[l].mark} {LEVEL_HI[l]}</button>)}
                  </div>
                )}
                <SkillLine level={observedLevel.level} skillId={observedLevel.competency_id} name={observedLevel.name_hi} testid="skill-2" />
                {big && (
                  <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                    <button type="button" data-testid="obs-mode-sample" style={mode(useSample)} onClick={() => setSampleMode('sample')}>नमूना<En>Sample</En> {sample.size}/{sample.group_size}</button>
                    <button type="button" style={mode(!useSample)} onClick={() => setSampleMode('all')}>सभी<En>Everyone</En> {coverage.group_rolls.length}</button>
                  </div>
                )}
                {/* what the last save recorded; the list below stays usable (retap and submit again) */}
                <ObservedSaved saved={observedSaved} onOpenProgress={toProgress} />
                <SaveError message={observedError} testid="observed-error" />
                {rolls.map(r => (
                  <div key={r} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                    <b style={{ width: 78, fontSize: '0.8125rem' }}>रोल {r}{names && names[r] && <div style={{ fontSize: '0.7rem', fontWeight: 500 }} data-testid={`name-${r}`}>{names[r]}</div>}{coverage?.labels?.[r] && <div style={{ fontSize: '0.55rem', fontWeight: 400, color: 'var(--text-secondary)' }}>{coverage.labels[r]}</div>}</b>
                    {[['achieved', 'A', 'var(--proficient-ink)'], ['partially_achieved', 'PA', 'var(--progressor-ink)'], ['not_achieved', 'NA', 'var(--beginner-ink)']].map(([st, code, color]) => (
                      <button key={st} type="button" data-testid={`obs-${r}-${st}`} aria-pressed={shown(r) === st} data-state={statusOf(r) === st ? (isChange(r) ? 'changing' : 'new') : (!statusOf(r) && recordedOf(r) === st ? 'recorded' : 'off')}
                        style={btn(shown(r) === st, color, isChange(r) && statusOf(r) === st)} onClick={() => tap(r, st)}>{code}</button>
                    ))}
                    {isChange(r)
                      ? <span data-testid={`obs-change-${r}`} style={{ fontSize: '0.7rem', fontWeight: 700, color: '#8A5A00' }}>{OBS_CODE[recordedOf(r)]} → {OBS_CODE[statusOf(r)]}</span>
                      : recordedOf(r) && <span data-testid={`obs-recorded-${r}`} style={{ fontSize: '0.7rem', color: 'var(--proficient)' }}>✓ दर्ज<En>recorded</En></span>}
                    {useSample && !saved.has(r) && <button type="button" data-testid={`obs-absent-${r}`} style={{ marginLeft: 'auto', minHeight: 44, padding: '0 6px', background: 'none', border: 'none', fontSize: '0.75rem', color: 'var(--text-secondary)', textDecoration: 'underline', fontFamily: 'inherit' }}
                      onClick={() => setAbsent(prev => [...prev, r])}>अनुपस्थित</button>}
                  </div>
                ))}
                {useSample && <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 6 }} data-testid="sample-note-obs">नमूना मोटी तस्वीर देता है (लगभग ±{sample.margin_points} अंक)।<span className="en" lang="en">A sample gives a rough picture of the group.</span></p>}
                <button className="btn btn-primary" onClick={submitObserved} disabled={loading || !observedItems.length} style={{ marginTop: 8 }} data-testid="obs-submit">
                  {loading ? 'दर्ज हो रहा...' : <>✓ जमा करें{observedItems.length > 0 && <> · {[newCount && `${newCount} ${newCount === 1 ? 'नया' : 'नए'}`, changeCount && `${changeCount} बदलाव`].filter(Boolean).join(', ')}</>}
                    <En>Submit{observedItems.length > 0 ? ` · ${[newCount && `${newCount} new`, changeCount && `${changeCount} ${changeCount === 1 ? 'change' : 'changes'}`].filter(Boolean).join(', ')}` : ''}</En></>}
                </button>
              </div>
            );
          })()}
          {/* Observed: the manual form, used only when today's plan is not available */}
          {channel === 'observed' && !observedLevel && (
            <div className="card">
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
                <Bi hi="हर बच्चे के लिए A / PA / NA दबाएँ" en="Tap A / PA / NA for each child" />
              </p>
              {/* what the last save recorded; the list below stays usable (retap and submit again) */}
              <ObservedSaved saved={observedSaved} onOpenProgress={toProgress} />
              <SaveError message={observedError} testid="observed-error" />
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
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '4px 0' }}>किस समूह की वर्कशीट?<span className="en en-inline" lang="en">Which group's sheet?</span></div>
              <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                {GROUP_ORDER.filter((id) => levelsFor('photo').includes(id)).map((id) => (
                  <button key={id} type="button" onClick={() => setSheetLevel(id)} className={`tier-option tier-${id} ${sheetLevel === id ? 'selected' : ''}`}>
                    {GROUP_LABELS[id].mark} <Bi hi={GROUP_LABELS[id].hi} en={GROUP_LABELS[id].en} />
                  </button>
                ))}
              </div>
              {(() => { const g = groups.find((x) => x.label === sheetLevel) || {}; return <SkillLine level={sheetLevel} skillId={g.target_competency_id} name={g.target_competency_name_hi} testid="skill-2" />; })()}
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
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
                <Bi hi="एक बच्चे को एक मिनट पढ़ते सुनें, फिर सही शब्द और गलतियाँ दर्ज करें। कोई आवाज़ रिकॉर्ड नहीं होती।" en="Listen to one child read for a minute, then enter the correct words and the errors. No audio is recorded." />
              </p>
              {orfLevel && (
                <div style={{ marginBottom: 8, fontSize: '0.75rem' }} data-testid="orf-chips">
                  <SkillLine level={orfLevel.level} skillId={orfLevel.competency_id} name={orfLevel.name_hi} testid="skill-2" />
                  {orfLevel.passage ? (
                    <div data-testid="orf-passage" style={{ fontSize: '0.8125rem', marginBottom: 6 }}>
                      <Bi hi="पढ़ने का पाठ" en="Text to read" inline />: <b>«{orfLevel.passage.title}»</b> ({orfLevel.passage.word_count} शब्द<span className="en en-inline" lang="en">words</span>)
                      <details className="fold" data-testid="orf-passage-text" style={{ marginTop: 2 }}>
                        <summary><span><Bi hi="पाठ दिखाएँ (बच्चा यहीं से पढ़ सकता है)" en="Show the text (the child can read it here)" inline /></span></summary>
                        <p lang="hi" style={{ fontSize: '1.125rem', lineHeight: 1.7, whiteSpace: 'pre-line', margin: '4px 0' }}>{orfLevel.passage.text}</p>
                      </details>
                    </div>
                  ) : (
                    <div data-testid="orf-no-passage" style={{ fontSize: '0.75rem', color: '#8A5A00', marginBottom: 6 }}>
                      <Bi hi="इस कौशल का पाठ बैंक में नहीं मिला; अपनी कक्षा के स्तर का कोई ऐसा पाठ लें जो बच्चों ने आज नहीं पढ़ा।" en="No text for this skill in the bank; use a text at your class's level that the children have not read today." inline />
                    </div>
                  )}
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
              {/* the child just scored, and how many in the group are still to score today on this skill (the server's coverage) */}
              <ReadingSaved saved={orfSaved} left={coverage && coverage.pending_rolls ? coverage.pending_rolls.length : 0} onOpenProgress={toProgress} />
              {coverage && coverage.recorded && Object.keys(coverage.recorded).length > 0 && (
                <details className="fold" data-testid="orf-recorded" style={{ margin: '0 0 8px' }}>
                  <summary><span><Bi hi={`आज पढ़ चुके: ${Object.keys(coverage.recorded).length} ${Object.keys(coverage.recorded).length === 1 ? 'बच्चा' : 'बच्चे'}`} en={`Read today: ${Object.keys(coverage.recorded).length} ${Object.keys(coverage.recorded).length === 1 ? 'child' : 'children'}`} inline /></span></summary>
                  {Object.entries(coverage.recorded).sort((a, b) => Number(a[0]) - Number(b[0])).map(([roll, rec]) => (
                    <div key={roll} data-testid={`orf-recorded-${roll}`} style={{ fontSize: '0.8125rem', padding: '3px 0' }}>
                      {rec.cwpm != null && isFluencySkill(orfLevel?.competency_id)
                        ? <FluencyLine roll={Number(roll)} correct={rec.cwpm} errors={rec.errors ?? 0} classification={rec.status} />
                        : <>✓ रोल {roll}{rec.cwpm != null ? `: ${rec.cwpm} CWPM` : ''} · <span className="badge badge-result">{RESULT_MARK[rec.status] || '—'}</span></>}
                    </div>
                  ))}
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                    <Bi hi="गलत दर्ज हुआ हो तो वही रोल नंबर फिर दर्ज करें; नया नतीजा गिना जाएगा।" en="If one was entered wrongly, enter the same roll number again; the newest counts." />
                  </div>
                </details>
              )}
              <SaveError message={orfError} testid="orf-error" />
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

          {(analysisResult || savedAnalyses.length > 0) && (
            <button className="btn btn-secondary" data-testid="see-analysis" onClick={() => (analysisResult ? setAnalysisOpen(true) : openSaved(savedAnalyses[0]))} style={{ marginTop: 12 }}>
              <Bi hi="फ़ोटो विश्लेषण देखें" en="See the photo analysis" inline /> →
            </button>
          )}
          <button type="button" className="btn btn-primary" data-testid="to-final" onClick={enterFinal} style={{ marginTop: 12, marginBottom: 80, flexDirection: 'column', gap: 0 }}>
            <Bi hi="आगे: अंतिम निर्णय →" en="Next: the final decision" />
          </button>
        </>
      )}

      {/* STEP 2, a photo analysis on screen (it is the result of one way of checking, not a step of its own) */}
      {step === 2 && analysisOpen && (
        <>
          <StepTitle n={2} icon="🔍" hi="फ़ोटो विश्लेषण" en="Photo analysis" />
          <div style={{ marginBottom: 8 }} />

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
                    {analysisResult.ai_recommendation === 'advance' ? <Bi hi="⬆ आगे बढ़ें" en="Advance" /> : <Bi hi="🔄 दोहराएँ" en="Re-teach" />}
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

          <button type="button" className="btn btn-secondary" data-testid="back-to-work" onClick={() => setAnalysisOpen(false)} style={{ marginTop: 16, flexDirection: 'column', gap: 0 }}>
            <Bi hi="← बच्चों का काम: अगला समूह या तरीका" en="Back to the children's work: the next group or way" />
          </button>
          <button type="button" className="btn btn-primary" data-testid="to-final" onClick={enterFinal} style={{ marginTop: 8, marginBottom: 80, flexDirection: 'column', gap: 0 }}>
            <Bi hi="आगे: अंतिम निर्णय →" en="Next: the final decision" />
          </button>
        </>
      )}

      {/* STEP 3: the final decision per group, with the first judgment and today's evidence in front of the teacher */}
      {step === 3 && (() => {
        // today's evidence from the server; null when the reply has none (it could not be loaded, or an older server): then the screen says it cannot show it,
        // never "nobody assessed" (that is only said when the server counts zero)
        const evidence = planInfo && planInfo.today_evidence ? planInfo.today_evidence : null;
        const needed = groups.filter((g) => g.count > 0);
        const undecidedFinal = needed.filter((g) => !finals[g.label]);
        const choose = (label, d) => { setFinals((f) => ({ ...f, [label]: f[label] === d ? null : d })); setFinalDone(false); };
        const saveFinal = async () => {
          setLoading(true);
          try {
            const chosen = Object.fromEntries(needed.map((g) => [g.label, finals[g.label]]));
            await recordDecisions(teacher.teacher_id, today, selectedDomain, chosen, 'final');
            setFinalDone(true);
            setPlanInfo((p) => ({ ...(p || {}), final_decisions: chosen, decisions: { ...((p && p.decisions) || {}), ...chosen } }));
          } catch (e) { notify(friendlyError(e, { hi: 'अंतिम निर्णय दर्ज नहीं हो सके', en: 'The final decisions could not be recorded' }), 'error'); }
          setLoading(false);
        };
        return (
          <>
            <button type="button" className="btn btn-secondary btn-small" data-testid="final-back" onClick={() => goStep(2)} style={{ marginBottom: 8 }}>
              ← <span className="step-count">2/3</span> <Bi hi="बच्चों का काम" en="The children's work" inline />
            </button>
            <StepTitle n={3} hi="अंतिम निर्णय" en="Final decision" />
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
              <Bi hi="आज की जाँच देखकर हर समूह के लिए निर्णय पक्का करें। अगली योजना इन्हीं निर्णयों से सुझाई जाएगी।"
                en="With today's evidence in front of you, settle each group's decision. The next plan is suggested from these." />
            </p>
            {needed.map((g) => {
              const ev = (evidence && evidence[g.label]) || {};
              const first = decisions[g.label];
              const fin = finals[g.label];
              const L = GROUP_LABELS[g.label] || {};
              return (
                <div key={g.label} className={`card tier-card tier-${g.label}`} data-testid={`final-${g.label}`}>
                  <div className="card-header">
                    <div><span className={`badge badge-${g.label}`}>{L.hi}</span><span className="en en-inline" lang="en">{L.en}</span></div>
                  </div>
                  <SkillLine level={g.label} skillId={g.target_competency_id} name={g.target_competency_name_hi} withGroup={false} testid={`skill-3-${g.label}`} />
                  <div style={{ fontSize: '0.8125rem' }} data-testid={`final-first-${g.label}`}>
                    <Bi hi="पहला अनुमान" en="First judgment" inline />: {first ? <b>{DECISION_TEXT[first].hi}</b> : '—'}
                  </div>
                  <div style={{ fontSize: '0.8125rem', marginTop: 2 }} data-testid={`final-evidence-${g.label}`}>
                    <Bi hi="आज की जाँच" en="Today's evidence" inline />:{' '}
                    {!evidence || typeof ev.assessed !== 'number'
                      ? <span data-testid={`final-evidence-unknown-${g.label}`} style={{ color: '#8A5A00' }}><Bi hi="अभी नहीं दिख रही; पेज दोबारा खोलें" en="cannot be shown right now; reopen the page" inline /></span>
                      : ev.assessed > 0
                        ? <>✓ A {ev.a} · ~ PA {ev.pa} · ✗ NA {ev.na} <span style={{ color: 'var(--text-secondary)' }}>({ev.group_size} में से {ev.assessed} का आकलन<span className="en en-inline" lang="en">{ev.assessed} of {ev.group_size} assessed</span>)</span></>
                        : <span style={{ color: 'var(--text-secondary)' }}><Bi hi="अभी किसी का आकलन नहीं" en="nobody assessed yet" inline /></span>}
                  </div>
                  {ev.recommend && (
                    <div data-testid={`final-suggest-${g.label}`} style={{ fontSize: '0.8125rem', color: '#8A5A00', fontWeight: 600, marginTop: 2 }}>
                      <Bi hi="सुझाव: 🔄 दोहराएँ (एक-तिहाई या ज़्यादा बच्चों से गलती हुई)" en="Suggestion: re-teach (a third or more made a mistake)" inline />
                    </div>
                  )}
                  {!ev.recommend && ev.very_small && (
                    <div data-testid={`final-too-few-${g.label}`} style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                      <Bi hi="बहुत कम बच्चे जाँचे गए; ऐप कोई सुझाव नहीं देता।" en="Too few children checked for the app to suggest anything." inline />
                    </div>
                  )}
                  <div className="decision-row" style={{ marginTop: 6 }}>
                    {['advance', 'reteach', 'not_sure'].map((d) => (
                      <button key={d} type="button" className={`decision-btn ${d === 'advance' ? 'advance' : d === 'reteach' ? 'reteach' : ''} ${fin === d ? 'selected' : ''}`}
                        data-testid={`final-${g.label}-${d}`} aria-pressed={fin === d} onClick={() => choose(g.label, d)}>
                        <Bi hi={DECISION_TEXT[d].hi} en={DECISION_TEXT[d].en} />
                      </button>
                    ))}
                  </div>
                  {first && fin && fin !== first && (
                    <div data-testid={`final-changed-${g.label}`} style={{ fontSize: '0.75rem', fontWeight: 700, color: '#8A5A00', marginTop: 4 }}>
                      <Bi hi={`पहला अनुमान ${DECISION_TEXT[first].hi} → अंतिम ${DECISION_TEXT[fin].hi}`} en={`First ${DECISION_TEXT[first].en} → final ${DECISION_TEXT[fin].en}`} inline />
                    </div>
                  )}
                </div>
              );
            })}
            {undecidedFinal.length > 0 && (
              <p data-testid="finals-left" style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '8px 0 0' }}>
                <Bi hi={`हर समूह के लिए अंतिम निर्णय चुनें (बाकी: ${undecidedFinal.map((g) => `${GROUP_LABELS[g.label]?.mark || ''} ${GROUP_LABELS[g.label]?.hi || g.label}`.trim()).join(', ')})`}
                  en={`Choose a final decision for each group (left: ${undecidedFinal.map((g) => GROUP_LABELS[g.label]?.en || g.label).join(', ')})`} />
              </p>
            )}
            {finalDone ? (
              <div className="saved-block" data-testid="final-saved" role="status" style={{ marginTop: 10, borderLeftColor: 'var(--green-dark)', background: 'var(--green-bg)' }}>
                <div style={{ fontWeight: 600 }}><Bi hi="✓ अंतिम निर्णय दर्ज हुए। अगली योजना इन्हीं से सुझाई जाएगी।" en="Final decisions recorded. The next plan is suggested from them." /></div>
              </div>
            ) : (
              <button className="btn btn-primary" data-testid="record-final" onClick={saveFinal} disabled={loading || undecidedFinal.length > 0} style={{ marginTop: 8, flexDirection: 'column', gap: 0 }}>
                {loading ? <Bi hi="दर्ज हो रहा..." en="Recording" /> : <Bi hi="अंतिम निर्णय दर्ज करें" en="Record the final decisions" />}
              </button>
            )}
            {/* the review ends here: every change has its own way (first judgment: step 2's "←", another group: "← बच्चों का काम", a final decision: tap and record again) */}
            <div style={{ height: 80 }} aria-hidden="true" />
          </>
        );
      })()}
      </>)}
    </div>
  );
}
