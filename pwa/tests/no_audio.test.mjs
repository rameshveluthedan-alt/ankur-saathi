// The app records NO audio, and its screens must not suggest it does.
//
// Why this test exists: the reading-aloud form (words per minute, entered by the teacher after timing one child) was marked with a microphone, so an evaluator would expect voice recording.
// Assessing by voice in a class where several groups are at work is too noisy to be clear, so the daily review is by observation, and recording is planned only for the periodic assessments,
// in a quiet one-to-one moment (docs/ROADMAP.md). Until then this is a promise made in docs/PRIVACY.md and docs/STATUS.md, so it is checked in the code, like the rule that names never reach the AI.
//
//     cd pwa
//     node tests/no_audio.test.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const files = [];
(function walk(d) { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); e.isDirectory() ? walk(p) : /\.(jsx?|html|css)$/.test(e.name) && files.push(p); } })(src);
const read = (f) => fs.readFileSync(f, 'utf8');
const all = files.map((f) => [path.relative(path.join(here, '..'), f).replace(/\\/g, '/'), read(f)]);

let n = 0;
const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('the code cannot record sound');
const capture = /getUserMedia|MediaRecorder|AudioContext|webkitAudioContext|SpeechRecognition|webkitSpeechRecognition|enumerateDevices|mediaDevices/;
const hits = all.filter(([, t]) => capture.test(t)).map(([f]) => f);
check(`none of the ${files.length} source files asks for the microphone or records or recognises speech`, hits.length === 0, hits.join(', '));
check('the page never asks the browser for the microphone permission (index.html and the manifest)', !/microphone|audio/i.test(read(path.join(here, '..', 'index.html'))) && !/microphone/i.test(read(path.join(here, '..', 'vite.config.js'))));

console.log('\nthe screens do not suggest it');
const mic = all.filter(([, t]) => t.includes('🎤')).map(([f]) => f);
check('no screen uses a microphone symbol (it used to mark the reading-aloud form, the tab and the skill list)', mic.length === 0, mic.join(', '));
const review = all.find(([f]) => f.endsWith('screens/ReviewScreen.jsx'))[1];
check('the reading-aloud form says, in Hindi and in English, that no audio is recorded', review.includes('कोई आवाज़ रिकॉर्ड नहीं होती') && review.includes('No audio is recorded'));
check('...and says what the teacher does: listen to one child for a minute, then enter the words and the errors', review.includes('एक बच्चे को एक मिनट पढ़ते सुनें') && /Listen to one child read for a minute/.test(review));
check('the button says it saves a reading score, not that it records', review.includes('पठन दर्ज करें') && review.includes('Save reading score') && !/Record ORF/.test(review));
const plan = all.find(([f]) => f.endsWith('screens/PlanScreen.jsx'))[1];
check('the skill list marks a reading-aloud skill with a stopwatch', plan.includes("'oral_reading' ? '⏱️'"));

console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: the app has no way to record sound, and nothing on screen says it does'}`);
