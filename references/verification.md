# 无视觉自检验证

无图形界面环境下，用"像素采样 + OCR + 坐标审查 + 卡片比对 + 字幕带检查"代替眼睛。参考脚本：`../scripts/verify_video.py`、`../scripts/check_blackscreen.py`、`../scripts/make_cards.py`（文末 `verify_text_not_covered`）。

## 0. 卡片阶段自检：图片是否遮挡文字（text-only）

`make_cards.py` 跑完自动执行 `verify_text_not_covered(generators)`：
- monkeypatch `paste_ppt_card` 只记录 region 不粘贴，生成"无图版"卡片；
- 检查每个图 region 内亮度均值>235 且暗像素=0（文字侵入即出现暗像素）；
- 任一 region 失败就说明文字被图遮住，需上移/收窄图片后重跑。
- 硬约束：所有卡片内容最下缘 ≤ **y940**（字幕烧录后占 y960-1049）。

## 1. 成品基础校验（ffprobe）

```bash
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 成品.mp4
ffprobe -v error -select_streams v -show_entries stream=width,height,codec_name -of csv 成品.mp4
ffprobe -v error -select_streams a -show_entries stream=codec_name,sample_rate -of csv 成品.mp4
```
- 时长应等于 `END_END`；分辨率 1920×1080；视频 H.264，音频 AAC。

## 2. 抽帧 + 像素亮度采样

```bash
ffmpeg -y -ss <T> -i 成品.mp4 -frames:v 1 -q:v 2 /tmp/frame_T.png
```

用 PIL 采样判断：
- **黑屏检测**：把画面按行采样亮度。真实演示视频若某个时间点起**上部亮度骤降**（如 75→0），就是黑屏段起点。黑屏起点 = 可用的最晚干净帧。
  ```python
  im = Image.open(f).convert("L")
  top = im.crop((0, 0, w, int(h*0.35))).getextrema()  # 上部亮度范围
  ```
- **页面空白检查**：整图采样，学术卡应接近纯白（如 250+）；预告卡应接近深色渐变。

## 3. OCR 检查文字

```bash
tesseract /tmp/frame_T.png /tmp/ocr_T -l chi_sim 2>/dev/null
```
- 检查标题/要点完整出现、无乱码、无重叠（重叠会 OCR 成乱串）。
- 无 chi_sim 语言包先装：`sudo apt-get install -y tesseract-ocr tesseract-ocr-chi-sim`。

## 4. 坐标逻辑审查（SVG 图）

- 对 `arch.svg` / `feedback.svg` 这类手写图，用 PIL 在**已知坐标**采样验证：某通道 y 行应只有箭头色（如 `#2563eb`），标签矩形区应有白底遮断。
- 检查走线是否穿字：沿通道 y 扫描，被标签矩形覆盖的区间外不应有文字像素与线重叠。
- 审查要点：网格对齐（坐标 %8==0）、组件间距 ≥64、图标在 44×44 内、两行文字基线不叠。

## 5. 逐段边界抽查

在每段边界前后各抽 1 帧（如 `t-0.3 / t+0.3`），确认淡入淡出正常、切换画面是预期卡片。尤其检查：
- 实测段结束点恰好 = 黑屏起点前（若放过了黑屏，观众会看到黑屏）。
- 结束页在总长窗口内出现（上一版 bug：实测段超时把结束页挤出截断窗口）。

## 6. 卡片比对 + 字幕带检查（有字幕片的终检）

```bash
python3 scripts/verify_video.py 成品.mp4 --cards=cards 3.0 14.0 18.0 33.0 99.0 117.0
```
- 每个抽样时间点（必须是**该卡片段内、且该段配音正在播**的中间点）抽帧：
  - **卡片区 y<945** 与 `cards/*.png` 逐张比对，取 diff 最小者，要求 **diff<4**（=画面与源卡一致，无渲染异常/被污染）。
  - **字幕带 y945-1080** 与源卡该区比暗像素，要求渲染像素 **>300**（有配音段字幕确在显示）。
- **终检假阳性提醒**：抽样时间别落在段边界上（恰在边界时上一段刚淡出，diff 会误报）；结束页等后段取实际段内时间（如总长 157s 时取 155.5 而非 152.0）。

## 7. 字幕时间轴核对

- `make_subs.py` 生成的 `subs.srt` 与配音同源，逐条验证显示区间落在对应配音段内。
- 抽帧 OCR 字幕带，确认中文字幕渲染正确、无乱码、未超出单行长度。
