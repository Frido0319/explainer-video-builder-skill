# Explainer Video Builder V2 Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the approved showcase prototype into a manifest-driven V2 skill that supports both create and enhance workflows and proves reuse with automotive RAG and 6G examples.

**Architecture:** A small `explainer_video_v2` Python package owns manifest validation, pronunciation rewriting, theme tokens, data-driven card rendering, media assembly, audio generation, and verification. A CLI exposes `validate`, `build`, and `verify`; project-specific JSON files contain all content and source paths.

**Tech Stack:** Python 3.13, Pillow, edge-tts, numpy, ffmpeg/ffprobe 4.2.7, ASS subtitles, unittest.

## Global Constraints

- Work only on `v2-enhance-showcase`; keep `main` unchanged.
- Preserve all user source files and reference them read-only.
- Support `create` and `enhance` from the same CLI and manifest schema.
- Use `research_ppt` as the first formal theme.
- Apply pronunciation rewriting before both TTS and subtitle generation.
- Use 4x Lanczos card prescaling before `zoompan`.
- Keep all card content at or above y875 and reserve y900-1049 for subtitles.
- Use deterministic numpy mixing with BGM volume `0.08` and peak protection.
- Do not merge or push `main`.

---

### Task 1: Manifest and Pronunciation Core

**Files:**
- Create: `explainer_video_v2/__init__.py`
- Create: `explainer_video_v2/manifest.py`
- Create: `explainer_video_v2/pronunciation.py`
- Create: `tests/test_v2_manifest.py`
- Create: `tests/test_v2_pronunciation.py`

**Interfaces:**
- Produces: `load_manifest(path: Path) -> dict`, `validate_manifest(data: dict) -> None`, `rewrite_text(text: str, replacements: dict[str, str] | None = None) -> str`, `rewrite_narration(data: dict) -> dict`.

- [ ] **Step 1: Write failing manifest tests**

```python
def test_enhance_requires_clip():
    data = minimal_manifest(mode="enhance", visuals=[card_segment(0, 10)])
    with self.assertRaisesRegex(ValueError, "enhance requires at least one clip"):
        validate_manifest(data)

def test_visuals_must_be_contiguous():
    data = minimal_manifest(visuals=[card_segment(0, 4), card_segment(5, 10)])
    with self.assertRaisesRegex(ValueError, "contiguous"):
        validate_manifest(data)
```

- [ ] **Step 2: Run manifest tests and verify they fail**

Run: `python3 -m unittest tests.test_v2_manifest -v`

Expected: import failure because `explainer_video_v2.manifest` does not exist.

- [ ] **Step 3: Implement manifest loading and validation**

Validation must enforce version 2, supported mode/theme, positive dimensions, exact visual coverage, narration bounds, required fields per `card`/`clip`/`image`, and at least one clip for enhance mode.

- [ ] **Step 4: Write failing pronunciation tests**

```python
def test_default_rewrites_are_applied():
    self.assertEqual(rewrite_text("重排、重传、多运营商"), "重新排序、重新传输、多家运营商")

def test_narration_rewrite_is_non_mutating():
    original = {"narration": [{"text": "执行重排"}]}
    rewritten = rewrite_narration(original)
    self.assertEqual(rewritten["narration"][0]["text"], "执行重新排序")
    self.assertEqual(original["narration"][0]["text"], "执行重排")
```

- [ ] **Step 5: Implement pronunciation rewriting and run both test modules**

Run: `python3 -m unittest tests.test_v2_manifest tests.test_v2_pronunciation -v`

Expected: all tests pass.

- [ ] **Step 6: Commit core model**

```bash
git add explainer_video_v2 tests/test_v2_manifest.py tests/test_v2_pronunciation.py
git commit -m "feat: add v2 manifest and pronunciation core"
```

### Task 2: Theme Tokens and Data-Driven Cards

**Files:**
- Create: `explainer_video_v2/themes.py`
- Create: `explainer_video_v2/cards.py`
- Create: `tests/test_v2_cards.py`

**Interfaces:**
- Consumes: validated card specs from `manifest.py`.
- Produces: `get_theme(name: str) -> Theme`, `render_card(spec: dict, theme: Theme, destination: Path) -> None`, `card_content_bottom(spec: dict) -> int`.

- [ ] **Step 1: Write failing tests for the theme and six templates**

Tests must render `hero`, `process`, `metric_compare`, `chapter`, `metric_grid`, and `ending`; assert 1920x1080 output; verify the research PPT blue/white/red palette; and assert `card_content_bottom(spec) <= 875`.

- [ ] **Step 2: Run tests and verify the missing-module failure**

Run: `python3 -m unittest tests.test_v2_cards -v`

- [ ] **Step 3: Implement immutable theme tokens**

`Theme` must include background, blue, dark_blue, light_blue, red, yellow, text, gray, font paths, and subtitle-safe y boundary.

- [ ] **Step 4: Implement six data-driven templates**

Each template reads only its card spec. No automotive, RAG, 6G, E5, K1, or metric value may appear in `cards.py`.

- [ ] **Step 5: Render a six-card fixture and inspect the contact sheet**

Run: `python3 -m unittest tests.test_v2_cards -v`

Expected: all tests pass and rendered cards have a clear y900-1049 subtitle band.

- [ ] **Step 6: Commit theme and cards**

```bash
git add explainer_video_v2/themes.py explainer_video_v2/cards.py tests/test_v2_cards.py
git commit -m "feat: add data-driven research presentation cards"
```

### Task 3: Shared Media and Audio Pipeline

**Files:**
- Create: `explainer_video_v2/media.py`
- Create: `explainer_video_v2/audio.py`
- Create: `explainer_video_v2/builder.py`
- Create: `explainer_video_v2/cli.py`
- Create: `tests/test_v2_pipeline.py`

