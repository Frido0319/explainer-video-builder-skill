# V1 / V2 Selectable Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one `explainer-video-builder-skill` expose stable, explicit V1 and V2 choices without replacing the existing V1 workflow.

**Architecture:** Put the authoritative version router near the top of `SKILL.md`, mirror it in `README.md`, and keep the two implementations isolated: V1 continues using the existing scripts, while V2 continues using the manifest-driven package. Protect the contract with repository tests and routing evals instead of adding a misleading wrapper CLI.

**Tech Stack:** Markdown skill instructions, JSON evals, Python `unittest`, existing V1 scripts, existing `explainer_video_v2` package.

## Global Constraints

- Explicit `V1` or `V2` selection always wins over automatic routing.
- An existing video without editing authorization routes to V1 and keeps its original picture, sequence, and duration.
- V2 contains `create` and `enhance`; `enhance` still requires explicit editing authorization.
- If routing remains ambiguous, default to V1.
- Do not delete, rename, or rewrite the proven V1 scripts.
- Do not change the V2 manifest schema from `version=2`.
- Do not push GitHub during this implementation.

---

### Task 1: Add the dual-version contract test

**Files:**
- Create: `tests/test_version_selection.py`

**Interfaces:**
- Consumes: repository `SKILL.md`, `README.md`, `evals/evals.json`, V1 script paths, and V2 package paths.
- Produces: a static acceptance test that fails until the version router and eval cases exist.

- [ ] **Step 1: Write the failing test**

```python
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VersionSelectionContractTests(unittest.TestCase):
    def test_skill_and_readme_publish_the_same_version_contract(self):
        markers = (
            "## 版本选择：V1 / V2",
            "V1（保真增强）",
            "V2（制作 / 精剪）",
            "显式版本选择优先于自动路由",
            "未明确选择版本时，默认使用 V1",
        )
        for name in ("SKILL.md", "README.md"):
            content = (ROOT / name).read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, content, f"{name} missing {marker}")

    def test_both_implementations_remain_present(self):
        for relative in (
            "scripts/make_tts.py",
            "scripts/make_subs.py",
            "scripts/mix_audio.py",
            "scripts/verify_video.py",
            "explainer_video_v2/cli.py",
            "explainer_video_v2/manifest.py",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_evals_cover_explicit_and_fallback_routing(self):
        data = json.loads((ROOT / "evals/evals.json").read_text(encoding="utf-8"))
        names = {item["name"] for item in data["evals"]}
        self.assertTrue(
            {"explicit-v1", "explicit-v2", "default-v1-fallback"}.issubset(names)
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_version_selection -v`

Expected: FAIL because the shared version heading, routing phrases, and three eval cases are not present yet.

- [ ] **Step 3: Commit the red test**

```bash
git add tests/test_version_selection.py
git commit -m "test: define v1 v2 selection contract"
```

### Task 2: Publish the authoritative router in the skill

**Files:**
- Modify: `SKILL.md`

**Interfaces:**
- Consumes: the version contract from Task 1 and the existing V1/V2 workflows.
- Produces: one authoritative routing table and conflict rules for future agents.

- [ ] **Step 1: Add the version selection section near the top of SKILL.md**

Add `## 版本选择：V1 / V2` immediately after the introductory paragraph. It must state:

```markdown
- **显式版本选择优先于自动路由**：用户说“用 V1”或“用 V2”时，严格按该版本执行。
- **未明确选择版本时，默认使用 V1**；只有创建新视频，或用户明确授权改变镜头结构时，才自动进入 V2。
```

Add a table defining V1 as preserve-picture overlay and V2 as manifest-driven `create` / `enhance`. Add a conflict rule stating that V1 plus a request to delete/reorder clips must stop at the V1 boundary rather than silently switching versions.

- [ ] **Step 2: Make the existing V2 section subordinate to the router**

Rename the heading to `## V2 工作流（仅在选择 V2 后）`, keep the CLI commands unchanged, and replace the old mixed “legacy overlay / create / enhance” table with only the two V2 modes.

- [ ] **Step 3: Run the focused contract test**

Run: `python3 -m unittest tests.test_version_selection -v`

Expected: only the README/eval assertions remain failing; V1/V2 files continue to exist.

- [ ] **Step 4: Commit the skill router**

```bash
git add SKILL.md
git commit -m "feat: add v1 v2 routing to skill"
```

### Task 3: Mirror the contract for users and evals

**Files:**
- Modify: `README.md`
- Modify: `evals/evals.json`

**Interfaces:**
- Consumes: the authoritative SKILL router from Task 2.
- Produces: user-visible version selection examples and regression prompts.

- [ ] **Step 1: Add the same version heading and routing table to README.md**

Use the exact contract markers from the test. Show these example requests:

```text
用 V1 给这个成片加中文配音、字幕和 BGM，不改变原时长。
用 V2 enhance 精剪这个录屏，可以删除、压缩和重新排序。
用 V2 create 根据这些 PPT 页和文案重新制作讲解视频。
```

- [ ] **Step 2: Add three eval cases**

Append JSON entries named `explicit-v1`, `explicit-v2`, and `default-v1-fallback`. Their expected output must respectively require V1 overlay behavior, V2 `enhance` with authorization, and V1 safe fallback when no version or editing authorization is present.

- [ ] **Step 3: Run the focused contract test**

Run: `python3 -m unittest tests.test_version_selection -v`

Expected: 3 tests pass.

- [ ] **Step 4: Commit docs and evals**

```bash
git add README.md evals/evals.json
git commit -m "docs: expose selectable v1 and v2 workflows"
```

### Task 4: Run full validation and prepare local integration

**Files:**
- Verify only: repository test suite and existing example manifests.

**Interfaces:**
- Consumes: all implementation commits.
- Produces: fresh evidence that V1 files remain present and V2 still validates real projects.

- [ ] **Step 1: Run every repository test**

Run: `python3 -m unittest discover -s tests -v`

Expected: all tests pass, including the new 3-test version contract.

- [ ] **Step 2: Validate the neutral V2 create example**

Run: `python3 -m explainer_video_v2.cli validate examples/create_minimal/project.json`

Expected: `mode=create`, `theme=research_ppt`, and successful validation.

- [ ] **Step 3: Verify the neutral V2 create output**

Run: `python3 -m explainer_video_v2.cli verify examples/create_minimal/project.json`

Expected: duration, video/audio specifications, black-frame scan, loudness, and requested frame extraction all pass.

- [ ] **Step 4: Verify the automotive V2 enhance output**

Run with `AUTOMOTIVE_RAG_DELIVERY` set to the local `06_视频成果` directory:

```bash
python3 -m explainer_video_v2.cli verify examples/automotive_rag/project.json
```

Expected: the accepted 72-second automotive output passes all checks.

- [ ] **Step 5: Check repository integrity**

Run: `git diff --check && git status --short --branch`

Expected: no whitespace errors and a clean `v2-enhance-showcase` worktree.
