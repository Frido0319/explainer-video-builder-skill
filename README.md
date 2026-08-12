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
sudo apt-get install -y ffmpeg fonts-noto-cjk tesseract-ocr tesseract-ocr-chi-sim \
  gstreamer1.0-libav gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
pip install edge-tts==7.2.8 pillow
```

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
- [ ] SVG 架构图坐标对齐网格、通道不穿字
- [ ] 混音无削波爆音（alimiter 生效）
- [ ] 本地播放器可打开（GStreamer 解码器就位）
- [ ] 所有素材只读引用，原文件未改动

## Example prompts

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

## 中文说明

这是一个 Claude Code skill，用来沉淀"把技术方案/项目成果做成中文配音讲解视频"的完整流程。

特别适合这些场景：

- 课题组中期汇报、结题答辩、组会分享的视频
- 把论文/方案/系统架构讲给不懂技术的人听
- 需要实测画面佐证的项目展示
- 想用脚本一键重出、改文案就重跑的视频
- 无图形界面环境下也要能自检验证的场景

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

