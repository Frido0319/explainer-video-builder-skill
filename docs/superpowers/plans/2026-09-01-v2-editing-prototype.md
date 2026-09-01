# V2 Editing Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build two directly comparable 28-second clips from the existing RAG video, with the V2 clip adding restrained zooms, chapter guidance, and evidence-based callouts while preserving the verified narration, subtitles, and BGM.

**Architecture:** A single `timeline.json` defines the source interval and visual events. A Python builder validates the timeline, renders transparent Chinese callout assets, rebases the existing ASS subtitles, and invokes ffmpeg 4.2.7 to produce baseline and edited clips. A separate verifier checks media specifications, duration, audio presence, frame-level visual differences, and the subtitle safety band.

**Tech Stack:** Python 3 standard library, Pillow, ffmpeg/ffprobe 4.2.7, ASS subtitles, unittest.

## Global Constraints

- Work only on branch `v2-prototype-editing`; do not modify `main`.
- Treat all source videos, subtitles, reports, and existing outputs as read-only.
- Use source interval `36.0s–64.0s`; both outputs must be `28.0s ± 0.10s`.
- Output must be 1920×1080 H.264 + AAC and remain playable on Ubuntu 20.04.
- Reuse the verified narration, subtitles, and BGM; do not regenerate voice or change wording.
- Maximum visual zoom is `1.08×`.
- New callouts must stay above `y=820`; subtitles retain the verified lower safe band.
- Do not add MiniMax, synthetic experiment footage, publishing, account, or marketing features.

---

### Task 1: Timeline Configuration and Validation

**Files:**
- Create: `prototypes/v2_editing/timeline.json`
- Create: `prototypes/v2_editing/build_prototype.py`
- Create: `tests/test_v2_timeline.py`

**Interfaces:**
- Consumes: JSON object with `source`, `reference`, `clip`, `zoom_segments`, `chapter`, and `callouts`.
- Produces: `load_timeline(path: Path) -> dict` and `validate_timeline(data: dict) -> None`.

- [ ] **Step 1: Write failing validation tests**

Create tests covering exact 28-second duration, non-overlapping zoom segments, maximum zoom `1.08`, and callout bottom edge no lower than `y=820`:

