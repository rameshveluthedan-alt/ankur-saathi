import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { getReviewChannels } from '../services/api';
import { GROUP_LABELS, GROUP_ORDER } from '../tiers';
import { localToday } from '../services/today';
import { CHANNELS } from '../services/reviewWays';
import { hiDate, classLine } from '../services/printFormat';

/**
 * The paper tick sheet: for a teacher who records during You Do without her phone, then enters the marks in the Review's step 2 after class.
 * One table per group checked by observing (रोल | A | PA | NA, a box to tick) or by reading aloud (रोल | सही शब्द | गलतियाँ, a box to write in);
 * photo groups get none (their evidence is the worksheet itself). A long table runs on to the next page; its column row, with the group's mark, repeats there. Hindi only, roll numbers but never a name (as the printed plan).
 * The groups and their rolls are the server's review ways for today's plan; with the ways unknown there is no sheet (never a guess).
 */
const KEY = CHANNELS.find((c) => c.id === 'observed').how[1].hi;        // "A = करके दिखाया, बिना मदद · PA = …": the Review's own meanings
const ERRORS = 'गलती = गलत शब्द, छूटा शब्द, या जो शब्द आपको बताना पड़ा';
// (called once the ways are known: with no stored plan the page has already said so)
export const tickLevels = (ways) => ((ways && ways.levels) || [])
  .filter((l) => (l.channel === 'observed' || l.channel === 'orf') && GROUP_LABELS[l.level] && (l.rolls || []).length)
  .sort((a, b) => GROUP_ORDER.indexOf(a.level) - GROUP_ORDER.indexOf(b.level));

function Group({ l }) {
  const L = GROUP_LABELS[l.level];
  const reading = l.channel === 'orf';
  const cols = reading ? ['सही शब्द', 'गलतियाँ'] : ['A', 'PA', 'NA'];
  return (
    <section className={`tick-group tier-${l.level}`} data-testid={`tick-group-${l.level}`} data-channel={l.channel}>
      <div className="print-block-head" data-testid="tick-head">
        {L.mark} {L.hi} · {l.competency_id}{l.name_hi ? ` ${l.name_hi}` : ''} · {reading ? '⏱️ पढ़कर सुनाना' : '✓ देखकर दर्ज करें'}
      </div>
      {reading && (
        <div data-testid="tick-passage">
          {l.passage ? <>पाठ: «{l.passage.title}» ({l.passage.word_count} शब्द) · एक मिनट</> : 'पाठ: अपनी कक्षा के स्तर का ऐसा पाठ जो बच्चों ने आज नहीं पढ़ा · एक मिनट'}
        </div>
      )}
      <div style={{ fontSize: '9pt' }} data-testid="tick-key">{reading ? ERRORS : KEY}</div>
      <table className="tick-table">
        <thead><tr><th>{L.mark} रोल</th>{cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>
          {[...l.rolls].sort((a, b) => a - b).map((r) => (
            <tr key={r} data-testid={`tick-row-${l.level}-${r}`}><td>{r}</td>{cols.map((c) => <td key={c} />)}</tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export default function TickSheet() {
  const { currentPlan, teacher, selectedDomain } = useAuth();
  const navigate = useNavigate();
  const date = (currentPlan && currentPlan.plan_date) || localToday();
  const domain = (currentPlan && currentPlan.domain_id) || selectedDomain;
  const [ways, setWays] = useState(undefined);        // undefined: loading; null: could not load

  useEffect(() => {
    let cancelled = false;
    getReviewChannels(teacher.teacher_id, date, domain).then((w) => { if (!cancelled) setWays(w); }).catch(() => { if (!cancelled) setWays(null); });
    return () => { cancelled = true; };
  }, [date, domain]);
  // printing shows this page alone (no banner, no bottom bar): the printed plan's own rule, "body.print-plan" in index.css
  useEffect(() => { document.body.classList.add('print-plan'); return () => document.body.classList.remove('print-plan'); }, []);

  const levels = tickLevels(ways);
  const bar = (
    <div className="no-print" style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
      <button type="button" className="btn btn-secondary btn-small" data-testid="ticks-back" onClick={() => navigate('/yojana')}>← वापस</button>
      {levels.length > 0 && <button type="button" className="btn btn-primary btn-small" data-testid="ticks-print" onClick={() => window.print()}>🖨️ प्रिंट करें</button>}
    </div>
  );
  if (ways === undefined) return <div className="screen">{bar}<div className="loading"><div className="spinner" /></div></div>;
  if (!ways || !ways.has_plan) return <div className="screen">{bar}<p data-testid="ticks-unknown">आज की योजना के समूह नहीं मिले; टिक शीट योजना बनने के बाद बनेगी।</p></div>;
  if (!levels.length) return <div className="screen">{bar}<p data-testid="ticks-none">आज कोई समूह देखकर या पढ़कर सुनाकर नहीं जाँचा जाता; टिक शीट की ज़रूरत नहीं।</p></div>;

  const code = teacher.employee_code || teacher.school_code || '';
  return (
    <div className="screen plan-print tick-sheet" data-testid="tick-sheet">
      {bar}
      <div className="print-title" data-testid="ticks-title">{['टिक शीट', code, classLine(teacher.enrolled_grades), hiDate(date)].filter(Boolean).join(' · ')}</div>
      <div data-testid="ticks-when">स्वतंत्र अभ्यास (तुम करोगे) के दौरान भरें; पढ़ाने के बाद समीक्षा के चरण 2 में यही दर्ज करें।</div>
      <hr />
      {levels.map((l) => <Group key={l.level} l={l} />)}
      <hr />
      <div className="print-footer" data-testid="ticks-footer">🌱 अंकुर साथी · {date} · सिर्फ़ रोल नंबर, कोई नाम नहीं</div>
    </div>
  );
}
