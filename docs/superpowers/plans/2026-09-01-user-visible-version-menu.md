# User-Visible Version Menu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the skill visibly present V1, V2 create, and V2 enhance choices whenever the user has not already selected a complete version direction.

**Architecture:** Keep version selection as an instruction-level contract in `SKILL.md`, mirrored in `README.md` and protected by static contract tests and eval prompts. Do not alter either media engine; only replace silent automatic fallback with an explicit menu, recommendation, and wait state.

**Tech Stack:** Markdown skill instructions, JSON evals, Python `unittest`, existing V1 scripts and `explainer_video_v2` package.

## Global Constraints

- When no version is specified, display V1, V2 create, and V2 enhance and wait for the user.
- A recommendation may guide the user but must never start work automatically.
- When the user specifies only V2, display the two V2 sub-directions and wait.
- When the user already specifies V1, V2 create, or V2 enhance, announce the boundary and proceed without repeating the menu.
- Map replies `1`, `2`, and `3` to V1, V2 create, and V2 enhance.
- Selecting V2 enhance from the menu authorizes the listed delete, compress, reorder, and added-card operations; broader destructive actions still require separate authorization.
- Do not change V1 scripts, the V2 manifest schema, media rendering, TTS, subtitles, mixing, or verification logic.
- Do not push GitHub.

---

### Task 1: Replace the old fallback contract with menu tests

**Files:**
- Modify: `tests/test_version_selection.py`

**Interfaces:**
- Consumes: `SKILL.md`, `README.md`, `evals/evals.json`, V1 script paths, and V2 package paths.
- Produces: regression tests for visible choices, wait behavior, numeric mapping, explicit-version bypass, and eval coverage.

- [ ] **Step 1: Replace the document marker test**

Use these required markers for both `SKILL.md` and `README.md`:

```python
markers = (
    "请选择视频制作方向：",
    "V1｜保真增强",
    "V2 create｜重新制作",
    "V2 enhance｜精剪重构",
    "展示完整三项菜单并等待用户选择",
    "1 / 2 / 3",
)
```

Also assert that neither document contains `未明确选择版本时，默认使用 V1`.

- [ ] **Step 2: Add routing-boundary assertions**

Add a test that requires these SKILL markers:

```python
for marker in (
    "只说 V2",
    "列出两个 V2 子方向并等待选择",
    "已明确选择 V1、V2 create 或 V2 enhance",
    "不重复展示菜单",
):
    self.assertIn(marker, skill)
```

- [ ] **Step 3: Replace the eval coverage assertion**

Require these eval names:

```python
required = {
    "menu-no-version",
    "menu-v2-submode",
    "numeric-version-selection",
    "explicit-version-no-repeat",
}
self.assertTrue(required.issubset(names))
self.assertNotIn("default-v1-fallback", names)
```

- [ ] **Step 4: Run the focused test and verify RED**

Run: `python3 -m unittest tests.test_version_selection -v`

Expected: FAIL because SKILL, README, and evals still describe the old default-V1 behavior.

- [ ] **Step 5: Commit the failing contract**

```bash
git add tests/test_version_selection.py
git commit -m "test: require user-visible version menu"
```

### Task 2: Implement the visible menu in SKILL and README

**Files:**
- Modify: `SKILL.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the menu contract from Task 1.
- Produces: the runtime instructions agents follow and the matching human-facing documentation.

- [ ] **Step 1: Replace SKILL automatic routing with the fixed menu**

Add the exact three-item menu from the approved spec, including a dynamic recommendation line and this reply line:

```text
请回复 1 / 2 / 3，或直接回复 V1 / V2 create / V2 enhance
```

State that the agent must display it and wait when no complete version is present.

- [ ] **Step 2: Add explicit and partial-selection behavior to SKILL**

Write the following rules in imperative form:

```markdown
- 用户只说 V2 时，列出两个 V2 子方向并等待选择。
- 用户已明确选择 V1、V2 create 或 V2 enhance 时，复述边界后直接执行，不重复展示菜单。
- 用户回复 1 / 2 / 3 时，分别映射到 V1 / V2 create / V2 enhance。
```

Remove the sentence `未明确选择版本时，默认使用 V1` and any instruction that automatically starts work based only on inferred intent.

- [ ] **Step 3: Mirror the same contract in README**

Show the full menu, recommendation behavior, numeric mapping, partial V2 rule, and explicit-version bypass. Remove the default-V1 claim.

- [ ] **Step 4: Run the focused test**

Run: `python3 -m unittest tests.test_version_selection -v`

Expected: document contract tests pass; eval coverage still fails.

- [ ] **Step 5: Commit the menu documentation**

```bash
git add SKILL.md README.md
git commit -m "feat: show version menu before video work"
```

### Task 3: Update evals and complete regression verification

**Files:**
- Modify: `evals/evals.json`

**Interfaces:**
- Consumes: menu behavior from Task 2.
- Produces: four realistic evaluation cases and final evidence that both engines remain intact.

- [ ] **Step 1: Replace the old fallback eval and add three routing evals**

Create the following cases:

- `menu-no-version`: an existing-video request without a version must receive the full menu, a V1 recommendation, and no work before selection.
- `menu-v2-submode`: “用 V2 做视频” must receive create/enhance choices and wait.
- `numeric-version-selection`: replying `3` after the menu maps to V2 enhance and authorizes the listed editing operations.
- `explicit-version-no-repeat`: an explicit V1 request announces V1 and proceeds without showing the menu again.

Delete the contradictory `default-v1-fallback` case.

- [ ] **Step 2: Run the focused test and verify GREEN**

Run: `python3 -m unittest tests.test_version_selection -v`

Expected: all version-selection tests pass.

- [ ] **Step 3: Run the complete repository suite**

Run: `python3 -m unittest discover -s tests -v`

Expected: all tests pass.

- [ ] **Step 4: Validate the skill structure**

Run: `python3 "${SKILL_CREATOR_DIR}/scripts/quick_validate.py" .`

Expected: `Skill is valid!`

- [ ] **Step 5: Re-verify both V2 acceptance outputs**

Run:

```bash
python3 -m explainer_video_v2.cli verify examples/create_minimal/project.json
AUTOMOTIVE_RAG_DELIVERY='/path/to/automotive-rag-delivery' \
  python3 -m explainer_video_v2.cli verify examples/automotive_rag/project.json
```

Expected: both outputs pass duration, codec, black-frame, audio, and verification-frame checks.

- [ ] **Step 6: Commit evals**

```bash
git add evals/evals.json
git commit -m "test: cover interactive version selection"
```

- [ ] **Step 7: Check branch integrity**

Run: `git diff --check && git status --short --branch`

Expected: clean `v2-enhance-showcase` worktree.
