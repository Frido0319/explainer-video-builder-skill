<p align="center">
  <img src="assets/hero.svg" alt="Explainer Video Builder" width="860">
</p>

<p align="center">
  <b>把技术方案 / 项目成果做成带中文配音、有叙事节奏的 1080p 讲解视频。</b>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-0f766e?style=for-the-badge"></a>
  <img alt="Skill" src="https://img.shields.io/badge/Claude%20Skill-ready-2563eb?style=for-the-badge">
  <img alt="Output" src="https://img.shields.io/badge/output-MP4%20%7C%201080p%20%7C%20H.264%2FAAC-7c3aed?style=for-the-badge">
  <img alt="Voice" src="https://img.shields.io/badge/voice-edge--tts%20中文-dc2626?style=for-the-badge">
</p>

<p align="center">
  <a href="#why-it-exists">Why</a>
  <span> · </span>
  <a href="#highlights">Highlights</a>
  <span> · </span>
  <a href="#what-it-produces">Outputs</a>
  <span> · </span>
  <a href="#install">Install</a>
  <span> · </span>
  <a href="#workflow">Workflow</a>
  <span> · </span>
  <a href="#quality-bar">Quality Bar</a>
  <span> · </span>
  <a href="#中文说明">中文说明</a>
</p>

---

## 版本选择：V1 / V2

同一个 skill 同时提供三个可选方向，V2 不会覆盖 V1。用户没有指定完整版本时，skill 会展示完整三项菜单并等待用户选择：

**编号是版本选择协议，不是局部菜单的装饰序号。** 在整段对话中始终保持 `1=V1`、`2=V2 create`、`3=V2 enhance`，不得因只展示 V2 子方向而改变映射。

V2 子菜单固定模板（必须原样使用序号）：

```text
请选择 V2 子方向：

2. V2 create｜重新制作
   根据 PPT、图片、文案和素材，从零制作讲解视频

3. V2 enhance｜精剪重构
   可删除、压缩、重新排序原视频，并增加标题卡、数据卡等新画面

请回复 2 / 3，或直接回复 V2 create / V2 enhance
```

```text
请选择视频制作方向：

1. V1｜保真增强
   保留原画面、顺序和时长，只添加配音、字幕和 BGM

2. V2 create｜重新制作
   根据 PPT、图片、文案和素材，从零制作讲解视频

3. V2 enhance｜精剪重构
   可删除、压缩、重新排序原视频，并增加标题卡、数据卡等新画面

根据你的素材和目标，我推荐：<V1 / V2 create / V2 enhance>
推荐理由：<一句与当前请求直接相关的理由>
请回复 1 / 2 / 3，或直接回复 V1 / V2 create / V2 enhance
```

- 推荐只帮助用户判断，skill 必须等待选择，不能按推荐项自动开工。
- 用户只说 V2 时，列出两个 V2 子方向并等待选择，并沿用完整菜单中的全局编号：
  - `2. V2 create｜重新制作`
  - `3. V2 enhance｜精剪重构`
- 提示用户“请回复 2 / 3”；不得在 V2 子菜单中重新编号为 1 / 2。
- 用户已明确选择 V1、V2 create 或 V2 enhance时，复述边界后直接执行，不重复展示菜单。
- 用户回复 1 / 2 / 3 时，分别映射到 V1 / V2 create / V2 enhance。
- 选择 V2 enhance，表示授权菜单列明的删除、压缩、重新排序和增加信息卡操作。
- 选择与请求冲突时不会静默改版本。例如 V1 不执行删除镜头，需改选 V2 enhance。

## Why it exists

学生、工程师和课题组经常需要"给老师 / 组会 / 结题做一个项目讲解视频"，但手搓视频极其耗时：

- 画面没有统一风格，随手贴图、随手放字，放大就脏
- 架构图不按规范画，粗线大色块经不起看
- 配音与画面不同步，"画外音"追着画面跑
- 实测视频没检查黑屏段，把黑屏放进成品
- 每一步手动做，改一版文案就要全部重来

本 skill 把整套流程固化成可复现的工作流：**白底学术卡（配图一律 PPT 原图）→ 规范 SVG 架构图 → edge-tts 中文配音 → 自动中文字幕 → ffmpeg 按时间轴合成烧录 → 卡片比对 + 字幕带无视觉自检**。你只需要给项目素材和一段叙事文案，剩下的全自动化。

这是为任意技术领域设计的：通信、无人机、AI、嵌入式、科研汇报……凡是"把一个方案讲清楚"的视频都适用。成片效果样例：`智信2026.mp4`（无人机 5G 视频可靠传输，157s，10 段，中文配音 + 38 条中文字幕，卡片图片全部来自 6G 申报书 PPT 原图）。

## Highlights

