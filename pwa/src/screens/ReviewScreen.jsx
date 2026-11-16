import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../App';
import { recordDecisions, recordObserved, recordORF, analysePhotos, replaceResults, getSavedAnalyses, getReviewCoverage, getReviewChannels, getCachedPlan } from '../services/api';
import { placeKey, loadPlace, savePlace } from '../services/reviewPlace';
import { historyState, pushMarks, replaceMarks } from '../services/backHistory';
import { compressImage } from '../utils/imageCompress';
import { useOnline } from '../components/OfflineBanner';
import { GROUP_LABELS, GROUP_ORDER } from '../tiers';
import Bi from '../components/Bi';
import PilotFlag from '../components/PilotFlag';
import GroupMark from '../components/GroupMark';
import ObservePanel, { observeOf } from '../components/ObservePanel';
import { bi } from '../services/language';
import { notify } from '../services/notify';
import { friendlyError } from '../services/errors';
import { localToday } from '../services/today';
import { useNavigate, useLocation } from 'react-router-dom';
import { ObservedSaved, ReadingSaved, SaveError } from '../components/ReviewConfirm';
import { DECISION_TEXT } from '../components/ProgressToday';
import { CHANNELS, channelOf, PRACTICE_ONLY, hasWorksheet } from '../services/reviewWays';
import SkillLine from '../components/SkillLine';
import AbbrKey from '../components/AbbrKey';
import FluencyLine from '../components/FluencyLine';
import { RESULT_MARK } from '../components/ProgressToday';
import { isFluencySkill } from '../services/pace';
import Hint from '../components/Hint';

// an English translation on the same line, after its Hindi (hidden by the "Hindi only" setting)
const SAVE_FAILED = { hi: 'सहेजा नहीं जा सका', en: 'Could not save' };
const OBS_CODE = { achieved: 'A', partially_achieved: 'PA', not_achieved: 'NA' };

const En = ({ children }) => <span className="en en-inline" lang="en">{children}</span>;

// Two steps since 14 Nov (Vaishnavi: "capture evidence -> make one final decision"; the first-judgment step is gone): "1/2 · आज का प्रदर्शन दर्ज करें",
// "2/2 · अंतिम निर्णय: कल क्या पढ़ाएँ?". Inside, the steps keep their old numbers (2 and 3: data-step, the history marks, the saved place); the heading shows 1/2 and 2/2.
export function StepTitle({ n, hi, en, icon }) {
  return (
    <h2 data-testid="review-title" data-step={n} style={{ marginBottom: 4 }}>
      <span className="step-count">{n === 3 ? 2 : 1}/2</span> {icon ? `${icon} ` : ''}<Bi hi={hi} en={en} inline />
    </h2>
  );
}

