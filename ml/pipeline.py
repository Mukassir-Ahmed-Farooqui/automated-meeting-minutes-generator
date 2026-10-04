"""
Clean Python API for the ML pipeline.
Exposes a simple run_pipeline function to be used by FastAPI.
"""
from __future__ import annotations

import logging
import uuid
from typing import Dict, Any, Optional

from ml.asr import WhisperASR
from ml.chunking import chunk_turns
from ml.classifier import SentenceClassifier
from ml.config import load_config
from ml.data_loader import load_transcript_file
from ml.extraction import extract_actions, extract_decisions, extract_followups
from ml.preprocessing import clean_text, merge_short_turns, turn_sentences
from ml.summarizer import HierarchicalSummarizer
from ml.utils import select_models, set_seed

log = logging.getLogger("pipeline")


def _merge_continuation_turns(turns: list) -> list:
    """Merge turns that are sentence continuations.

    Whisper often splits a single continuous sentence across multiple 'turns'.
    We detect these by checking:
      - Same speaker as the previous turn, AND
      - Previous turn ends without terminal punctuation, OR current turn starts lowercase.

    This significantly reduces fragmented sentences that confuse the extractor.
    """
    merged: list = []
    for t in turns:
        if not t.text.strip():
            continue
        if merged and merged[-1].speaker == t.speaker:
            prev_text = merged[-1].text.strip()
            current_text = t.text.strip()
            is_continuation = (
                (prev_text and prev_text[-1] not in ".!?") or
                (current_text and current_text[0].islower())
            )
            if is_continuation:
                merged[-1].text = f"{prev_text} {current_text}"
                # Extend the end timestamp
                if hasattr(t, "end") and t.end is not None:
                    merged[-1].end = t.end
                continue
        merged.append(t)
    return merged


def _format_turn(t) -> str:
    """Format a turn for display, hiding unhelpful 'Unknown' speaker labels."""
    speaker = (t.speaker or "").strip()
    if not speaker or speaker.lower() in {"unknown", "none", "speaker"}:
        return t.text
    return f"{speaker}: {t.text}"


def run_pipeline(
    input_path: str,
    title: Optional[str] = None,
    date: Optional[str] = None,
    participants: Optional[str] = None,
    meeting_id: Optional[str] = None,
    status_callback: Optional[callable] = None,
) -> Dict[str, Any]:
    """
    Run the end-to-end ML pipeline on an audio/video file or transcript.
    Returns structured JSON results.
    """
    cfg = load_config()
    set_seed(cfg.seed)
    chosen = select_models(cfg)
    meeting_id = meeting_id or str(uuid.uuid4())

    if status_callback:
        status_callback("transcribing")

    # 1. ASR or Transcript Loading
    speaker_diarization = False
    if input_path.endswith((".txt", ".json")):
        meeting = load_transcript_file(input_path, meeting_id=meeting_id)
        if title:
            meeting["title"] = title
        if date:
            meeting["date"] = date
        if participants:
            meeting["participants"] = [p.strip() for p in participants.split(",")]
        # Check if the transcript has real speaker labels (not just 'Unknown')
        raw_speakers = {t.speaker for t in meeting.get("turns", [])}
        speaker_diarization = bool(raw_speakers - {"Unknown", "Speaker", ""})
    else:
        log.info(f"Running ASR on {input_path}")
        asr = WhisperASR(chosen["whisper"], device=chosen["device"])
        from ml.asr import transcript_to_turns
        result = asr.transcribe(input_path)
        meeting = {
            "meeting_id": meeting_id,
            "title": title or "Not specified",
            "date": date or "Not specified",
            "participants": [p.strip() for p in participants.split(",")] if participants else [],
            "turns": transcript_to_turns(result),
            "raw_text": result.get("text", ""),
        }

    if not meeting.get("turns"):
        return {"error": "No speech detected or empty transcript."}

    if status_callback:
        status_callback("preprocessing")

    # 2. Preprocessing — clean text, then smart-merge continuation fragments
    for t in meeting["turns"]:
        t.text = clean_text(t.text)
    turns = _merge_continuation_turns(meeting["turns"])
    turns = merge_short_turns(turns)

    if status_callback:
        status_callback("summarizing")

    # 3. Chunking & Summarization
    chunks = chunk_turns(turns, max_tokens=1024 - 50, overlap_turns=1)
    summarizer = HierarchicalSummarizer(chosen["summarization"], device=chosen["device"])

    try:
        summary_result = summarizer.summarize_meeting(chunks, meeting_id=meeting["meeting_id"])
        final_summary = summary_result.get("final_summary", "")
        key_points = summary_result.get("key_points", [])
    except Exception as e:
        log.error(f"Summarization failed: {e}")
        final_summary = ""
        key_points = []

    if status_callback:
        status_callback("extracting")

    # 4. Classification & Extraction
    sents = turn_sentences(turns, meeting_id=meeting["meeting_id"])
    classifier = SentenceClassifier(chosen["classifier"], device=chosen["device"])
    analyzed = classifier.analyze(sents)

    decisions = extract_decisions(analyzed)
    actions = extract_actions(analyzed, participants=meeting.get("participants", []))
    followups = extract_followups(analyzed)

    # 5. Build clean transcript lines (hide uninformative "Unknown" labels)
    transcript_lines = [_format_turn(t) for t in turns if t.text.strip()]

    # 6. Package and return results
    return {
        "metadata": {
            "meeting_id": meeting["meeting_id"],
            "title": meeting.get("title", "Not specified"),
            "date": meeting.get("date", "Not specified"),
            "participants": meeting.get("participants", []),
        },
        "pipeline_info": {
            "transcription_model": f"Whisper ({chosen.get('whisper', 'small')})",
            "summarization_model": "sshleifer/distilbart-cnn-12-6",
            "speaker_diarization": speaker_diarization,
            "note": (
                "Speaker identification is not available. All speech is attributed to a single channel."
                if not speaker_diarization
                else "Speaker identification was applied to this transcript."
            ),
        },
        "transcript": "\n".join(transcript_lines),
        "summary": final_summary,
        "key_points": key_points,
        "decisions": [
            {
                "text": d.get("text", ""),
                "confidence": float(d.get("confidence", 0.0)),
            }
            for d in decisions
        ],
        "action_items": [
            {
                "text": a.get("action", a.get("text", "")),
                "owner": a.get("owner") if (a.get("owner") and a["owner"] != "Not specified") else None,
                "deadline": a.get("deadline") if (a.get("deadline") and a["deadline"] != "Not specified") else None,
                "confidence": float(a.get("confidence", 0.0)),
            }
            for a in actions
        ],
        "follow_ups": [{"text": f.get("text", "")} for f in followups],
    }