**Interfaces:**
- Consumes: rewritten, validated manifest.
- Produces: `build_project(manifest_path: Path) -> Path`, CLI commands `validate`, `build`, and `verify`.

- [ ] **Step 1: Write failing pipeline tests**

Tests must assert ffmpeg commands use 4x Lanczos card prescaling, clip speed is `source_duration / output_duration`, image segments use contain scaling, subtitles consume rewritten narration, and final composition uses H.264/AAC with `+faststart`.

- [ ] **Step 2: Run tests and verify failure**

Run: `python3 -m unittest tests.test_v2_pipeline -v`

- [ ] **Step 3: Implement visual segment builders**

Implement `card`, `clip`, and `image`; normalize every segment to configured fps, dimensions, sample aspect ratio 1, and yuv420p; concatenate in manifest order.

- [ ] **Step 4: Implement narration, ASS subtitles, and deterministic mixing**

Use `zh-CN-YunjianNeural`, configured rate, rewritten narration, per-segment placement, stereo BGM at 0.08, ending fade, and peak scaling only above 0.99.

- [ ] **Step 5: Implement CLI orchestration**

```bash
python3 -m explainer_video_v2.cli validate examples/automotive_rag/project.json
python3 -m explainer_video_v2.cli build examples/automotive_rag/project.json
python3 -m explainer_video_v2.cli verify examples/automotive_rag/project.json
```

- [ ] **Step 6: Run pipeline tests and commit**

```bash
git add explainer_video_v2 tests/test_v2_pipeline.py
git commit -m "feat: add shared v2 media and audio pipeline"
```

### Task 4: Automotive RAG Enhance Example

**Files:**
- Create: `examples/automotive_rag/project.json`
- Create: `examples/automotive_rag/README.md`
- Modify: `tests/test_v2_showcase.py`

**Interfaces:**
- Consumes: V2 manifest schema and CLI.
- Produces: reproducible 72-second enhance example.

- [ ] **Step 1: Write a failing migration test**

The test must load the example, validate 72-second coverage, assert all thirteen visual segments and eleven rewritten narration segments, and reject project-specific text in package modules.

- [ ] **Step 2: Create the automotive manifest**

Move every card string, metric, source path, label, narration, output path, and verification timestamp from `prototypes/v2_showcase` into `examples/automotive_rag/project.json`.

- [ ] **Step 3: Build and verify the 72-second output**

Run the three CLI commands from Task 3. Verify duration `72.024 +/- 0.10`, 1920x1080, 24fps, H.264/AAC, no black intervals, mean volume near -25 dB, max volume below -1 dB, and all representative frames.

- [ ] **Step 4: Document and commit the example**

```bash
git add examples/automotive_rag tests/test_v2_showcase.py
git commit -m "feat: migrate automotive showcase to v2 manifest"
```

### Task 5: Create Example, Local 6G Acceptance, and Skill Documentation

**Files:**
- Create: `examples/create_minimal/project.json`
- Create: `examples/create_minimal/README.md`
- Create: `tests/test_v2_examples.py`
- Modify: `SKILL.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: V2 CLI and, for local acceptance only, user-provided 6G PPT renders.
- Produces: repository-safe create example, local 30-second 6G acceptance video, and V2 usage documentation.

- [ ] **Step 1: Write failing cross-topic tests**

Tests must validate create mode without clips, verify no automotive terms appear in the neutral create manifest, and assert both repository examples use the same `research_ppt` theme.

- [ ] **Step 2: Add a repository-safe create example**

Create a 12-second all-card manifest containing only neutral labels such as `技术方案演示`, `问题`, `方案`, and `验证`. It exists to exercise create mode without storing user project content.

- [ ] **Step 3: Build the local 6G acceptance case outside Git**

Render the provided PPTX to PNG under a temporary local acceptance directory, create the local project manifest there, and build a 30-second video with timeline 0-5 hero, 5-11 background image, 11-18 research-content image, 18-25 expected-results image, 25-30 ending. Narration must summarize only visible source content. Do not `git add` any file from this local acceptance directory.

- [ ] **Step 4: Update Skill documentation**

Document mode selection, manifest schema, pronunciation rules, `research_ppt`, CLI commands, branch status, and the rule that legacy no-cut enhancement remains the default unless V2 editing is explicitly authorized.

- [ ] **Step 5: Build and verify both examples**

Run all unit tests, the automotive and neutral project validations, the automotive and local 6G full builds, ffprobe, blackdetect, volumedetect, and per-segment frame extraction.

- [ ] **Step 6: Commit cross-topic proof and docs**

```bash
git add examples/create_minimal tests/test_v2_examples.py SKILL.md README.md
git commit -m "feat: document v2 create and enhance workflows"
```

### Task 6: Final Branch Acceptance

**Files:**
- Modify only files required by verification findings.

**Interfaces:**
- Produces: clean feature branch with two verified videos and no main changes.

- [ ] **Step 1: Run full automated suite**

Run: `python3 -m unittest tests.test_v2_manifest tests.test_v2_pronunciation tests.test_v2_cards tests.test_v2_pipeline tests.test_v2_showcase tests.test_v2_examples -v`

- [ ] **Step 2: Verify code and branch hygiene**

Run `git diff --check`, confirm feature worktree is clean, confirm root `main...origin/main` is clean, and inspect `git diff --stat main...v2-enhance-showcase`.

- [ ] **Step 3: Verify media artifacts**

Both outputs must decode end to end, contain no black interval longer than 0.2 seconds, have no clipping, render subtitles, and show no text overlap in representative frames.

- [ ] **Step 4: Commit any verification fixes and deliver**

Do not merge or push. Deliver branch name, commit hashes, example commands, and both video paths.
