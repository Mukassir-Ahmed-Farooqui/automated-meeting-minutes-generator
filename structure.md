# Automated Meeting Minutes Generator: Architecture & Implementation Blueprint

## Overview
This document outlines the architectural roadmap for transforming the Automated Meeting Minutes Generator from a sequential, CLI-driven academic/portfolio project into a polished, functional, and simple web application. 

**Core Architectural Principle:** The architecture must remain simple, understandable, reliable, and easy to run locally. This is a portfolio project, not an enterprise SaaS platform. We avoid unnecessary infrastructure like PostgreSQL, Redis, Celery, RabbitMQ, Kafka, or Kubernetes.

## Features
- **Video Upload:** Accept MP4, MOV, MKV, WebM via a drag-and-drop React interface.
- **Audio Extraction:** Backend extracts audio from the video using FFmpeg.
- **Transcription:** High-accuracy transcription using the OpenAI Whisper model.
- **NLP Processing:** The existing DistilBERT and DistilBART pipelines extract actions, decisions, key points, and generate a hierarchical summary.
- **Results Viewer:** A polished React UI displaying the structured results (Transcript, Summary, Action Items, Decisions).
- **Downloadable Outputs:** Users can download `.txt` (transcript), `.md` (minutes), and `.json` (full structured results).

---

## Architecture

We are building a simple, modular monolith utilizing React + Vite for the frontend and FastAPI for the backend. Data is handled via the local filesystem for simplicity.

### High-Level System Flow

```mermaid
graph TD
    UI[React + Vite Frontend]
    API[FastAPI Backend]
    FFMPEG[FFmpeg Audio Extraction]
    WHISPER[Whisper Transcription]
    NLP[NLP Pipeline (Summarize, Classify, Extract)]
    OUTPUT[Minutes Generator]

    UI -- "Upload Video (MP4/MOV)" --> API
    API -- "Save Temp Video" --> FFMPEG
    FFMPEG -- "Extract Audio (WAV)" --> WHISPER
    WHISPER -- "Transcript (Timestamps)" --> NLP
    NLP -- "Classify, Summarize, Extract" --> OUTPUT
    OUTPUT -- "Structured JSON" --> API
    API -- "Poll/Return Results" --> UI
```

### Detailed Processing Flow
1. **Video Input:** User uploads a video to FastAPI.
2. **Audio Extraction:** FastAPI calls FFmpeg to extract the audio track to a temporary `.wav` file.
3. **Transcription:** Whisper ASR transcribes the audio, preserving sentence boundaries and timestamps where possible. *(Note: Speaker diarization is not currently supported natively by this Whisper pipeline and will not be faked. All speakers are marked as "Unknown" unless explicitly labeled in text).*
4. **Text Preprocessing & Chunking:** Transcript is cleaned, segmented into sentences, and chunked to fit the 1024-token limit of DistilBART.
5. **Summarization:** DistilBART hierarchically summarizes the transcript chunks.
6. **Classification & Extraction:** DistilBERT classifies sentences (Action/Decision/Other), and spaCy extracts specific owners and deadlines.
7. **JSON Formatting:** The pipeline packages the transcript, summary, key points, decisions, and action items into a clean JSON structure.

---

## Directory Structure

The project will use a monorepo approach with clear separation of Frontend and Backend/ML code.

```text
project-root/
│
├── frontend/                 # React + Vite Application
│   ├── public/
│   ├── src/
│   │   ├── components/       # Reusable UI (UploadBox, ActionItemsTable)
│   │   ├── pages/            # Views (Home, Results)
│   │   ├── api/              # Axios/Fetch API wrappers
│   │   ├── hooks/            # Custom hooks (usePolling, useUpload)
│   │   ├── utils/            # Formatters
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── routes/
│   │   │   └── meetings.py   # API endpoints
│   │   ├── services/
│   │   │   ├── video.py      # FFmpeg integration
│   │   │   └── pipeline.py   # Wrapper around ML module
│   │   └── schemas/
│   │       └── meeting.py    # Pydantic JSON schemas
│   └── requirements.txt
│
├── ml/                       # Refactored Machine Learning Pipeline (formerly `src/`)
│   ├── asr.py                # Whisper transcription
│   ├── preprocessing.py
│   ├── chunking.py
│   ├── classification.py
│   ├── summarization.py
│   ├── extraction.py
│   ├── pipeline.py           # Clean Python API: run_pipeline(audio_path)
│   └── minutes_generator.py
│
├── data/                     # Local processing storage (gitignored)
│   ├── uploads/              # Temp uploaded videos
│   ├── audio/                # Extracted WAV files
│   └── outputs/              # JSON/MD/TXT results
│
├── scripts/                  # Helper CLI scripts
├── tests/                    # Pytest suite
├── .env.example
├── .gitignore
└── README.md
```