| 能力 | 效果 |
| --- | --- |
| 白底学术风画面 | 纯白底 + 黑色大字 + 单一强调色下划线，正式汇报观感 |
| **PPT 原图铁律** | 卡内图片一律用用户 PPT 导出原图，等比 contain 不裁剪，禁额外图片 |
| **图片不遮文字自检** | text-only 验证：图区域无文字侵入才放行 |
| **自动中文字幕** | `make_subs.py` 复用配音文案自动生成 `subs.srt`，字幕是必须项 |
| **字幕带约束** | 卡片内容最下缘 ≤y940，字幕烧录(y960-1049)不遮任何内容 |
| Flat Icon 规范技术图 | 细边框、tint 图标、正交走线、8px 网格对齐（借鉴高星 skill 规范） |
| 先预告再放实测 | 实测前必有"实测效果展示"预告卡，观众有预期 |
| 黑屏段自动检测 | 实测前扫描上部亮度，找黑屏起点，只剪干净段 |
| 中文男声配音 | edge-tts Yunjian 沉稳男声，按时间轴 `adelay` 精确对齐 |
| 时间轴自动合成 | 段边界在脚本顶部定义，段长由边界相减自动算 |
| 防削波混音 | `alimiter=limit=0.95`，多路配音+背景乐不爆音 |
| 默认 BGM | `assets/bgm_default.mp3`（洛克王国人鱼湾/兜圈活音乐），音量 0.08，结尾 3s 淡出 + 5s 静音 |
| 字幕底部居中 | 实战字号 18px，遇到原视频底部文字可调小或上移 |
| 保持原视频时长 | 用户未要求剪辑时，不动原画面时长，配音/字幕/背景音叠加其上 |
| V2 双模式 | `create` 从 PPT/图片/文案创建；`enhance` 在明确授权后精剪现有视频 |
| 科研汇报主题 | `research_ppt` 统一蓝白红视觉语言，并为 PPT 页预留字幕安全区 |
| 发音词典 | “重排”自动改为“重新排序”等自然说法，TTS 与字幕共享改写结果 |
| 无视觉自检 | 像素亮度 + OCR + 卡片比对 + 字幕带检查，无图形界面也能验证 |
| 可复现工作流 | 改文案改时间轴即重出，无需手动剪辑 |

## What it produces

```text
video_build/
  cards/          # PIL 生成的全部画面卡（白底学术卡/预告卡/渐变背景）
    arch.svg      # 按 Flat Icon 规范手写的系统架构图
    feedback.svg  # 反馈闭环图（与架构图同风格）
  audio/          # seg*.mp3 配音 + 合成音轨
  seg/            # 每段独立 mp4
  subs.srt        # make_subs.py 自动生成的中文字幕
  *.mp4           # 成品：1920×1080 H.264+AAC，60–120s，带中文字幕
```

## Install

克隆到 Claude Code skills 目录：

```bash
git clone https://github.com/Frido0319/explainer-video-builder-skill.git ~/.claude/skills/explainer-video-builder-skill
```

或手动拷贝本地目录。依赖（Ubuntu 已验证）：

```bash
sudo apt-get install -y ffmpeg libreoffice poppler-utils fonts-noto-cjk tesseract-ocr tesseract-ocr-chi-sim \
  gstreamer1.0-libav gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
pip install edge-tts==7.2.8 pillow numpy
```

macOS/Windows 未安装 Noto CJK 时，可通过 `EXPLAINER_VIDEO_FONT_REGULAR` 和
`EXPLAINER_VIDEO_FONT_BOLD` 指定中文字体文件；程序也会自动尝试 PingFang 和微软雅黑。

## Workflow

```mermaid
flowchart LR
  A[素材 + 叙事文案] --> B[定时间轴九段]
  B --> C[PIL 生成画面卡<br/>PPT原图+字幕带约束]
  C --> D[SVG 技术图 → chrome 渲染 PNG]
  D --> E[edge-tts 中文配音<br/>make_subs 生成字幕]
  E --> F[ffmpeg 按时间轴合成<br/>+字幕烧录重编码]
  F --> G[卡片比对+字幕带检查]
  G --> H[交付 MP4]
```

九段叙事：片头 → 背景 → 痛点 → 方案 → 架构 → 反馈闭环 → **实测预告** → 实测视频 → 结束页。字幕由配音文案自动生成（`make_subs.py`），烧录时卡片内容已按字幕带（y960-1049）上移避让。

### V2 manifest workflow

V2 把一次性脚本收敛为 `project.json`：

```bash
python3 -m explainer_video_v2.cli validate examples/create_minimal/project.json
python3 -m explainer_video_v2.cli build examples/create_minimal/project.json
python3 -m explainer_video_v2.cli verify examples/create_minimal/project.json
```

- `mode=create`：从卡片、PPT/PPTX 页、图片和旁白创建新视频。`kind=pptx` 配合 1 起始的 `slide`，构建时只读导出并缓存该页。
- `mode=enhance`：用户明确允许剪辑后，从现有视频选择、压缩、重新排序片段，并加入新卡片重构叙事。
- `theme=research_ppt`：复用正式申报 PPT 的蓝白红视觉体系；导入 PPT 页时完整缩放至 y=875 以上，底部留给字幕。
- `pronunciations`：构建前统一改写易错读词。例如“重排”写入字幕和 TTS 前变成“重新排序”，保证读音与文字一致。