// "आज का प्रदर्शन दर्ज करें": one card per group, its way of checking and how many children are recorded today; a tap opens that group's recording below.
// The way follows from the group (today's plan), so there are no way tabs to choose from. Counts come from the same coverage the recording uses.
function GroupCards({ groups, channelsInfo, teacher, today, domain, tick, selected, onPick }) {
  const levels = (channelsInfo && channelsInfo.has_plan && channelsInfo.levels) || [];
  const [counts, setCounts] = useState({});
  useEffect(() => {
    let cancelled = false;
    levels.forEach((l) => {
      getReviewCoverage(teacher.teacher_id, today, domain, l.level, { channel: l.channel }).then((c) => {
        if (!cancelled && c) setCounts((prev) => ({ ...prev, [l.level]: c }));
      }).catch(() => {});
    });
    return () => { cancelled = true; };
  }, [channelsInfo, tick]);
  const WAY = { observed: { hi: 'देखकर जाँच', en: 'Observation' }, photo: { hi: 'वर्कशीट जाँच', en: 'Worksheet check' }, orf: { hi: 'पठन जाँच', en: 'Reading check' } };
  const shown = groups.filter((g) => g.count > 0 && levels.some((l) => l.level === g.label));
  if (!shown.length) return null;
  return (
    <div data-testid="group-cards" style={{ display: 'grid', gap: 6, marginBottom: 12 }}>
      {shown.map((g) => {
        const l = levels.find((x) => x.level === g.label);
        const way = channelOf(l.channel);
        const c = counts[g.label];
        const done = c ? (c.analysed_rolls || []).length : null;
        const target = c ? (c.sample && c.sample.mode === 'sample' ? c.sample.size : (c.group_rolls || []).length) : null;
        const complete = c && target > 0 && done >= target;
        return (
          <button key={g.label} type="button" className={`group-card tier-${g.label} ${selected === g.label ? 'on' : ''}`} data-testid={`group-card-${g.label}`} data-done={complete ? 'true' : 'false'}
            onClick={() => onPick(g.label, l.channel)}>
            <span className="group-card-name"><GroupMark group={g.label} name /> <span className="group-card-skill">{l.competency_id}</span></span>
            <span className="group-card-way">{way ? way.icon : ''} <Bi hi={WAY[l.channel]?.hi || ''} en={WAY[l.channel]?.en || ''} inline /></span>
            <span className="group-card-count" data-testid={`group-card-count-${g.label}`}>
              {c == null ? '…' : complete ? <>✓ <Bi hi="पूरा" en="done" inline /> ({done}/{target})</> : <>{done}/{target} <Bi hi="दर्ज" en="recorded" inline /></>}
            </span>
          </button>
        );
      })}
    </div>
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
  // opened from the plan's "अभी दर्ज करें" during the lesson: straight to the children's work, that way and group chosen, no first judgment asked
  // (observing and reading aloud are the teacher's own evidence: nothing to anchor her). Step 1 is still there after class.
  const location = useLocation();
  const [fromPlan] = useState(() => { const st = location && location.state; return st && st.from === 'plan' && st.channel ? st : null; });
  const [step, setStep] = useState(() => (fromPlan ? 2 : restored && restored.step === 3 ? 3 : 2));      // no step 1 any more: a place saved at step 1 opens at step 2
  const [analysisOpen, setAnalysisOpen] = useState(false);       // step 2: a photo analysis on screen instead of the ways of checking
  const [planInfo, setPlanInfo] = useState(null);                 // the server's plan reply: first judgments, final decisions, today's evidence per group
  const [finals, setFinals] = useState({});                       // step 3: the final decision chosen per group
  const [finalDone, setFinalDone] = useState(false);              // step 3: the final decisions were recorded
  const [decisions, setDecisions] = useState(() => (restored && restored.decisions) || {});
  const [channel, setChannel] = useState(() => (fromPlan ? fromPlan.channel : (restored && restored.channel) || null));
  const [photos, setPhotos] = useState([]);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [sheetLevel, setSheetLevel] = useState(() => (fromPlan ? fromPlan.level : (restored && restored.sheetLevel) || 'progressor'));   // which group's worksheet the photos are of
  const goStep = (n) => setStep(n);                  // a step chosen by the screen itself (on opening): no history entry
  // The phone's Back button follows the teacher's own moves in the Review (navigation D): each move to another step, or into a photo analysis, is an entry
  // in the browser's history marked with that view ('1', '2', 'a' for the analysis, '3'), so Back returns to the view before; from the view the Review was
  // opened at, Back leaves it as before. The screen's own "←" buttons do the same as Back when they go to the view just before.
  const view = analysisOpen ? 'a' : String(step);
  const viewRef = useRef(view);
  const showView = (v) => { setAnalysisOpen(v === 'a'); setStep(v === 'a' ? 2 : Number(v)); };
  const goView = (v) => {
    if (v === viewRef.current) return;
    if (historyState().reviewPrev === v) { window.history.back(); return; }        // the view just before: the same as the phone's Back (the pop shows it)
    pushMarks({ reviewView: v, reviewPrev: viewRef.current });
    viewRef.current = v;
    showView(v);
  };
  useEffect(() => { viewRef.current = view; if (historyState().reviewView !== view) replaceMarks({ reviewView: view }); }, [view]);
  useEffect(() => {
    const onPop = (e) => { const v = e.state && e.state.reviewView; if (v && v !== viewRef.current) { viewRef.current = v; showView(v); } };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);
  const touched = useRef(false);                     // the teacher has changed a decision on this screen: the server's copy never overwrites it
  const [loading, setLoading] = useState(false);
  const [replaceOff, setReplaceOff] = useState([]);     // "already checked today": the rolls the teacher UNticked (all ticked by default, 16 Nov)
  const [keptEarlier, setKeptEarlier] = useState(false); // she chose to keep all the earlier results: the card closes
  const [childView, setChildView] = useState('day');      // the children's cards: 'day' = everyone with a result today (17 Nov), 'round' = this round
  const online = useOnline();            // sending photos for analysis needs the internet (they go to the AI); the chosen photos stay on the screen
  const [observedItems, setObservedItems] = useState([]);
  const [orfEntry, setOrfEntry] = useState({ roll_number: '', cwpm: '', error_count: '' });
  const fileInput = useRef(null);
  const navigate = useNavigate();
  // in class: back to the plan, on the same group's slot with its You Do open (the browser's Back does the same: the plan is the entry before)
  const backToPlan = () => navigate('/yojana', { state: { slot: fromPlan && fromPlan.level, openYouDo: true } });
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
      if (touched.current || fromPlan) { setDecisions((prev) => ({ ...first, ...prev })); return; }        // opened from the plan: stay where the teacher asked to be
      setDecisions((prev) => ({ ...first, ...prev }));
      if (!restored && all(fin)) goStep(3);          // every group decided: the review opens at the decision
    }).catch((e) => { if (!cancelled) setPlanStatus(isToday(currentPlan) ? 'ready' : (e && e.status === 404 ? 'none' : 'error')); });
    return () => { cancelled = true; };
  }, [teacher.teacher_id, selectedDomain]);
  // a visit from the plan during the lesson is not where the review was left: it is never saved as the Review's place (13 Nov: the Review then reopened on that group's list)
  useEffect(() => { if (!fromPlan) savePlace(place, { step, decisions, channel, sheetLevel }); }, [place, step, decisions, channel, sheetLevel]);
  const groups = plan?.groups || [];
  // step 1 is complete when every group with children has a decision: until then "record" is off, and the screen says which groups are left
  const undecided = groups.filter((g) => g.count > 0 && !decisions[g.label]);
  const [savedAnalyses, setSavedAnalyses] = useState([]);
  const [coverage, setCoverage] = useState(null);       // who in this group is done today, and who is left
  const [coverageTick, setCoverageTick] = useState(0);  // a save happened: the group cards fetch their counts again
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
  // the teacher chooses the way and the group herself: when she asked for the other ways, or when today's ways are not known (no group cards then)
  const chooseByHand = showAllChannels || !(channelsInfo && channelsInfo.has_plan);
  const relevantChannels = channelsInfo && channelsInfo.has_plan && Object.keys(channelsInfo.channels).length ? Object.keys(channelsInfo.channels) : ALL_CHANNELS;
  const visibleChannels = showAllChannels ? ALL_CHANNELS : relevantChannels;
  const levelsFor = (ch) => (channelsInfo && channelsInfo.has_plan && channelsInfo.channels[ch]) || ['beginner', 'progressor', 'proficient'];
  const activeChannel = channel === 'observed' ? 'observed' : channel === 'orf' ? 'orf' : 'photo';
  const levelInfo = (ch) => (channelsInfo?.levels || []).find(l => l.channel === ch && l.level === sheetLevel);
  const observedLevel = levelInfo('observed');
  const orfLevel = levelInfo('orf');
  useEffect(() => {      // nothing chosen yet: the first group of today's plan, with its own way (the group cards choose after that)
    if (step !== 2 || channel || showAllChannels) return;
    const first = (channelsInfo && channelsInfo.has_plan && channelsInfo.levels || [])[0];
    if (first) { setChannel(first.channel); setSheetLevel(first.level); }
    else if (relevantChannels.length === 1) setChannel(relevantChannels[0]);
  }, [step, channelsInfo]);
  useEffect(() => {      // keep the selected group one that uses this channel
    if (!channel) return;
    const allowed = levelsFor(activeChannel);
    if (!allowed.includes(sheetLevel)) setSheetLevel(allowed[0]);
  }, [channel, channelsInfo]);
  const refreshCoverage = () => {
    setCoverageTick((t) => t + 1);          // the group cards count again
    if (!teacher?.teacher_id || !selectedDomain) return;
    getReviewCoverage(teacher.teacher_id, today, selectedDomain, sheetLevel, { absent, channel: activeChannel }).then(setCoverage).catch(() => setCoverage(null));
  };
  useEffect(() => { setAbsent([]); }, [sheetLevel]);
  useEffect(refreshCoverage, [teacher?.teacher_id, selectedDomain, today, sheetLevel, savedAnalyses.length, absent.join(','), activeChannel]);
  const openSaved = (a) => { setAnalysisResult({ ...a.result, analysis_id: a.id }); setReplaceOff([]); setKeptEarlier(false); setChildView('day'); setSheetLevel(a.worksheet_level); goView('a'); };
  // "Use the new photos" (16 Nov): the AI already read these sheets in this round; their readings replace the earlier results, no new AI call
  const useNewPhotos = async (rolls) => {
    if (!rolls.length || !analysisResult || !analysisResult.analysis_id) return;
    setLoading(true);
    try {
      const result = await replaceResults(teacher.teacher_id, analysisResult.analysis_id, rolls);
      setAnalysisResult(result); setReplaceOff([]); setKeptEarlier(false); setChildView('day');
      refreshSaved(); refreshCoverage();
    } catch (e) {
      notify(friendlyError(e, { hi: 'नई फ़ोटो से नतीजे नहीं बदले जा सके', en: 'The new photos could not be used' }), 'error');
    }
    setLoading(false);
  };
  // step 3: today's evidence fetched again (the children's work may have changed it), and each group's choice starts on her final decision if one
  // was recorded, else on her first judgment
  const enterFinal = async () => {
    goView('3');
    try {
      const reply = await getCachedPlan(teacher.teacher_id, today, selectedDomain);
      setPlanInfo(reply);
      setFinals((prev) => { const out = { ...prev }; groups.forEach((g) => { if (!out[g.label]) out[g.label] = (reply.final_decisions || {})[g.label] || null; }); return out; });
    } catch { /* keep the choices on screen */ }
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
      goView('2');
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
      // no first judgment since 14 Nov: the field is not sent (an empty one broke the save after the AI call, 15 Nov)
      fd.append('on_duplicate', 'skip');                       // a child already analysed today keeps the earlier result
      if (opts.replaceRolls && opts.replaceRolls.length) fd.append('replace_rolls', opts.replaceRolls.join(','));
      photos.forEach(p => fd.append('photos', p));
      const result = await analysePhotos(teacher.teacher_id, fd);
      setAnalysisResult(result); setReplaceOff([]); setKeptEarlier(false); setChildView('day');
      goView('a');
      refreshSaved();
      refreshCoverage();
    } catch (e) {
      if (e && e.code === 'wrong_group') {          // the sheets are another group's: say so, move to that group's card, keep the photos to send again
        const lv = (e.detail && e.detail.suggested_level) || '';
        const L = GROUP_LABELS[lv] || { hi: lv, en: lv, mark: '' };
        const rolls = ((e.detail && e.detail.rolls) || []).join(', ');
        notify(bi(`ये वर्कशीट ${L.mark} ${L.hi} समूह के बच्चों की लगती हैं (रोल ${rolls})। कुछ भी दर्ज नहीं हुआ। ऊपर ${L.mark} ${L.hi} का कार्ड चुनकर यही फ़ोटो दोबारा भेजें।`,
          `These sheets look like the ${L.en} group's (roll ${rolls}). Nothing was saved. Choose the ${L.en} card above and send the same photos again.`), 'error');
        if (!fromPlan && lv) setSheetLevel(lv);
        setLoading(false);
        return;
      }
      notify(friendlyError(e, { hi: 'फ़ोटो का विश्लेषण नहीं हो सका', en: 'The photos could not be analysed' }, { 400: { hi: 'फ़ोटो पढ़ी नहीं जा सकी। वर्कशीट की साफ़ फ़ोटो चुनें।', en: "The photo couldn't be read. Choose a clear photo of the worksheet." } }), 'error'); }
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

  // the photo result's children (17 Nov): everyone with a result today (each child's latest card), or this round only; "photograph again" cards always stay
  const dayKids = (analysisResult && analysisResult.today_group && analysisResult.today_group.per_child) || null;
  const roundKids = (analysisResult && analysisResult.per_child) || [];
  const showDayKids = !!dayKids && childView === 'day';
  const freshRolls = new Set(roundKids.filter((c) => c.accuracy != null).map((c) => c.roll_number));
  const cardList = showDayKids ? [...dayKids, ...roundKids.filter((c) => c.accuracy == null)] : roundKids;

  return (
    <div className="screen">
      <div className="screen-header">
        {/* in class (opened from a group's You Do): one group, one way, and the way back to that group's slot; nothing else of the Review */}
        {fromPlan ? (
          <button type="button" className="btn btn-secondary btn-small" data-testid="back-to-plan" onClick={backToPlan}>← <Bi hi="योजना" en="Plan" inline /></button>
        ) : null}
        <h1>{fromPlan ? <>{channelOf(fromPlan.channel)?.icon} <Bi hi="कक्षा में दर्ज करें" en="Record in class" inline /></> : <>☑️ <Bi hi="आकलन" en="Assess" inline /></>}</h1>
        {!fromPlan && (
          <button type="button" className="btn btn-secondary btn-small" data-testid="review-to-plan" onClick={() => navigate('/yojana')}>📋 <Bi hi="आज की योजना" en="Today's plan" inline /></button>
        )}
      </div>
      {fromPlan && step === 2 && (
        <div data-testid="from-plan" className={`in-class-bar tier-${fromPlan.level}`}>
          <GroupMark group={fromPlan.level} name /> · <Bi hi={channelOf(fromPlan.channel)?.hi || ''} en={channelOf(fromPlan.channel)?.en || ''} inline />
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 2 }}>
            <Bi hi="सिर्फ़ इसी समूह के बच्चे। अभी दर्ज करें, या कागज़ पर लिखकर पढ़ाने के बाद आकलन में। अगली कक्षा में क्या पढ़ाना है, यह पढ़ाने के बाद तय होगा।" en="Only this group's children. Record now, or note it on paper and enter it later in Assess. You decide the next class after teaching." />
          </div>
        </div>
      )}

      {/* no plan for today in this subject (or it could not be loaded): say so, and the way to make one */}
      {!plan && (planStatus === 'loading' ? (
        <div className="loading" data-testid="review-loading"><div className="spinner" /><span><Bi hi="आज की योजना खोली जा रही है…" en="Opening today's plan" inline /></span></div>
      ) : (
        <div className="card" data-testid="review-no-plan" style={{ textAlign: 'center' }}>
          {planStatus === 'none'
            ? <Bi hi="आज इस विषय की योजना नहीं बनी है। पहले योजना बनाएँ; पढ़ाने के बाद यहाँ आकलन करें।" en="No plan for this subject today. Make a plan first; assess here after teaching." />
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
          <div style={{ fontWeight: 600, fontSize: '0.875rem', marginBottom: 6 }}>🔍 <Bi hi="आज का विश्लेषण उपलब्ध है" en="Today's photo results, tap to open" inline /></div>
          {(() => {
            // 16 Nov: one card per group, its NEWEST round (which opens with the whole group's day on top); the earlier rounds under a fold.
            // Each card counts the group's day when the round has it (today_group), else the round's own children. In both languages.
            const card = (a, testid) => {
              const day = a.result.today_group;
              const n = day ? day.children : (a.result.children_scored ?? a.result.children_analysed);
              const acc = day ? day.group_accuracy : a.result.group_accuracy;
              const L = GROUP_LABELS[a.worksheet_level] || { hi: a.worksheet_level, en: a.worksheet_level, mark: '' };
              return (
                <button key={a.id} type="button" className="btn btn-secondary" onClick={() => openSaved(a)} data-testid={testid}
                  style={{ width: '100%', display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: '0.8125rem' }}>
                  <span>{L.mark} <Bi hi={`${L.hi} · ${n} बच्चे`} en={`${L.en} · ${n} ${n === 1 ? 'child' : 'children'}`} inline /> · {acc == null ? '—' : `${Math.round(acc * 100)}%`}</span>
                  <span style={{ color: 'var(--text-secondary)' }}>{new Date(a.created_at).toLocaleTimeString('hi-IN', { hour: '2-digit', minute: '2-digit' })} <Bi hi="देखें" en="Open" inline /> →</span>
                </button>
              );
            };
            const newest = [], earlier = [], seen = new Set();
            savedAnalyses.forEach((a) => { if (seen.has(a.worksheet_level)) earlier.push(a); else { seen.add(a.worksheet_level); newest.push(a); } });
            return <>
              {newest.map((a) => card(a, `saved-latest-${a.worksheet_level}`))}
              {earlier.length > 0 && (
                <details data-testid="saved-earlier" style={{ fontSize: '0.8125rem' }}>
                  <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)', marginBottom: 6 }}><Bi hi={`आज के पहले के दौर (${earlier.length})`} en={`Earlier rounds today (${earlier.length})`} inline /></summary>
                  {earlier.map((a) => card(a, `saved-earlier-${a.id}`))}
                </details>
              )}
            </>;
          })()}
        </div>
      )}


      {/* STEP 2: Evidence capture */}
      {step === 2 && !analysisOpen && (
        <>
          {!fromPlan && (<>
          <StepTitle n={2} hi="आज का प्रदर्शन दर्ज करें" en="Record today's performance" />
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '0 0 10px' }} data-testid="performance-intro">
            <Bi hi="हर समूह के लिए: कक्षा में दर्ज हो चुका है तो देख लें; कागज़ पर लिखा है तो यहाँ दर्ज करें; वर्कशीट की फ़ोटो लें। किसी भी क्रम में, आज के दिन कभी भी।"
              en="For each group: check what was recorded in class, enter what you noted on paper, or photograph the worksheets. In any order, any time today." />
          </p>
          <GroupCards groups={groups} channelsInfo={channelsInfo} teacher={teacher} today={today} domain={selectedDomain} tick={coverageTick}
            selected={sheetLevel} onPick={(level, way) => { setChannel(way); setSheetLevel(level); setShowAllChannels(false); }} />
          </>)}

          {!fromPlan && chooseByHand && <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            {CHANNELS.filter(ch => visibleChannels.includes(ch.id)).map(ch => (
              <button key={ch.id} className={`domain-tab ${channel === ch.id ? 'active' : ''}`} data-testid={`channel-${ch.id}`}
                onClick={() => setChannel(ch.id)}>
                {ch.icon} <Bi hi={ch.hi} en={ch.en} />
                {channelsInfo?.has_plan && channelsInfo.channels[ch.id] && <div style={{ fontSize: '0.55rem', fontWeight: 400 }}>{channelsInfo.channels[ch.id].map(l => LEVEL_HI[l]).join(', ')}</div>}
              </button>
            ))}
          </div>}
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
                <p data-testid="worksheet-practice" style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--info)', margin: '2px 0 4px' }}><Bi hi={PRACTICE_ONLY.hi} en={PRACTICE_ONLY.en} inline /></p>
              )}
              <ol data-testid="how-steps" style={{ margin: '2px 0 4px', paddingLeft: 20, fontSize: '0.8125rem' }}>
                {channelOf(channel).how.map((st, i) => <li key={i} style={{ marginBottom: 2 }}><Bi hi={st.hi} en={st.en} inline /></li>)}
              </ol>
            </details>
          )}
          {/* today's skills need only some of the three ways: why, which groups, and the other ways if the teacher wants them */}
          {!fromPlan && channelsInfo?.has_plan && relevantChannels.length < 3 && (
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
                {showAllChannels ? <Bi hi="सिर्फ़ ज़रूरी तरीके दिखाएँ" en="Show fewer ways" inline /> : <Bi hi="दूसरे तरीके भी दिखाएँ" en="Show all ways to record" inline />}
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
                {!fromPlan && chooseByHand && levelsFor('observed').length > 1 && (
                  <div style={{ display: 'flex', gap: 6, margin: '6px 0' }}>
                    {levelsFor('observed').map(l => <button key={l} type="button" className={`tier-option tier-${l} ${sheetLevel === l ? 'selected' : ''}`} onClick={() => setSheetLevel(l)}>{GROUP_LABELS[l].mark} {LEVEL_HI[l]}</button>)}
                  </div>
                )}
                <SkillLine level={observedLevel.level} skillId={observedLevel.competency_id} name={observedLevel.name_hi} nameEn={observedLevel.name_en} testid="skill-2" />
                {/* what A / PA / NA mean for today's task (in class: the task and materials too; after class: only what to look for) */}
                <ObservePanel observe={observeOf(plan && plan.plan, observedLevel.level)} testid="observe-review" compact={!fromPlan} />
                <AbbrKey testid="abbr-observe" />
                {big && (
                  <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                    <button type="button" data-testid="obs-mode-sample" style={mode(useSample)} onClick={() => setSampleMode('sample')}><Bi hi="नमूना" en="Sample" inline /> {sample.size}/{sample.group_size}</button>
                    <button type="button" style={mode(!useSample)} onClick={() => setSampleMode('all')}><Bi hi="सभी" en="Everyone" inline /> {coverage.group_rolls.length}</button>
                  </div>
                )}
                {/* what the last save recorded; the list below stays usable (retap and submit again) */}
                <ObservedSaved saved={observedSaved} onOpenProgress={toProgress} />
                <SaveError message={observedError} testid="observed-error" />
                {rolls.map(r => (
                  <div key={r} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                    <b style={{ width: 78, fontSize: '0.8125rem' }}><Bi hi="रोल" en="Roll" inline /> {r}{names && names[r] && <div style={{ fontSize: '0.7rem', fontWeight: 500 }} data-testid={`name-${r}`}>{names[r]}</div>}{coverage?.labels?.[r] && <div style={{ fontSize: '0.55rem', fontWeight: 400, color: 'var(--text-secondary)' }}>{coverage.labels[r]}</div>}</b>
                    {[['achieved', 'A', 'var(--green-dark)'], ['partially_achieved', 'PA', 'var(--info)'], ['not_achieved', 'NA', 'var(--text)']].map(([st, code, color]) => (
                      <button key={st} type="button" data-testid={`obs-${r}-${st}`} aria-pressed={shown(r) === st} data-state={statusOf(r) === st ? (isChange(r) ? 'changing' : 'new') : (!statusOf(r) && recordedOf(r) === st ? 'recorded' : 'off')}
                        style={btn(shown(r) === st, color, isChange(r) && statusOf(r) === st)} onClick={() => tap(r, st)}>{code}</button>
                    ))}
                    {isChange(r)
                      ? <span data-testid={`obs-change-${r}`} style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--info)' }}>{OBS_CODE[recordedOf(r)]} → {OBS_CODE[statusOf(r)]}</span>
                      : recordedOf(r) && <span data-testid={`obs-recorded-${r}`} style={{ fontSize: '0.7rem', color: 'var(--green-dark)' }}>✓ <Bi hi="दर्ज" en="recorded" inline /></span>}
                    {useSample && !saved.has(r) && <button type="button" data-testid={`obs-absent-${r}`} style={{ marginLeft: 'auto', minHeight: 44, padding: '0 6px', background: 'none', border: 'none', fontSize: '0.75rem', color: 'var(--text-secondary)', textDecoration: 'underline', fontFamily: 'inherit' }}
                      onClick={() => setAbsent(prev => [...prev, r])}><Bi hi="अनुपस्थित" en="Absent" inline /></button>}
                  </div>
                ))}
                {useSample && <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 6 }} data-testid="sample-note-obs"><span className="hi">नमूना समूह की मोटी तस्वीर देता है।</span><span className="en" lang="en">A sample gives a rough picture of the group.</span></p>}
                <button className="btn btn-primary" onClick={submitObserved} disabled={loading || !observedItems.length} style={{ marginTop: 8 }} data-testid="obs-submit">
                  {loading ? <Bi hi="दर्ज हो रहा..." en="Saving…" inline /> : <><span className="hi">✓ जमा करें{observedItems.length > 0 && <> · {[newCount && `${newCount} ${newCount === 1 ? 'नया' : 'नए'}`, changeCount && `${changeCount} बदलाव`].filter(Boolean).join(', ')}</>}</span>
                    <En>✓ Save{observedItems.length > 0 ? ` · ${[newCount && `${newCount} new`, changeCount && `${changeCount} ${changeCount === 1 ? 'change' : 'changes'}`].filter(Boolean).join(', ')}` : ''}</En></>}
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
                  <strong>{observedItems.length} <Bi hi="दर्ज" en="recorded" inline />:</strong>{' '}
                  {observedItems.map(i => `R${i.roll_number}:${i.status[0].toUpperCase()}`).join(', ')}
                </div>
              )}
              <button className="btn btn-primary" onClick={submitObserved} disabled={loading || !observedItems.length} style={{ marginTop: 8 }}>
                {loading ? 'दर्ज हो रहा...' : <>✓ {observedItems.length} <Bi hi="अवलोकन जमा करें" en="Save" inline /></>}
              </button>
            </div>
          )}

          {/* Photo */}
          {channel === 'photo' && (
            <div className="card">
              {/* which group's sheet these photos are taken as: said plainly, right above the photos (15 Nov: a test batch went in as the Beginners' sheet unnoticed) */}
              <div className={`photo-for tier-${sheetLevel}`} data-testid="photo-for">
                <Bi hi="इन फ़ोटो को इस समूह की वर्कशीट माना जाएगा" en="Photos for" inline />: <b><GroupMark group={sheetLevel} name /></b>
                {!fromPlan && <span style={{ fontWeight: 400 }}> · <Bi hi="दूसरा समूह? ऊपर उसका कार्ड चुनें" en="Wrong group? Choose the right card above" inline /></span>}
              </div>
              <PilotFlag testid="pilot-photo" chip={{ icon: '🤖', hi: 'AI जाँच', en: 'AI marking' }} hi="नतीजे देखें; निर्णय आपका है।"
                en="Check the results; the decision is yours." />
              {/* the group comes from the group card above (or from the plan, in class): this choice only with the other ways shown */}
              {!fromPlan && chooseByHand && (<>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '4px 0' }}><Bi hi="किस समूह की वर्कशीट?" en="Which group's sheet?" inline /></div>
              <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                {GROUP_ORDER.filter((id) => levelsFor('photo').includes(id)).map((id) => (
                  <button key={id} type="button" onClick={() => setSheetLevel(id)} className={`tier-option tier-${id} ${sheetLevel === id ? 'selected' : ''}`}>
                    {GROUP_LABELS[id].mark} <Bi hi={GROUP_LABELS[id].hi} en={GROUP_LABELS[id].en} />
                  </button>
                ))}
              </div>
              </>)}
              {(() => { const g = groups.find((x) => x.label === sheetLevel) || {}; return <SkillLine level={sheetLevel} skillId={g.target_competency_id} name={g.target_competency_name_hi} nameEn={g.target_competency_name_en} testid="skill-2" />; })()}
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
                        <button type="button" data-testid="mode-sample" style={mode(useSample)} onClick={() => setSampleMode('sample')}><Bi hi="नमूना" en="Sample" inline /> {sample.size}/{sample.group_size}</button>
                        <button type="button" data-testid="mode-all" style={mode(!useSample)} onClick={() => setSampleMode('all')}><Bi hi="सभी" en="Everyone" inline /> {coverage.group_rolls.length}</button>
                      </div>
                    )}
                    <div><b>✓ <Bi hi="हो चुके" en="Done" inline />: {done.length}/{total}</b>{done.length > 0 && <> · <Bi hi="रोल" en="roll" inline /> {done.join(', ')}</>}</div>
                    {left.length === 0 ? <div style={{ marginTop: 2 }} data-testid="all-done"><b>✓ <Bi hi="सब हो गए" en="All done" inline /></b></div> : (
                    <div style={{ marginTop: 2 }}>
                      ⏳ {useSample ? <><Bi hi="इन बच्चों की फ़ोटो लें" en="Photograph these children's sheets" inline /></> : <><Bi hi="बाकी" en="Left" inline /></>}:{' '}
                      {left.length === 0 ? <><Bi hi="कोई नहीं" en="none" inline /></> : useSample
                        ? left.map(r => <button key={r} type="button" data-testid={`chip-${r}`} title={[names && names[r], coverage.labels?.[r]].filter(Boolean).join(' · ')} className="chip" onClick={() => toggleAbsent(r)}>{r}{coverage.labels?.[r] ? <span style={{ fontSize: '0.55rem', color: 'var(--text-secondary)' }}> {coverage.labels[r]}</span> : null}</button>)
                        : left.join(', ')}
                    </div>)}
                    {useSample && left.length > 0 && <div style={{ color: 'var(--text-secondary)' }}><Bi hi="कोई बच्चा अनुपस्थित है? उसके रोल पर दबाएँ, उसकी जगह दूसरा बच्चा सुझाया जाएगा।" en="Child absent? Tap their roll number to get another child." /></div>}
                    {useSample && sample.absent.length > 0 && (
                      <div style={{ marginTop: 4 }}><Bi hi="अनुपस्थित" en="Absent" inline />: {sample.absent.map(r => <button key={r} type="button" data-testid={`absent-${r}`} className="chip" onClick={() => toggleAbsent(r)}>{r} ✕</button>)}</div>
                    )}
                    {useSample && (
                      <div data-testid="sample-note" style={{ color: 'var(--text-secondary)', marginTop: 4 }}>
                        <span className="hi">नमूना समूह की मोटी तस्वीर देता है। स्तर सिर्फ़ आकलन से बदलते हैं, दैनिक नमूने से नहीं।</span>
                        <span className="en" lang="en">A sample gives a rough picture of the group. Levels change only through an assessment, never from daily results.</span>
                      </div>
                    )}
                    {!useSample && done.length > 0 && <div style={{ color: 'var(--text-secondary)', marginTop: 2 }}><Bi hi="जो हो चुके हैं उनकी दोबारा फ़ोटो न लें।" en="Already done: no need to photograph these again." /></div>}
                  </div>
                );
              })()}
              <div className="capture-area" onClick={() => fileInput.current?.click()}>
                <div className="capture-icon">📷</div>
                <p className="hi">वर्कशीट की फ़ोटो लें या चुनें: एक बार में 6 तक (और फ़ोटो अगली बार भेजें)</p>
                <p className="en" lang="en" style={{ fontSize: '0.75rem' }}>Take or choose photos: up to 6 at a time (send more in another round)</p>
                <input ref={fileInput} type="file" accept="image/*" capture="environment"
                  multiple onChange={handlePhotoCapture} style={{ display: 'none' }} />
              </div>
              {dupNotice && <div style={{ fontSize: '0.75rem', color: 'var(--info)', background: 'var(--info-bg)', borderRadius: 8, padding: '4px 10px', marginTop: 6 }} data-testid="dup-notice">⚠ {dupNotice}</div>}
              <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: 6 }} data-testid="photo-name-hint">
