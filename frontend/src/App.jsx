import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import {
  UploadCloud, FileAudio, CheckCircle2, Circle, Loader2,
  Download, AlertCircle, ListChecks, Target, AlignLeft,
  Cpu, Users, Calendar, RefreshCcw, Sparkles, Info
} from 'lucide-react';
import './index.css';

const API_BASE = 'http://127.0.0.1:8000/api';

/* ─────────────────────────── helpers ───────────────────────────── */
const PIPELINE_STEPS = [
  { id: 'transcribing',  label: 'Transcribing audio',        detail: 'Whisper ASR' },
  { id: 'preprocessing', label: 'Cleaning & merging turns',   detail: 'Preprocessing' },
  { id: 'summarizing',   label: 'Generating summary',         detail: 'DistilBART' },
  { id: 'extracting',    label: 'Extracting actions & decisions', detail: 'Rule-based NLP' },
];

function stepIndex(id) {
  return PIPELINE_STEPS.findIndex(s => s.id === id);
}

function ConfBar({ value }) {
  const pct = Math.round((value || 0) * 100);
  const color = pct >= 70 ? 'var(--success)' : pct >= 45 ? 'var(--warning)' : 'var(--danger)';
  return (
    <div className="conf-bar-wrap">
      <div className="conf-bar">
        <div className="conf-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="conf-label">{pct}%</span>
    </div>
  );
}

