# V2 Showcase Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a polished 72-second RAG technology showcase video from verified project footage and metrics.

**Architecture:** A single timeline configuration drives card rendering, source clip extraction, TTS, subtitle generation, deterministic audio mixing, final ffmpeg composition, and verification. Source assets remain read-only and generated artifacts are written beside the existing video deliverables.

**Tech Stack:** Python 3, Pillow, edge-tts, numpy, ffmpeg/ffprobe 4.2.7, ASS subtitles, unittest.

## Global Constraints

- Work only on `v2-enhance-showcase`; keep `main` unchanged.
- Use only verified metrics from `项目系统复盘_2026-08-29.txt`.
- Output exactly 72 seconds at 1920×1080, 24fps, H.264 + AAC.
- Preserve all original source files; generated output goes to `06_视频成果/v2_showcase/`.
- Use 4× Lanczos prescaling for every animated static card to prevent zoom jitter.
- Subtitles and narration must share one source text.

---

### Task 1: Timeline, Data Model, and Tests

- [ ] Create `prototypes/v2_showcase/timeline.json` with all thirteen visual segments and nine narration segments.
- [ ] Create `tests/test_v2_showcase.py` asserting 72-second duration, contiguous visual segments, narration bounds, approved metrics, and 4× prescale requirement.
- [ ] Run the test and observe failure because the builder is missing.
- [ ] Create `prototypes/v2_showcase/build_showcase.py` with timeline loading and validation.
- [ ] Run tests and commit the passing timeline model.

### Task 2: Visual Cards and Video Segments

- [ ] Implement six 1920×1080 dark technology cards with a shared grid, typography, data pills, and progress arrows.
- [ ] Implement smooth card animation using `scale=7680:4320:flags=lanczos,zoompan`.
- [ ] Extract and speed the four real comparison clips into four-second segments.
- [ ] Extract K1/K3/K4 six-second clips from `viz_gen.mp4`.
- [ ] Build all thirteen normalized video segments and concatenate a silent 72-second video.
- [ ] Extract representative frames and visually inspect every card and source segment.

### Task 3: Narration, Subtitles, and Audio

- [ ] Generate nine edge-tts narration files with `zh-CN-YunjianNeural` and verify each fits its allocated segment.
- [ ] Generate ASS subtitles from the same narration, with protected technical terms and no trailing punctuation.
- [ ] Mix narration and `assets/bgm_default.mp3` deterministically at BGM volume0.08 with a three-second ending fade.
- [ ] Verify mean/max volume and absence of clipping.

### Task 4: Final Composition and Verification

- [ ] Burn ASS subtitles and mux the mixed audio into the 72-second silent video.
- [ ] Verify duration, dimensions, codecs, frame rate, sample rate, and channels with ffprobe.
- [ ] Extract frames at every segment midpoint and build a contact sheet.
- [ ] Check subtitle rendering and overlap at active cue timestamps.
- [ ] Run full tests, `git diff --check`, and verify `main` remains clean.
- [ ] Commit the showcase implementation and deliver the final MP4.
