import React, { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { fetchAuthedPage } from '../services/api';
import { friendlyError } from '../services/errors';
import Bi from '../components/Bi';

/**
 * A server page (today: a group's worksheet) shown inside the app, with ← Back and 🖨️ Print at the top.
 * Opened with navigate('/page', { state: { path, title: {hi, en}, back } }). The page is the server's own printable A4 HTML, put in a frame:
 * no pop-up tab (blocked or lost on a desktop browser, found by the hackathon evaluators on 12 Nov), and the service worker's saved copy works offline.
 */
export default function PageViewer() {
  const { state } = useLocation();
  const navigate = useNavigate();
  const frame = useRef(null);
  const [html, setHtml] = useState(null);
  const [error, setError] = useState(null);
  const [height, setHeight] = useState(1200);
  const path = state && state.path;
  const back = (state && state.back) || '/yojana';

  useEffect(() => {
    if (!path) return undefined;
    let cancelled = false;
    setHtml(null); setError(null);
    fetchAuthedPage(path).then((t) => { if (!cancelled) setHtml(t); })
      .catch((e) => { if (!cancelled) setError(friendlyError(e, { hi: 'पेज नहीं खुल सका', en: 'The page could not be opened' })); });
    return () => { cancelled = true; };
  }, [path]);

  const fit = () => {          // the frame as tall as its page, so the app scrolls once (not a frame inside a page)
    try { const d = frame.current.contentDocument; if (d && d.documentElement) setHeight(d.documentElement.scrollHeight + 16); } catch { /* keep the default */ }
  };
  const print = () => {
    try { frame.current.contentWindow.focus(); frame.current.contentWindow.print(); } catch { window.print(); }
  };

  return (
    <div className="page-viewer" data-testid="page-viewer">
      <div className="page-viewer-bar no-print">
        <button type="button" className="btn btn-secondary btn-small" data-testid="page-back" onClick={() => navigate(back)}>← <Bi hi="वापस" en="Back" inline /></button>
        <strong style={{ flex: 1, fontSize: '0.875rem', minWidth: 0 }}>{state && state.title ? <Bi hi={state.title.hi} en={state.title.en} inline /> : null}</strong>
        {html && <button type="button" className="btn btn-primary btn-small" data-testid="page-print" onClick={print}>🖨️ <Bi hi="प्रिंट" en="Print" inline /></button>}
      </div>
      {!path && <p style={{ padding: 16 }}><Bi hi="कोई पेज नहीं चुना गया।" en="No page was chosen." /></p>}
      {path && !html && !error && <div className="loading"><div className="spinner" /><span><Bi hi="खुल रहा है…" en="Opening" inline /></span></div>}
      {error && <p className="note note-error" role="alert" data-testid="page-error" style={{ margin: 16 }}>{error}</p>}
      {html && <iframe ref={frame} title="page" data-testid="page-frame" srcDoc={html.replace('</head>', '<style>.print-bar{display:none!important}</style></head>')} onLoad={fit} style={{ width: '100%', height, border: 'none', background: 'white', display: 'block' }} />}
    </div>
  );
}