```python
class TimelineValidationTests(unittest.TestCase):
    def test_repository_timeline_is_valid(self):
        data = load_timeline(TIMELINE)
        validate_timeline(data)

    def test_rejects_zoom_over_limit(self):
        data = load_timeline(TIMELINE)
        data["zoom_segments"][0]["zoom_end"] = 1.09
        with self.assertRaisesRegex(ValueError, "zoom"):
            validate_timeline(data)
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `python3 -m unittest tests.test_v2_timeline -v`

Expected: import or function failure because `build_prototype.py` does not yet expose the validators.

- [ ] **Step 3: Add timeline and minimal validators**

The timeline must define `clip.start=36.0`, `clip.end=64.0`, two zoom events (`8–16s`, `21–28s`), one chapter event (`16–16.8s`), and four callout events. Implement explicit numeric and boundary checks with actionable `ValueError` messages.

- [ ] **Step 4: Run tests and confirm pass**

Run: `python3 -m unittest tests.test_v2_timeline -v`

Expected: all timeline tests pass.

- [ ] **Step 5: Commit**

```bash
git add prototypes/v2_editing/timeline.json prototypes/v2_editing/build_prototype.py tests/test_v2_timeline.py
git commit -m "feat: add v2 prototype timeline model"
```

### Task 2: Subtitle Rebasing and Visual Assets

**Files:**
- Modify: `prototypes/v2_editing/build_prototype.py`
- Modify: `tests/test_v2_timeline.py`

**Interfaces:**
- Consumes: existing `subs.ass`, clip start/end, callout definitions.
- Produces: `rebase_ass(source: Path, destination: Path, start: float, end: float) -> int`, `render_assets(data: dict, work_dir: Path) -> dict[str, Path]`.

- [ ] **Step 1: Write failing subtitle rebasing tests**

Use a temporary ASS file containing one event before, one inside, and one after the clip. Assert that only the overlapping event remains and its timestamps are shifted by exactly `start` seconds.

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `python3 -m unittest tests.test_v2_timeline.SubtitleRebaseTests -v`

Expected: failure because `rebase_ass` is missing.

- [ ] **Step 3: Implement ASS timestamp parsing and rebasing**

Implement `parse_ass_time`, `format_ass_time`, and `rebase_ass`. Preserve the ASS header and style lines unchanged. Clamp partially overlapping events to `0` and `clip_duration` and return the number of retained dialogue events.

- [ ] **Step 4: Implement transparent overlay rendering**

Use Pillow and `/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc` to render:

- chapter label `泛化能力测试`;
- callouts `命中率更高`, `教材出处可核验`, `不同问法`, `稳定命中`.

Each asset must use a semi-transparent dark-blue or green rounded rectangle, white text, and dimensions derived from `textbbox` rather than fixed text widths.

- [ ] **Step 5: Run all unit tests and commit**

Run: `python3 -m unittest tests.test_v2_timeline -v`

Expected: all tests pass.

```bash
git add prototypes/v2_editing/build_prototype.py tests/test_v2_timeline.py
git commit -m "feat: add subtitle rebasing and callout assets"
```

### Task 3: Baseline and Edited Clip Builder

**Files:**
- Modify: `prototypes/v2_editing/build_prototype.py`
- Modify: `tests/test_v2_timeline.py`

**Interfaces:**
- Consumes: validated timeline, original visual source, verified enhanced reference, rebased ASS, rendered overlay PNGs.
- Produces: `build_baseline(data: dict, output: Path) -> None`, `build_edited(data: dict, work_dir: Path, output: Path) -> None`, and two MP4 files in the configured output directory.

- [ ] **Step 1: Write failing filter construction tests**

Assert that `build_filter_graph(data, assets)` contains two zoom sections, four callout overlay windows, one chapter overlay window, and a final subtitles filter. Assert every overlay ends above `y=820`.

- [ ] **Step 2: Run tests and confirm failure**

Run: `python3 -m unittest tests.test_v2_timeline.FilterGraphTests -v`

Expected: failure because `build_filter_graph` is missing.

- [ ] **Step 3: Implement deterministic ffmpeg commands**

Build the baseline by re-encoding exactly `36–64s` from the verified enhanced reference. Build the edited clip from the original visual source, split into four timeline ranges, apply zoompan only to the two configured ranges, concatenate them, overlay chapter/callout PNGs with `enable=between(t,start,end)`, then burn the rebased ASS subtitles. Map audio from the enhanced reference over the same source interval. Use `libx264`, `-preset medium`, `-crf 18`, `-pix_fmt yuv420p`, AAC 192 kb/s, 44.1 kHz stereo, `-movflags +faststart`, and output-side `-t 28.0`.

- [ ] **Step 4: Run tests and build both clips**

Run:

```bash
python3 -m unittest tests.test_v2_timeline -v
python3 prototypes/v2_editing/build_prototype.py
```

Expected: tests pass and both MP4 files exist in `06_视频成果/v2_prototype/`.

- [ ] **Step 5: Commit**

```bash
git add prototypes/v2_editing/build_prototype.py tests/test_v2_timeline.py
git commit -m "feat: build comparable v2 editing clips"
```

### Task 4: Automated and Visual Verification

**Files:**
- Create: `prototypes/v2_editing/verify_prototype.py`
- Create: `prototypes/v2_editing/README.md`

**Interfaces:**
- Consumes: baseline and edited MP4 paths.
- Produces: terminal verification report and extracted representative frames under the output work directory.

- [ ] **Step 1: Implement media verification**

Use ffprobe JSON to assert both files are 1920×1080, H.264 + AAC, and `28.0s ± 0.10s`. Use ffmpeg `volumedetect` to verify neither audio track is silent.

- [ ] **Step 2: Implement frame-difference and safety checks**

Extract frames at sample-relative times `4, 10, 16.4, 18, 23, 26`. Confirm baseline and edited frames differ at zoom/callout times. Compare the subtitle band `y=820–1080` at zoom-only times to ensure zoom processing did not move the subtitle layer. Save contact sheets for visual inspection.

- [ ] **Step 3: Document reproducible commands**

Document exact build and verification commands, source/output locations, branch requirement, and the fact that generated MP4 files are delivery artifacts rather than Git-tracked source files.

- [ ] **Step 4: Run verification and inspect representative frames**

Run:

```bash
python3 prototypes/v2_editing/verify_prototype.py
```

Expected: all hard assertions pass; contact sheet clearly shows restrained zooms, chapter label, and four callouts without subtitle overlap.

- [ ] **Step 5: Commit**

```bash
git add prototypes/v2_editing/verify_prototype.py prototypes/v2_editing/README.md
git commit -m "test: verify v2 editing prototype output"
```

### Task 5: Final Branch Integrity and Delivery

**Files:**
- Verify only; no required source changes.

**Interfaces:**
- Consumes: branch history, generated clips, verifier report.
- Produces: final user-facing links to baseline and edited clips.

- [ ] **Step 1: Verify branch isolation**

Run: `git diff --name-status main...v2-prototype-editing`

Expected: only design/plan documents, prototype scripts/configuration, tests, and prototype README; no existing stable script is modified.

- [ ] **Step 2: Run complete regression checks**

Run:

```bash
python3 -m unittest tests.test_v2_timeline -v
python3 prototypes/v2_editing/verify_prototype.py
git diff --check main...v2-prototype-editing
```

Expected: all commands pass.

- [ ] **Step 3: Deliver both videos**

Provide the absolute paths and inline playback links for `原版片段_36-64s.mp4` and `V2精剪样片_36-64s.mp4`, summarize visible differences, and explicitly state that `main` remains unchanged.