/* ─────────────────────────── UPLOAD ────────────────────────────── */
function UploadPanel({ onSubmit }) {
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState('');
  const inputRef = useRef(null);

  const accept = "video/mp4,video/quicktime,video/x-matroska,video/webm,audio/*";

  function pickFile(f) {
    if (f) { setFile(f); setErr(''); }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setErr('');
    try {
      const fd = new FormData();
      fd.append('video', file);
      const res = await axios.post(`${API_BASE}/process`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      onSubmit(res.data.job_id);
    } catch (ex) {
      setErr(ex.response?.data?.detail || 'Upload failed. Is the backend running?');
      setUploading(false);
    }
  }

  return (
    <div className="upload-wrapper">
      <div className="card">
        <form onSubmit={handleSubmit}>
          <div
            id="dropzone"
            className={`dropzone${dragOver ? ' drag-over' : ''}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={e => { e.preventDefault(); setDragOver(false); pickFile(e.dataTransfer.files[0]); }}
          >
            <input
              type="file"
              ref={inputRef}
              style={{ display: 'none' }}
              accept={accept}
              onChange={e => pickFile(e.target.files[0])}
            />
            <div className="dropzone-icon">
              {file ? <FileAudio size={26} /> : <UploadCloud size={26} />}
            </div>
            <div className="dropzone-title">
              {file ? file.name : 'Drop your meeting recording here'}
            </div>
            <div className="dropzone-sub">
              {file
                ? `${(file.size / (1024 * 1024)).toFixed(2)} MB — click to change`
                : 'MP4, MOV, MKV, WAV, MP3 · up to 2 GB'}
            </div>
            {file && (
              <div className="file-selected">
                <CheckCircle2 size={14} /> File ready
              </div>
            )}
          </div>

          {err && (
            <div className="error-banner" style={{ marginTop: '1rem', marginBottom: 0 }}>
              <AlertCircle size={18} />
              <p>{err}</p>
            </div>
          )}

          <button
            id="process-btn"
            type="submit"
            className="btn btn-full"
            style={{ marginTop: '1.5rem' }}
            disabled={!file || uploading}
          >
            {uploading ? (
              <><span className="spinner-sm" /> Uploading…</>
            ) : (
              <><Sparkles size={16} /> Generate Meeting Minutes</>
            )}
          </button>
        </form>
      </div>

      <p style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        Powered by Whisper · DistilBART · DistilBERT
      </p>
    </div>
  );
}

/* ─────────────────────────── PROCESSING ─────────────────────────── */
function ProcessingScreen({ jobId, onComplete, onError }) {
  const [currentStep, setCurrentStep] = useState('');

  useEffect(() => {
    const iv = setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE}/process/${jobId}`);
        setCurrentStep(res.data.step || '');
        if (res.data.status === 'completed') {
          clearInterval(iv);
          onComplete(res.data.results);
        } else if (res.data.status === 'failed') {
          clearInterval(iv);
          onError(res.data.error || 'Pipeline failed.');
        }
      } catch (ex) {
        if (ex.response?.status !== 404) console.error(ex);
      }
    }, 2500);
    return () => clearInterval(iv);
  }, [jobId]);

  const activeIdx = stepIndex(currentStep);

  return (
    <div className="processing-screen">
      <div className="card">
        <div className="orbit" />
        <h2>Analysing your meeting</h2>
        <p>This may take a few minutes for long recordings.</p>

        <ul className="pipeline-steps">
          {PIPELINE_STEPS.map((s, i) => {
            const done   = i < activeIdx || (activeIdx === -1 && i < PIPELINE_STEPS.length);
            const active = i === activeIdx;
            return (
              <li key={s.id} className={`pipeline-step${active ? ' active' : done ? ' done' : ''}`}>
                <div className="step-dot">
                  {done   && <CheckCircle2 size={12} />}
                  {active && <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} />}
                </div>
                <div>
                  <div>{s.label}</div>
                  <div style={{ fontSize: '0.72rem', opacity: 0.6 }}>{s.detail}</div>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}

/* ─────────────────────────── RESULTS ────────────────────────────── */
function ResultsPanel({ results, jobId, onReset }) {
  const { metadata, pipeline_info, summary, key_points, decisions, action_items, follow_ups, transcript } = results;

  const download = (fmt) => window.open(`${API_BASE}/download/${jobId}/${fmt}`, '_blank');

  return (
    <div>
      {/* Results header */}
      <div className="results-header">
        <div>
          <h2>Meeting Minutes</h2>
          <div className="meta-pills">
            {metadata?.title && metadata.title !== 'Not specified' && (
              <span className="meta-pill"><FileAudio size={12} />{metadata.title}</span>
            )}
            {metadata?.date && metadata.date !== 'Not specified' && (
              <span className="meta-pill"><Calendar size={12} />{metadata.date}</span>
            )}
            {metadata?.participants?.length > 0 && (
              <span className="meta-pill">
                <Users size={12} />{metadata.participants.join(', ')}
              </span>
            )}
          </div>
        </div>
        <div className="results-actions">
          <button id="dl-md"   className="btn btn-ghost btn-sm" onClick={() => download('md')}>
            <Download size={14} /> Minutes
          </button>
          <button id="dl-txt"  className="btn btn-ghost btn-sm" onClick={() => download('txt')}>
            <Download size={14} /> Transcript
          </button>
          <button id="dl-json" className="btn btn-ghost btn-sm" onClick={() => download('json')}>
            <Download size={14} /> JSON
          </button>
          <button id="reset-btn" className="btn btn-sm" onClick={onReset}>
            <RefreshCcw size={14} /> New File
          </button>
        </div>
      </div>

      <div className="grid-2col">
        {/* ── Left column ── */}
        <div className="stack">

          {/* Summary */}
          <div className="card">
            <div className="sec-header">
              <AlignLeft size={17} />
              <h3>Executive Summary</h3>
            </div>
            {summary ? (
              <p className="summary-text">{summary}</p>
            ) : (
              <p className="summary-text" style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                No summary could be generated.
              </p>
            )}

            {key_points?.length > 0 && (
              <>
                <div style={{ margin: '1.25rem 0 0.5rem', fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Key Points
                </div>
                <ul className="key-points">
                  {key_points.map((pt, i) => <li key={i}>{pt}</li>)}
                </ul>
              </>
            )}
          </div>

          {/* Decisions */}
          <div className="card">
            <div className="sec-header">
              <Target size={17} />
              <h3>Decisions</h3>
              {decisions?.length > 0 && <span className="count">{decisions.length}</span>}
            </div>
            {decisions?.length > 0 ? (
              <ul className="decision-list">
                {decisions.map((d, i) => (
                  <li key={i} className="decision-item">
                    {d.text}
                    <ConfBar value={d.confidence} />
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-state">
                <Target size={28} />
                <p>No confirmed decisions detected in this recording.</p>
              </div>
            )}
          </div>

          {/* Pipeline info */}
          {pipeline_info && (
            <div className="card" style={{ padding: '1rem 1.25rem' }}>
              <div className="sec-header" style={{ marginBottom: '0.6rem' }}>
                <Cpu size={15} /><h3>Pipeline Info</h3>
              </div>
              <div className="pipeline-info">
                <strong>ASR:</strong> {pipeline_info.transcription_model}<br />
                <strong>Summarization:</strong> {pipeline_info.summarization_model}<br />
                <strong>Speaker diarization:</strong> {pipeline_info.speaker_diarization ? 'Yes' : 'No'}<br />
                <span style={{ opacity: 0.8 }}>{pipeline_info.note}</span>
              </div>
            </div>
          )}
        </div>

        {/* ── Right column ── */}
        <div className="stack">

          {/* Action Items */}
          <div className="card">
            <div className="sec-header">
              <ListChecks size={17} />
              <h3>Action Items</h3>
              {action_items?.length > 0 && <span className="count">{action_items.length}</span>}
            </div>
            {action_items?.length > 0 ? (
              <div className="action-table-wrap">
                <table className="action-table">
                  <thead>
                    <tr>
                      <th style={{ width: '55%' }}>Task</th>
                      <th>Owner</th>
                      <th>Deadline</th>
                    </tr>
                  </thead>
                  <tbody>
                    {action_items.map((a, i) => (
                      <tr key={i}>
                        <td>
                          {a.text}
                          <ConfBar value={a.confidence} />
                        </td>
                        <td>
                          {a.owner
                            ? <span className="tag tag-owner"><Users size={10} />{a.owner}</span>
                            : <span className="tag tag-none">Not identified</span>}
                        </td>
                        <td>
                          {a.deadline
                            ? <span className="tag tag-date"><Calendar size={10} />{a.deadline}</span>
                            : <span className="tag tag-none">Not specified</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state">
                <ListChecks size={28} />
                <p>No confirmed action items detected in this recording.</p>
              </div>
            )}
          </div>

          {/* Follow-ups */}
          {follow_ups?.length > 0 && (
            <div className="card">
              <div className="sec-header">
                <Info size={17} />
                <h3>Follow-ups & Open Items</h3>
                <span className="count">{follow_ups.length}</span>
              </div>
              <ul className="key-points">
                {follow_ups.map((f, i) => <li key={i}>{f.text}</li>)}
              </ul>
            </div>
          )}

          {/* Transcript */}
          <div className="card">
            <div className="sec-header">
              <AlignLeft size={17} />
              <h3>Full Transcript</h3>
            </div>
            <div className="transcript-box" id="transcript-box">
              {transcript
                ? transcript.split('\n').map((line, i) => (
                    <div key={i} className="transcript-line">{line || '\u00A0'}</div>
                  ))
                : <span style={{ color: 'var(--text-muted)' }}>No transcript available.</span>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────── APP ROOT ───────────────────────────── */
export default function App() {
  const [phase, setPhase]     = useState('upload'); // upload | processing | results | error
  const [jobId, setJobId]     = useState(null);
  const [results, setResults] = useState(null);
  const [errMsg, setErrMsg]   = useState('');

  function handleUpload(id) {
    setJobId(id);
    setPhase('processing');
  }
  function handleComplete(res) {
    setResults(res);
    setPhase('results');
  }
  function handleError(msg) {
    setErrMsg(msg);
    setPhase('error');
  }
  function handleReset() {
    setJobId(null);
    setResults(null);
    setErrMsg('');
    setPhase('upload');
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-badge">
          <Cpu size={12} /> Team 14 — Text Generation &amp; Summarization
        </div>
        <h1>Automated Meeting Minutes</h1>
        <p>
          Upload a meeting recording and our NLP pipeline will transcribe, summarize,
          identify decisions and extract action items automatically.
        </p>
      </header>

      {phase === 'error' && (
        <div className="error-banner">
          <AlertCircle size={20} />
          <p>{errMsg}</p>
          <button className="btn btn-sm" onClick={handleReset} style={{ marginLeft: 'auto' }}>
            <RefreshCcw size={14} /> Try Again
          </button>
        </div>
      )}

      {phase === 'upload'     && <UploadPanel onSubmit={handleUpload} />}
      {phase === 'processing' && (
        <ProcessingScreen
          jobId={jobId}
          onComplete={handleComplete}
          onError={handleError}
        />
      )}
      {phase === 'results' && results && (
        <ResultsPanel results={results} jobId={jobId} onReset={handleReset} />
      )}
    </div>
  );
}