---

## API Design

The backend exposes a minimal REST API. There are no CRUD database endpoints, as data is temporary.

**POST `/api/process`**
- **Request:** `multipart/form-data` containing `video=<file>`.
- **Response:** `{ "success": true, "job_id": "uuid-1234" }`
- **Action:** Saves the video, creates a processing job, and launches a FastAPI `BackgroundTasks` execution.

**GET `/api/process/{job_id}`**
- **Purpose:** Polled by the frontend to check progress.
- **Response:** `{ "status": "processing", "step": "transcribing" }` OR `{ "status": "completed", "results": {...} }`

**GET `/api/download/{job_id}/{format}`**
- **Purpose:** Returns the generated `.txt`, `.md`, or `.json` file for the user to download.

---

## Processing Model (Sync vs Async)

Because audio extraction and ML inference (Whisper + Transformers) can take minutes, doing this synchronously will cause HTTP timeouts. 
**Solution:** We use a lightweight background processing approach via FastAPI's built-in `BackgroundTasks`. 
- No Celery, No Redis.
- The pipeline executes in the background. State and progress are tracked via simple JSON files written to the `data/outputs/` directory (e.g., `job-uuid.status.json`).
- The frontend polls the status endpoint until completion.

---

## ML Pipeline & Accuracy Considerations

**Priorities:** Transcription quality and end-to-end reliability above all else.

1. **Transcription:** The Whisper implementation must be stable. We will evaluate the existing implementation and consider upgrading to `openai-whisper` or `faster-whisper` based on local VRAM constraints and execution speed on long audio.
2. **Model Caching:** Transformer models (DistilBART, DistilBERT) and Whisper must be loaded into memory *once* at startup or upon first request, not re-loaded for every chunk/sentence.
3. **Graceful Degradation:** If the DistilBERT classifier is not fine-tuned, the pipeline must gracefully fall back to rules-based extraction without crashing or hallucinating.
4. **Speaker Diarization:** Not currently included in the core ML stack to avoid unnecessary complexity. Will be documented as a future enhancement.

---

## Deployment Strategy

**Frontend:**
- Easily deployable to **Vercel, Netlify, or Cloudflare Pages**.

**Backend (API + ML):**
- Can be deployed to **Render, Railway, or Fly.io**.
- **Crucial Note:** Running Whisper and Transformer models requires significant memory (typically >2-4GB RAM). Free tiers of PaaS providers will likely crash with Out Of Memory (OOM) errors. For this portfolio project, **local reproducibility** is the primary goal. Production cloud deployment would require a paid tier or dedicated EC2 instance.

---

## Implementation Roadmap

Implementation must strictly follow this order to ensure a stable product:

### Phase 1: Clean and Validate Existing ML Pipeline
- Audit existing code. Ensure the CLI pipeline works reliably on audio files.

### Phase 2: Create Clean Python Pipeline API
- Refactor the ML code to expose a simple function: `run_pipeline(video/audio_path)` that returns structured JSON dictionaries.

### Phase 3: Add Video → Audio Extraction
- Integrate `ffmpeg-python` or `subprocess` calls to reliably convert uploaded `.mp4/.mov` files into `.wav` audio.

### Phase 4: Integrate Pipeline with FastAPI
- Create the FastAPI backend. Implement the `/api/process` route using `BackgroundTasks` and state tracking.

### Phase 5: Create React + Vite Frontend
- Scaffold the frontend. Build the upload UI with drag-and-drop support and file format validation.

### Phase 6: Connect React → FastAPI
- Implement the API polling mechanism in React to display the "Uploading -> Extracting -> Transcribing -> Processing" pipeline states.

### Phase 7: Create the Results Interface
- Build the polished React views for the Transcript, Summary, Key Points, Decisions, and Action Items table.

### Phase 8: Add Download Functionality
- Implement endpoints and UI buttons to download `.json`, `.txt`, and `.md` outputs.

### Phase 9: Test with Real Meeting Videos
- Validate the entire stack locally using short, long, clear, and noisy meeting videos. Ensure no OOM errors or timeouts occur.

### Phase 10: Polish and Bug Fixes
- Fix accuracy, reliability, performance, and UI layout issues. Ensure the application feels like a cohesive, polished product.

---
*This document serves as the absolute source of truth for the architectural refactoring of the project.*