<Bi hi="फ़ोटो में बच्चे का नाम न आने दें। नाम AI को कभी नहीं भेजे जाते, पर फ़ोटो में लिखा नाम चला जाएगा।" en="Keep names off the sheet: the app never sends names to the AI, but a name in the photo would be sent." />
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
                    ) : <>🔍 <span className="hi">{photos.length} फ़ोटो का विश्लेषण करें</span><span className="en en-inline" lang="en">Analyse {photos.length} {photos.length === 1 ? 'photo' : 'photos'}</span></>}
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
                  <SkillLine level={orfLevel.level} skillId={orfLevel.competency_id} name={orfLevel.name_hi} nameEn={orfLevel.name_en} testid="skill-2" />
                  {coverage && coverage.sample && coverage.sample.rotation && coverage.sample.later > 0 && (
                    <div data-testid="orf-today" className="note note-info" style={{ margin: '4px 0 6px' }}>
                      <Bi hi={`आज ${coverage.sample.size} बच्चे · बाकी ${coverage.sample.later} अगले दिनों में`} en={`Today ${coverage.sample.size} children · the other ${coverage.sample.later} on the next days`} inline />
                    </div>
                  )}
                  {orfLevel.passage ? (
                    <div data-testid="orf-passage" style={{ fontSize: '0.8125rem', marginBottom: 6 }}>
                      <Bi hi="पढ़ने का पाठ" en="Passage to read" inline />: <b>«{orfLevel.passage.title}»</b> ({orfLevel.passage.word_count} <Bi hi="शब्द" en="words" inline />)
                      <details className="fold" data-testid="orf-passage-text" style={{ marginTop: 2 }}>
                        <summary><span><Bi hi="पाठ दिखाएँ (बच्चा यहीं से पढ़ सकता है)" en="Show the passage (the child reads from the phone)" inline /></span></summary>
                        <p lang="hi" style={{ fontSize: '1.125rem', lineHeight: 1.7, whiteSpace: 'pre-line', margin: '4px 0' }}>{orfLevel.passage.text}</p>
                      </details>
                    </div>
                  ) : (
                    <div data-testid="orf-no-passage" style={{ fontSize: '0.75rem', color: 'var(--info)', marginBottom: 6 }}>
                      <Bi hi="इस कौशल का पाठ बैंक में नहीं मिला; अपनी कक्षा के स्तर का कोई ऐसा पाठ लें जो बच्चों ने आज नहीं पढ़ा।" en="No text for this skill in the bank; use a text at your class's level that the children have not read today." inline />
                    </div>
                  )}
                  {!fromPlan && chooseByHand && levelsFor('orf').length > 1 && (
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
                        : <>✓ <Bi hi="रोल" en="Roll" inline /> {roll}{rec.cwpm != null ? <>: {rec.cwpm} <Bi hi="सही शब्द/मिनट" en="correct words a minute" inline /></> : ''} · <span className="badge badge-result">{RESULT_MARK[rec.status] || '—'}</span></>}
                    </div>
                  ))}
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                    <Bi hi="गलत दर्ज हुआ हो तो वही रोल नंबर फिर दर्ज करें; नया नतीजा गिना जाएगा।" en="Entered a wrong score? Enter the same roll number again; the latest counts." />
                  </div>
                </details>
              )}
              <SaveError message={orfError} testid="orf-error" />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <input type="number" inputMode="numeric" placeholder="रोल नं." aria-label="रोल नंबर (Roll number)" value={orfEntry.roll_number}
                  onChange={e => setOrfEntry(o => ({ ...o, roll_number: e.target.value }))}
                  style={{ padding: 10, borderRadius: 8, border: '1px solid var(--border)', fontSize: '1rem', fontFamily: 'inherit' }} />
                <input type="number" inputMode="numeric" placeholder={bi('सही शब्द/मिनट', 'Correct words per minute')} aria-label="सही शब्द प्रति मिनट (Correct Words Per Minute)" value={orfEntry.cwpm}
                  onChange={e => setOrfEntry(o => ({ ...o, cwpm: e.target.value }))}
                  style={{ padding: 10, borderRadius: 8, border: '1px solid var(--border)', fontSize: '1rem', fontFamily: 'inherit' }} />
                <input type="number" inputMode="numeric" placeholder={bi('गलतियाँ', 'Mistakes')} aria-label="गलतियाँ (Errors)" value={orfEntry.error_count}
                  onChange={e => setOrfEntry(o => ({ ...o, error_count: e.target.value }))}
                  style={{ padding: 10, borderRadius: 8, border: '1px solid var(--border)', fontSize: '1rem', fontFamily: 'inherit' }} />
              </div>
              <button className="btn btn-primary" onClick={submitORF}
                disabled={loading || !orfEntry.roll_number || !orfEntry.cwpm} style={{ marginTop: 10 }}>
                {loading ? 'दर्ज हो रहा...' : <>⏱️ <Bi hi="पठन दर्ज करें" en="Save reading score" inline /></>}
              </button>
            </div>
          )}

          {!channel && (
            <div className="empty-state">
              <p><Bi hi="ऊपर से एक समूह या तरीका चुनें" en="Choose a group above to start" /></p>
            </div>
          )}

          {fromPlan && (
            <button type="button" className="btn btn-primary" data-testid="done-in-class" onClick={backToPlan} style={{ marginTop: 12, marginBottom: 80, flexDirection: 'column', gap: 0 }}>
              <Bi hi="← पढ़ाना जारी रखें (योजना पर लौटें)" en="Back to today's plan" />
            </button>
          )}
          {!fromPlan && (analysisResult || savedAnalyses.length > 0) && (
            <button className="btn btn-secondary" data-testid="see-analysis" onClick={() => (analysisResult ? goView('a') : openSaved(savedAnalyses[0]))} style={{ marginTop: 12 }}>
              <Bi hi="फ़ोटो विश्लेषण देखें" en="See the photo results" inline /> →
            </button>
          )}
          {!fromPlan && (
          <button type="button" className="btn btn-primary" data-testid="to-final" onClick={enterFinal} style={{ marginTop: 12, marginBottom: 80, flexDirection: 'column', gap: 0 }}>
            <Bi hi="आगे: अगली कक्षा में क्या पढ़ाएँ, तय करें →" en="Next: decide for the next class →" />
          </button>
          )}
        </>
      )}

      {/* STEP 2, a photo analysis on screen (it is the result of one way of checking, not a step of its own) */}
      {step === 2 && analysisOpen && (
        <>
          <StepTitle n={2} icon="🔍" hi="फ़ोटो विश्लेषण" en="Photo analysis" />
          <div style={{ marginBottom: 8 }} />

          {analysisResult ? (
            <>
              {(() => {
                // 16 Nov: the main numbers are the WHOLE group's day (every photo saved today for it), not only this round: after "use the new photo"
                // a group of six read "1 child". This round's own count is the line under them. An older saved round without today_group shows its own.
                const day = analysisResult.today_group;
                const n = day ? day.children : (analysisResult.children_scored ?? analysisResult.children_analysed);
                const acc = day ? day.group_accuracy : analysisResult.group_accuracy;
                const rec = day ? day.ai_recommendation : analysisResult.ai_recommendation;
                const G = GROUP_LABELS[sheetLevel] || { hi: '', en: '', mark: '' };
                return (
              <div className="card">
                {loading && <div data-testid="saving" role="status" style={{ fontSize: '0.8125rem', color: 'var(--info)', background: 'var(--info-bg)', borderRadius: 6, padding: '4px 8px', marginBottom: 8 }}>
                  ⏳ <Bi hi="सहेजा जा रहा है…" en="Saving…" inline /></div>}
                {day && <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 6 }} data-testid="day-heading">
                  <Bi hi={`आज ${G.mark} ${G.hi} की सभी फ़ोटो`} en={`Today, all photos for ${G.mark} ${G.en}`} inline /></div>}
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span><Bi hi="जाँचे गए बच्चे" en="Children marked" /></span>
                  <strong data-testid="children-scored">{n}
                    {analysisResult.retake?.length > 0 && <span style={{ fontWeight: 400, fontSize: '0.75rem' }}> · {analysisResult.retake.length} <Bi hi="की फ़ोटो दोबारा" en="to photograph again" inline /></span>}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span><Bi hi="समूह शुद्धता" en="Group score" /></span>
                  <strong data-testid="group-accuracy">{acc == null ? '—' : `${Math.round(acc * 100)}%`}</strong>
                </div>
                {/* a sample (16 Nov): the result stands, but says what it rests on and who is left, so the teacher can decide now or photograph more */}
                {acc != null && coverage && coverage.group_rolls && (() => {
                  const s = coverage.sample, useSample = coverage.group_rolls.length > 8 && s && sampleMode === 'sample';
                  const done = useSample ? s.done : coverage.analysed_rolls, left = useSample ? s.left : coverage.pending_rolls, total = useSample ? s.size : coverage.group_rolls.length;
                  if (!left || left.length === 0) return null;
                  const who = useSample ? ['नमूने के', 'sample '] : ['समूह के', 'group '];
                  return (
                    <div data-testid="based-on" style={{ fontSize: '0.75rem', color: 'var(--info)', background: 'var(--info-bg)', borderRadius: 6, padding: '4px 8px', marginBottom: 8 }}>
                      <Bi hi={`${who[0]} ${total} में से ${done.length} बच्चों पर आधारित। पक्के नतीजे के लिए बाकी ${left.length} की फ़ोटो लें: रोल ${left.join(', ')}`}
                        en={`Based on ${done.length} of the ${total} ${who[1]}children. Photograph the other ${left.length} for a firmer result: roll ${left.join(', ')}`} />
                    </div>
                  );
                })()}
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span><Bi hi="AI सुझाव" en="AI suggests" /></span>
                  <strong data-testid="ai-suggests" style={{ color: rec === 'advance' ? 'var(--green-dark)' : 'var(--reteach)', textAlign: 'right' }}>
                    {rec == null ? <Bi hi="— (किसी बच्चे का आकलन नहीं हुआ)" en="— (no child assessed)" /> : rec === 'advance' ? <Bi hi="⬆ आगे बढ़ें" en="Move on" /> : <Bi hi="🔄 दोहराएँ" en="Teach again" />}
                  </strong>
                </div>
                {day && <div data-testid="this-round" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 8, borderTop: '1px solid var(--border)', paddingTop: 6 }}>
                  <Bi hi={`इस बार: ${analysisResult.children_scored ?? analysisResult.children_analysed} बच्चे जाँचे गए`} en={`This round: ${analysisResult.children_scored ?? analysisResult.children_analysed} marked`} inline />
                  {analysisResult.group_accuracy != null && <> · {Math.round(analysisResult.group_accuracy * 100)}%</>}</div>}
                {analysisResult.copy_errors_excluded > 0 && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 6 }}>
                    ✏️ {analysisResult.copy_errors_excluded} <Bi hi="सवाल गिने नहीं गए: बच्चों ने उन्हें अलग उतारा" en="questions not marked: copied wrongly" inline />
                  </div>
                )}
              </div>
                );
              })()}

              {/* several sheets with the SAME different numbers (16 Nov): most likely not today's worksheet, e.g. the plan was made again after printing */}
              {analysisResult.sheet_mismatch && (
                <div className="card" style={{ borderLeft: '4px solid var(--danger)', background: 'var(--danger-bg)', fontSize: '0.8125rem' }} data-testid="sheet-mismatch">
                  <h3 style={{ color: 'var(--danger)', marginBottom: 4 }}>⚠️ <Bi hi="ये शीट आज की वर्कशीट से मेल नहीं खातीं" en="These sheets don't match today's worksheet" inline /></h3>
                  <Bi hi={`रोल ${analysisResult.sheet_mismatch.rolls.join(', ')} की शीट में सवाल ${analysisResult.sheet_mismatch.problems.join(', ')} पर एक जैसी अलग संख्याएँ हैं। क्या शीट छपने के बाद आज की योजना फिर से बनाई गई? आज की वर्कशीट से बनी शीट की फ़ोटो लें।`}
                    en={`The sheets of roll ${analysisResult.sheet_mismatch.rolls.join(', ')} have the same different numbers on question ${analysisResult.sheet_mismatch.problems.join(', ')}. Was today's plan made again after the sheets were printed? Photograph sheets made from today's worksheet.`} />
                </div>
              )}
              {analysisResult.skipped_duplicates?.length > 0 && !keptEarlier && (() => {
                // 16 Nov: tick the children whose NEW photo should count (all ticked), then one button. The AI already read these sheets in this round,
                // so nothing is sent again. (An older saved round without the readings falls back to sending the photos again, one child at a time.)
                const pend = analysisResult.pending || {};
                const canSwap = !!analysisResult.analysis_id && analysisResult.skipped_duplicates.some((d) => pend[String(d.roll_number)]);
                const ticked = analysisResult.skipped_duplicates.map((d) => d.roll_number).filter((r) => pend[String(r)] && !replaceOff.includes(r));
                return (
                  <div className="card" style={{ borderLeft: '4px solid var(--info)', background: 'var(--info-bg)' }} data-testid="dup-skipped">
                    <h3 style={{ marginBottom: 4 }}>⚠️ <Bi hi="आज पहले ही जाँचे जा चुके" en="Already checked today" inline /></h3>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 6 }}>
                      {canSwap ? <Bi hi="पहले का नतीजा रखा गया है। जिनकी नई फ़ोटो गिननी है, उन्हें चुनें:" en="Their earlier results are kept. Tick the children whose new photo should count:" inline />
                        : <Bi hi="इनका पहले का परिणाम रखा गया" en="the earlier result is kept" inline />}
                    </p>
                    {analysisResult.skipped_duplicates.map(d => (
                      <label key={d.roll_number} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', fontSize: '0.8125rem', gap: 8 }}>
                        <span>
                          {canSwap && pend[String(d.roll_number)] && <input type="checkbox" data-testid={`replace-tick-${d.roll_number}`} checked={!replaceOff.includes(d.roll_number)}
                            onChange={() => setReplaceOff((p) => (p.includes(d.roll_number) ? p.filter((x) => x !== d.roll_number) : [...p, d.roll_number]))} style={{ marginRight: 6 }} />}
                          <Bi hi="रोल" en="Roll" inline /> {d.roll_number} · <Bi hi="पहले" en="earlier" inline /> {d.earlier_accuracy == null ? '—' : Math.round(d.earlier_accuracy * 100) + '%'} · {new Date(d.earlier_at).toLocaleTimeString('hi-IN', { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        {!canSwap && photos.length > 0 && <button type="button" className="btn btn-secondary btn-small" style={{ fontSize: '0.8125rem' }} disabled={loading || !online}
                          onClick={() => submitPhotos({ replaceRolls: [d.roll_number] })}><Bi hi="नई फ़ोटो से बदलें" en="Use the new photo" inline /></button>}
                      </label>
                    ))}
                    {canSwap && (
                      <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                        <button type="button" className="btn btn-primary btn-small" data-testid="use-new-photos" disabled={loading || !online || ticked.length === 0} onClick={() => useNewPhotos(ticked)}>
                          <Bi hi={`चुने गए बच्चों की नई फ़ोटो गिनें (${ticked.length})`} en={`Use the new photos for the ticked children (${ticked.length})`} inline />
                        </button>
                        <button type="button" className="btn btn-secondary btn-small" data-testid="keep-earlier" disabled={loading} onClick={() => setKeptEarlier(true)}>
                          <Bi hi="सबके पहले के नतीजे रखें" en="Keep all the earlier results" inline />
                        </button>
                      </div>
                    )}
                  </div>
                );
              })()}
              {(analysisResult.duplicates_in_batch?.length > 0 || analysisResult.unknown_rolls?.length > 0 || analysisResult.outside_group_rolls?.length > 0 ||
                analysisResult.unreadable_sheets > 0 || analysisResult.not_assessed?.length > 0 || analysisResult.retake?.length > 0) && (
                <div className="card" style={{ background: 'var(--info-bg)', fontSize: '0.8125rem' }} data-testid="roll-notices">
                  {analysisResult.duplicates_in_batch?.length > 0 && <div>🔁 <Bi hi="एक ही बच्चे की दो फ़ोटो, साफ़ वाली इस्तेमाल हुई" en="Two photos of the same child, the clearer one was used" inline />: <Bi hi="रोल" en="roll" inline /> {analysisResult.duplicates_in_batch.join(', ')}</div>}
                  {analysisResult.unknown_rolls?.length > 0 && <div>❓ <Bi hi="ये रोल नंबर इस कक्षा में नहीं हैं, गिने नहीं गए" en="Roll number not in this class, skipped" inline />: {analysisResult.unknown_rolls.join(', ')}</div>}
                  {analysisResult.outside_group_rolls?.length > 0 && <div>↔️ <Bi hi="दूसरे समूह की शीट" en="A sheet from another group" inline />: <Bi hi="रोल" en="roll" inline /> {analysisResult.outside_group_rolls.join(', ')}</div>}
                  {analysisResult.unreadable_sheets > 0 && <div>🔍 {analysisResult.unreadable_sheets} <Bi hi="शीट का रोल नंबर पढ़ा नहीं गया, दोबारा फ़ोटो लें" en="Roll number unreadable, please retake" inline /></div>}
                  {(() => {
                    const retake = analysisResult.retake || [], other = (analysisResult.not_assessed || []).filter((r) => !retake.includes(r));
                    return <>
                      {retake.length > 0 && <div data-testid="retake-notice">↺ <Bi hi="बहुत कम सवाल जाँचे जा सके, कोई स्तर दर्ज नहीं हुआ; दोबारा फ़ोटो लें" en="Too few questions could be marked, so no level was saved; photograph again" inline />: <Bi hi="रोल" en="roll" inline /> {retake.join(', ')}</div>}
                      {other.length > 0 && <div>📝 <Bi hi="कुछ आँका नहीं जा सका" en="Could not mark these" inline />: <Bi hi="रोल" en="roll" inline /> {other.join(', ')}</div>}
                    </>;
                  })()}
                </div>
              )}

              {analysisResult.discrepancy && (
                <div className="card" style={{ borderLeft: '4px solid var(--danger)', background: 'var(--danger-bg)' }}>
                  <h3 style={{ color: 'var(--danger)', marginBottom: 4 }}>⚠️ <Bi hi="विसंगति" en="Your decision differs from the evidence" inline /></h3>
                  <p style={{ fontSize: '0.875rem' }}>{analysisResult.discrepancy.reason}</p>
                </div>
              )}

              {analysisResult.misconceptions_detected?.length > 0 && (
                <div className="card">
                  <h3 style={{ marginBottom: 8 }}><Bi hi="पाई गई गलतियाँ" en="Mistakes found" inline /></h3>
                  {analysisResult.misconceptions_detected.map(m => (
                    <div key={m.id} style={{ padding: '6px 0', borderBottom: '1px solid var(--border)', fontSize: '0.875rem' }}>
                      {/* what the mistake means first, the code after it (15 Nov: codes alone meant nothing to a teacher) */}
                      {(analysisResult.misconception_names || {})[m.id]
                        ? <><strong data-testid={`mistake-name-${m.id}`}><Bi hi={analysisResult.misconception_names[m.id].hi} en={analysisResult.misconception_names[m.id].en} inline /></strong> <span style={{ fontFamily: 'monospace', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>({m.id})</span></>
                        : <strong>{m.id}</strong>}
                      {' '}— {m.total_occurrences} <Bi hi="बार" en={m.total_occurrences === 1 ? 'time' : 'times'} inline />
                    </div>
                  ))}
                </div>
              )}

              {(() => {
                // 17 Nov: the cards of EVERY child with a result today (each child's latest), or of this round only; this round's children are marked "new"
                const mode = (on) => ({ flex: 1, minHeight: 36, borderRadius: 8, border: '1px solid var(--border)', fontSize: '0.75rem', fontWeight: 600,
                                        background: on ? 'var(--green-dark)' : 'var(--surface)', color: on ? 'white' : 'var(--text)' });
                return dayKids ? (
                  <div style={{ display: 'flex', gap: 6, margin: '4px 0 8px' }} data-testid="child-view">
                    <button type="button" data-testid="view-day" style={mode(showDayKids)} onClick={() => setChildView('day')}><Bi hi={`आज के सभी बच्चे (${dayKids.length})`} en={`All children today (${dayKids.length})`} inline /></button>
                    <button type="button" data-testid="view-round" style={mode(!showDayKids)} onClick={() => setChildView('round')}><Bi hi={`इस बार (${roundKids.length})`} en={`This round (${roundKids.length})`} inline /></button>
                  </div>
                ) : null;
              })()}
              {cardList.map(c => (
                <div key={c.roll_number} className="card" style={{ padding: 10 }} data-testid={`child-card-${c.roll_number}`}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <strong><Bi hi="रोल" en="Roll" inline /> {c.roll_number}{showDayKids && freshRolls.has(c.roll_number) ? <span className="badge" style={{ marginLeft: 6, fontSize: '0.65rem' }} data-testid={`new-${c.roll_number}`}><Bi hi="नया" en="new" inline /></span> : null}</strong>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      {/* the result of THIS check, in words: one day on a sample says nothing about mastery of the skill */}
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }} data-testid="today-result">
                        <Bi hi={`आज की जाँच में: ${c.status === 'achieved' ? 'प्राप्त' : c.status === 'partially_achieved' ? 'आंशिक' : c.status === 'not_assessed' ? (c.reason === 'too_few_marked' ? 'दोबारा फ़ोटो लें' : 'आँका नहीं गया') : 'प्राप्त नहीं'}`}
                          en={`Today: ${c.status === 'achieved' ? 'Achieved' : c.status === 'partially_achieved' ? 'Partial' : c.status === 'not_assessed' ? (c.reason === 'too_few_marked' ? 'Photograph again' : 'Not marked') : 'Not achieved'}`} inline />
                      </span>
                      {/* a neutral badge with a symbol: a tier colour here would make "NA" look like the Beginner group */}
                      <span className="badge badge-result">
                        {c.status === 'achieved' ? '✓ A' : c.status === 'partially_achieved' ? '~ PA' : c.status === 'not_assessed' ? '—' : '✗ NA'}
                      </span>
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {c.accuracy == null
                      ? (c.reason === 'too_few_marked'
                        ? <span data-testid={`too-few-${c.roll_number}`}><Bi hi={`${c.sheet_points} में से सिर्फ़ ${c.marked_points} सवाल जाँचे जा सके (बाकी अलग उतारे गए), इसलिए कोई स्तर दर्ज नहीं हुआ। आज की वर्कशीट की शीट की दोबारा फ़ोटो लें।`}
                            en={`Only ${c.marked_points} of ${c.sheet_points} questions could be marked (the others were copied wrongly), so no level was saved. Photograph a sheet from today's worksheet again.`} inline /></span>
                        : <Bi hi="आँका नहीं गया" en="Not marked" inline />)
                      : <><Bi hi="शुद्धता" en="Score" inline />: {Math.round(c.accuracy * 100)}%{c.assessed_problems ? <> <Bi hi={`(${c.assessed_problems} में से ${Math.round(c.accuracy * c.assessed_problems)} सही)`} en={`(${Math.round(c.accuracy * c.assessed_problems)} of ${c.assessed_problems} right)`} inline /></> : null}</>}
                    {c.misconceptions?.length > 0 && <> · <Bi hi="गलती" en="Mistake" inline />: {c.misconceptions.map((id) => { const nm = (analysisResult.misconception_names || {})[id]; return nm ? (bi(nm.hi, nm.en) || id) : id; }).join('; ')}</>}
                  </div>
                  {c.copy_errors?.length > 0 && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--info)', marginTop: 4 }} data-testid="copy-errors">
                      ✏️ <Bi hi="अलग उतारा, गिना नहीं गया" en="Copied wrongly from the sheet, not marked" inline />:{' '}
                      <Bi hi={c.copy_errors.map(e => `#${e.problem}${e.written ? ` लिखा ${e.written}` : ''} → ${e.answer}${e.correct_for_written === true ? ' ✓ (उस सवाल के लिए सही)' : e.correct_for_written === false ? ' ✗' : ''}`).join(' · ')}
                        en={c.copy_errors.map(e => `#${e.problem}${e.written ? ` written ${e.written}` : ''} → ${e.answer}${e.correct_for_written === true ? ' ✓ (right for the sum written)' : e.correct_for_written === false ? ' ✗' : ''}`).join(' · ')} inline />
                    </div>
                  )}
                  {c.needs_check?.length > 0 && (
                    <div style={{ fontSize: '0.75rem', color: '#555', marginTop: 4 }} data-testid="needs-check">
                      👀 <Bi hi="नोटबुक में जाँचें" en="Check in the notebook" inline />: <Bi hi="सवाल" en="question" inline /> {c.needs_check.join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <p className="hi">फ़ोटो विश्लेषण के बाद परिणाम यहाँ दिखेंगे</p>
              <p className="en" lang="en" style={{ fontSize: '0.8rem', marginTop: 4 }}>Results will appear after photo analysis</p>
            </div>
          )}

          {fromPlan ? (
            <button type="button" className="btn btn-primary" data-testid="done-in-class" onClick={backToPlan} style={{ marginTop: 16, marginBottom: 80, flexDirection: 'column', gap: 0 }}>
              <Bi hi="← पढ़ाना जारी रखें (योजना पर लौटें)" en="Back to today's plan" />
            </button>
          ) : (<>
          <button type="button" className="btn btn-secondary" data-testid="back-to-work" onClick={() => goView('2')} style={{ marginTop: 16, flexDirection: 'column', gap: 0 }}>
            <Bi hi="← आज का प्रदर्शन: अगला समूह" en="Back to the groups (next group)" />
          </button>
          <button type="button" className="btn btn-primary" data-testid="to-final" onClick={enterFinal} style={{ marginTop: 8, marginBottom: 80, flexDirection: 'column', gap: 0 }}>
            <Bi hi="आगे: अगली कक्षा में क्या पढ़ाएँ, तय करें →" en="Next: decide for the next class →" />
          </button>
          </>)}
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
            <button type="button" className="btn btn-secondary btn-small" data-testid="final-back" onClick={() => goView('2')} style={{ marginBottom: 8 }}>
              ← <span className="step-count">1/2</span>: <Bi hi="आज का प्रदर्शन" en="Today's performance" inline />
            </button>
            <StepTitle n={3} hi="अंतिम निर्णय: अगली कक्षा में क्या पढ़ाएँ?" en="Next class: what to teach?" />
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
              <Bi hi="आज का प्रदर्शन देखकर हर समूह के लिए तय करें: अगली कक्षा में आगे बढ़ें, दोबारा पढ़ाएँ, या पक्का नहीं। अगली कक्षा की योजना बनाते समय ऐप इन्हीं के आधार पर सुझाव देगा।"
                en="With today's performance in front of you, decide for each group: move on, teach again, or not sure. When you plan the next class, the app suggests based on these." />
            </p>
            {needed.map((g) => {
              const ev = (evidence && evidence[g.label]) || {};
              const fin = finals[g.label];
              const L = GROUP_LABELS[g.label] || {};
              return (
                <div key={g.label} className={`card tier-card tier-${g.label}`} data-testid={`final-${g.label}`}>
                  <div className="card-header">
                    <div><span className={`badge badge-${g.label}`}><Bi hi={L.hi} en={L.en} inline /></span></div>
                  </div>
                  <SkillLine level={g.label} skillId={g.target_competency_id} name={g.target_competency_name_hi} nameEn={g.target_competency_name_en} withGroup={false} testid={`skill-3-${g.label}`} />
                  <div style={{ fontSize: '0.8125rem', marginTop: 2 }} data-testid={`final-evidence-${g.label}`}>
                    <Bi hi="आज का प्रदर्शन" en="Today's performance" inline />:{' '}
                    {!evidence || typeof ev.assessed !== 'number'
                      ? <span data-testid={`final-evidence-unknown-${g.label}`} style={{ color: 'var(--info)' }}><Bi hi="अभी नहीं दिख रही; पेज दोबारा खोलें" en="cannot be shown right now; reopen the page" inline /></span>
                      : ev.assessed > 0
                        ? <>✓ A {ev.a} · ~ PA {ev.pa} · ✗ NA {ev.na} <span style={{ color: 'var(--text-secondary)' }}>(<span className="hi">{ev.group_size} में से {ev.assessed} बच्चों का आकलन</span><span className="en en-inline" lang="en">{ev.assessed} of {ev.group_size} assessed</span>)</span></>
                        : <span style={{ color: 'var(--text-secondary)' }}><Bi hi="अभी किसी का आकलन नहीं" en="nobody assessed yet" inline /></span>}
                  </div>
                  {ev.recommend && (
                    <div data-testid={`final-suggest-${g.label}`} style={{ fontSize: '0.8125rem', color: 'var(--info)', fontWeight: 600, marginTop: 2 }}>
                      <Bi hi="सुझाव: 🔄 दोहराएँ (जाँचे गए बच्चों में से एक-तिहाई या ज़्यादा से गलती हुई; कम से कम 4 बच्चों की जाँच)" en="Suggested: teach again (a third or more of the children checked made a mistake; at least 4 checked)" inline />
                    </div>
                  )}
                  {!ev.recommend && ev.very_small && (
                    <div data-testid={`final-too-few-${g.label}`} style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                      <Bi hi="बहुत कम बच्चे जाँचे गए; ऐप कोई सुझाव नहीं देता।" en="Too few children checked for a suggestion." inline />
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
                </div>
              );
            })}
            <AbbrKey testid="abbr-final" />
            {undecidedFinal.length > 0 && (
              <p data-testid="finals-left" style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '8px 0 0' }}>
                <Bi hi={`हर समूह के लिए अंतिम निर्णय चुनें (बाकी: ${undecidedFinal.map((g) => `${GROUP_LABELS[g.label]?.mark || ''} ${GROUP_LABELS[g.label]?.hi || g.label}`.trim()).join(', ')})`}
                  en={`Choose a final decision for each group (left: ${undecidedFinal.map((g) => GROUP_LABELS[g.label]?.en || g.label).join(', ')})`} />
              </p>
            )}
            {finalDone ? (
              <div className="saved-block" data-testid="final-saved" role="status" style={{ marginTop: 10, borderLeftColor: 'var(--green-dark)', background: 'var(--green-bg)' }}>
                <div style={{ fontWeight: 600 }}><Bi hi="✓ निर्णय दर्ज हुए। अगली कक्षा की योजना बनाते समय ऐप इन्हीं के आधार पर सुझाव देगा।" en="Saved. When you plan the next class, the app suggests based on these." /></div>
              </div>
            ) : (
              <button className="btn btn-primary" data-testid="record-final" onClick={saveFinal} disabled={loading || undecidedFinal.length > 0} style={{ marginTop: 8, flexDirection: 'column', gap: 0 }}>
                {loading ? <Bi hi="दर्ज हो रहा..." en="Recording" /> : <Bi hi="निर्णय दर्ज करें" en="Save decisions" />}
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