可直接查看：

- `examples/create_minimal/project.json`：不依赖外部素材的纯 `create` 示例。
- `examples/automotive_rag/project.json`：现有视频精剪与科研卡片混排的 `enhance` 示例。

模式选择遵循授权边界：未明确允许剪辑时，继续保持源视频时长；只有用户明确说可以删除、压缩、重新排序或重拍，才启用 `enhance`。

## Quality bar

交付前逐条自查：

- [ ] 时长等于计划总长，每段边界与时间轴一致（ffprobe）
- [ ] 分辨率 1920×1080，H.264 + AAC + faststart
- [ ] **字幕已生成并烧录**（`subs.srt` 存在、成片字幕带 y960-1049 有渲染像素）
- [ ] **卡片内容最下缘 ≤y940**，字幕未遮挡任何文字/图片（text-only + 卡片比对通过）
- [ ] **卡内图片全为 PPT 原图**，无额外图片
- [ ] 实测段未含黑屏（上部亮度无骤降段）
- [ ] 结束页出现在截断窗口内
- [ ] 预告卡字线与文字无重叠（间距 ≥40px）
- [ ] 未获剪辑授权时，原视频/画面时长与源视频一致；获授权的 `enhance` 按 manifest 时间轴验收
- [ ] 字幕内容与当前画面严格对应，无常识性/单位错误
- [ ] BGM 音量 0.08 左右，不压人声，片尾 5s 静音、提前 3s 淡出
- [ ] SVG 架构图坐标对齐网格、通道不穿字
- [ ] 混音无削波爆音（alimiter 生效）
- [ ] 本地播放器可打开（GStreamer 解码器就位）
- [ ] 所有素材只读引用，原文件未改动

## Example prompts

```text
用 V1 优化这个已有视频：保留全部画面和原时长，只加中文配音、字幕和 BGM。
```

```text
用 V2 enhance 重构这个录屏，允许删除、压缩、重新排序和补充科研汇报卡片。
```

```text
用 V2 create 根据这些 PPT 页、图片和文案，从零制作一条讲解视频。
```

```text
把我的这个项目和这段素材做成一个中期汇报讲解视频，
要有中文配音、配上中文字幕，画面用白底学术风，
先讲背景痛点再讲方案，最后放实测视频。大约 1 分钟。
```

```text
做一条给老师看的演示视频：RaptorQ 喷泉码抗丢包方案。
架构图要按高星 skill 的 Flat Icon 规范画，实测视频先检测黑屏再截。
```

```text
画面里的图要用我 PPT 里的原图，不要另外找图，贴完检查图片不能挡到文字。
```

```text
我改了文案，重出一版视频。上一版的时间轴和画面结构都要保留，只换内容，
字幕也跟着新文案重新生成。
```

```text
给我的视频加配音和字幕，但不要改变原视频时长。字幕要看完画面内容再写，
底部居中、字号小一点。背景音用兜圈，音量轻一点，片尾不要生硬截断。
```

## 中文说明

这是一个 Claude Code skill，用来沉淀"把技术方案/项目成果做成中文配音讲解视频"的完整流程。

特别适合这些场景：

- 课题组中期汇报、结题答辩、组会分享的视频
- 把论文/方案/系统架构讲给不懂技术的人听
- 需要实测画面佐证的项目展示
- 想用脚本一键重出、改文案就重跑的视频
- 无图形界面环境下也要能自检验证的场景

## 关于默认 BGM

本 skill 已内置一首默认背景音：`assets/bgm_default.mp3`（洛克王国人鱼湾/兜圈纯音乐 BGM）。

- 音量默认 `0.08`，低于人声约 30dB，不压旁白。
- 结尾提前 3 秒淡出，最后 5 秒完全静音，避免片尾音乐被生硬截断。
- 需要其他 BGM 时，可以用 `you-get` 从 B 站/音乐网站下载，然后通过 `mix_audio.py --bgm 路径` 指定。

## Repository layout

```text
.
├── SKILL.md            # skill 主指令（工作流 + 铁律 + 坑速查）
├── README.md
├── LICENSE
├── references/
│   ├── cards.md        # 画面卡规范（白底学术风参数）
│   ├── flat-icon-graph.md  # SVG 技术图 Flat Icon 规范
│   ├── ffmpeg-recipes.md   # 合成配方 + 坑（-t 输出截断/防削波/竖屏）
│   └── verification.md     # 无视觉自检方法
├── scripts/
│   ├── make_cards.py       # 画面卡生成模板（PPT 原图 + 字幕带约束 + text-only 自检）
│   ├── make_tts.py         # edge-tts 配音（SEGS 文案唯一来源，含断词铁律）
│   ├── make_subs.py        # 复用 SEGS 自动生成中文字幕 subs.srt
│   ├── check_blackscreen.py# 实测视频黑屏检测
│   └── verify_video.py     # 成品自检（含卡片比对 + 字幕带检查）
├── assets/
│   └── hero.svg
└── evals/
    └── evals.json
```
